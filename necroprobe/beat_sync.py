"""TEST-016: HUDの拍をHTTP中点の時計へ当てはめる限定試験用の推定器。

HTTP区間は画像生成時刻でも保証された誤差範囲でもない。固定の取得遅延・
入力遅延は未校正であり、良い回帰残差も実機の拍受付を証明しない。
このmoduleは入力を送らない。復帰/リスタート/ポーズ時には呼出側がモデルを
破棄し、移動後の実画面と前面確認を別途行う。
"""
import math
from statistics import median

from PIL import Image, ImageChops

SIZE = (896, 414)
MIN_PERIOD_NS = 320_000_000
MAX_PERIOD_NS = 800_000_000
FRESH_NS = 3_000_000_000
DEFAULT_LEAD_NS = 150_000_000
MAX_RESIDUAL_CYCLES = 0.055
MAX_SINGLE_RESIDUAL_CYCLES = 0.13
MIN_ALIAS_GAP_CYCLES = 0.04
_TAU = 2 * math.pi
_POSITIVE = [0] + [255] * 255
_GREEN = [255 if value >= 75 else 0 for value in range(256)]
_BLUE = [255 if value >= 60 else 0 for value in range(256)]
_RED_PLUS_35 = [min(255, value + 35) for value in range(256)]
_RED_PLUS_25 = [min(255, value + 25) for value in range(256)]


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _ns(value):
    return type(value) is int and 0 <= value < 2**63


def _distance(a, b):
    return (a - b + 0.5) % 1 - 0.5


def _circle(values):
    real = sum(math.cos(_TAU * value) for value in values)
    imag = sum(math.sin(_TAU * value) for value in values)
    if math.hypot(real, imag) < 0.5 * len(values):
        return None
    return (math.atan2(imag, real) / _TAU) % 1


def extract(image):
    """原寸RGBの下部バーから残り拍割合を返す。不十分・不整合ならNone。

    色maskはPillow native演算、列の集計はbytes.count。Pythonでは896列の小さな
    要約だけを走査し、原画像全体の画素走査・resize・回転を行わない。
    閾値は既知HUDの試験値であり、未知画像での精度は未検証。
    """
    if not isinstance(image, Image.Image) or image.size != SIZE or image.mode != "RGB":
        return None
    with image.crop((0, 350, 896, 387)) as roi:
        red, green, blue = roi.split()
        mask = ImageChops.darker(green.point(_GREEN), blue.point(_BLUE))
        for channel, lower in ((green, _RED_PLUS_35), (blue, _RED_PLUS_25)):
            above = ImageChops.subtract(channel, red.point(lower)).point(_POSITIVE)
            mask = ImageChops.darker(mask, above)
        # 37行の二値mask: 平均>=120 と 255の個数>=18 は同値。
        # 旧Pillowで非対応のBoxBlur((0,18))を使わず、原画像も変形しない。
        columns = mask.tobytes()
    active = [x for x in range(20, 876)
              if not 418 <= x <= 474 and columns[x::896].count(255) >= 18]
    groups = []
    for x in active:
        if not groups or x - groups[-1][-1] > 3:
            groups.append([x])
        else:
            groups[-1].append(x)
    positions = [sum(group) / len(group) for group in groups
                 if 2 <= group[-1] - group[0] + 1 <= 10]
    left = [x for x in positions if x < 418]
    right = [x for x in positions if x > 474]
    if min(len(left), len(right)) < 2:
        return None
    gaps = [b - a for side in (left, right) for a, b in zip(side, side[1:])]
    adjacent = [gap for gap in gaps if 90 <= gap <= 120]
    if len(adjacent) < 2:
        return None
    spacing = median(adjacent)
    if any(abs(gap / spacing - round(gap / spacing)) > 0.045 for gap in gaps):
        return None
    centers = [(a + b) / 2 for a in left for b in right if 440 <= (a + b) / 2 <= 452]
    if len(centers) < 2:
        return None
    center = median(centers)
    if max(abs(value - center) for value in centers) > 2.5:
        return None
    phases_left = [((center - x) / spacing) % 1 for x in left]
    phases_right = [((x - center) / spacing) % 1 for x in right]
    q_left, q_right = _circle(phases_left), _circle(phases_right)
    if q_left is None or q_right is None or abs(_distance(q_left, q_right)) > 0.045:
        return None
    phases = phases_left + phases_right
    q = _circle(phases)
    if q is None or max(abs(_distance(value, q)) for value in phases) > 0.045:
        return None
    return {"remaining": q, "spacing_px": spacing, "center_px": center}


def make_sample(feature, http_start_ns, http_end_ns):
    """HTTP両端を失わず保存する。不正値はValueError。中点は未校正の推定。"""
    if (type(feature) is not dict or not _ns(http_start_ns) or not _ns(http_end_ns)
            or http_end_ns <= http_start_ns):
        raise ValueError("invalid beat sample")
    q, spacing, center = (feature.get(key) for key in ("remaining", "spacing_px", "center_px"))
    if (not all(_number(value) for value in (q, spacing, center))
            or not 0 <= q < 1 or not 90 <= spacing <= 120 or not 440 <= center <= 452):
        raise ValueError("invalid beat feature")
    return {"http_start_ns": http_start_ns, "http_end_ns": http_end_ns,
            "midpoint_ns": http_start_ns + (http_end_ns - http_start_ns) // 2,
            "http_half_width_ns": (http_end_ns - http_start_ns) / 2,
            "q": float(q), "remaining": float(q),
            "spacing_px": float(spacing), "center_px": float(center)}


def _sample_valid(sample):
    if type(sample) is not dict:
        return False
    try:
        expected = make_sample(sample, sample.get("http_start_ns"), sample.get("http_end_ns"))
    except ValueError:
        return False
    return all(type(sample.get(key)) is type(value) and sample[key] == value
               for key, value in expected.items())


def _candidate(times, phases, frequency):
    """端点で列挙した周回数を、全標本のunwrapと最小二乗で調整する。"""
    mean_t = sum(times) / len(times)
    variance = sum((value - mean_t) ** 2 for value in times)
    for _ in range(3):
        intercept = _circle([(q + frequency * t) % 1 for t, q in zip(times, phases)])
        if intercept is None:
            return None
        unwrapped = [q + round(intercept - frequency * t - q) for t, q in zip(times, phases)]
        mean_q = sum(unwrapped) / len(unwrapped)
        slope = sum((t - mean_t) * (q - mean_q) for t, q in zip(times, unwrapped)) / variance
        frequency = -slope
        intercept = mean_q - slope * mean_t
    if not 1e9 / MAX_PERIOD_NS <= frequency <= 1e9 / MIN_PERIOD_NS:
        return None
    errors = [_distance(q, intercept - frequency * t) for t, q in zip(times, phases)]
    rms = math.sqrt(sum(value * value for value in errors) / len(errors))
    return {"frequency": frequency, "intercept": intercept % 1,
            "rms": rms, "maximum": max(abs(value) for value in errors)}


def fit(samples):
    """8〜12標本から周期とHTTP中点基準のepochを推定。別解競合はNone。

    端点間の整数拍数と半拍ずれの初期候補を全列挙するため、探索量は有限。
    residualは中点への当てはまりであり、capture遅延の上限を表さない。
    """
    if type(samples) is not list or not 8 <= len(samples) <= 12 or not all(map(_sample_valid, samples)):
        return None
    mids = [sample["midpoint_ns"] for sample in samples]
    if any(b <= a for a, b in zip(mids, mids[1:])):
        return None
    times = [(value - mids[0]) / 1e9 for value in mids]
    span = times[-1]
    if not 2 <= span <= 20:
        return None
    phases = [sample["q"] for sample in samples]
    ordered = sorted(phases)
    circular_gaps = [b - a for a, b in zip(ordered, ordered[1:])] + [ordered[0] + 1 - ordered[-1]]
    if 1 - max(circular_gaps) < 0.35:
        return None
    delta = phases[0] - phases[-1]
    low = math.floor(span * 1e9 / MAX_PERIOD_NS - delta) - 1
    high = math.ceil(span * 1e9 / MIN_PERIOD_NS - delta) + 1
    candidates = []
    for cycles in range(low, high + 1):
        for shift in (0.0, 0.5):
            frequency = (delta + cycles + shift) / span
            if not 1e9 / MAX_PERIOD_NS <= frequency <= 1e9 / MIN_PERIOD_NS:
                continue
            candidate = _candidate(times, phases, frequency)
            if candidate is not None:
                candidates.append(candidate)
    candidates.sort(key=lambda value: value["rms"])
    distinct = []
    for candidate in candidates:
        if not any(abs(candidate["frequency"] - old["frequency"]) * span < 0.02 for old in distinct):
            distinct.append(candidate)
    if not distinct:
        return None
    best = distinct[0]
    alternate = distinct[1]["rms"] if len(distinct) > 1 else None
    if (best["rms"] > MAX_RESIDUAL_CYCLES or best["maximum"] > MAX_SINGLE_RESIDUAL_CYCLES
            or (alternate is not None and alternate - best["rms"] < MIN_ALIAS_GAP_CYCLES)):
        return None
    period = round(1e9 / best["frequency"])
    epoch = mids[0] + round(best["intercept"] * period)
    epoch += ((mids[-1] - epoch) // period) * period
    return {"period_ns": period, "epoch_ns": epoch,
            "first_sample_ns": mids[0], "last_sample_ns": mids[-1], "sample_count": len(samples),
            "residual_cycles": best["rms"], "max_residual_cycles": best["maximum"],
            "runner_up_residual_cycles": alternate,
            "alias_gap_cycles": None if alternate is None else alternate - best["rms"],
            "candidate_count": len(distinct),
            "http_half_width_max_ns": max(sample["http_half_width_ns"] for sample in samples),
            "clock_source": "http_midpoint_unverified", "device_timing_verified": False,
            "dispatch_lead_ns": DEFAULT_LEAD_NS, "dispatch_timing_calibrated": False}


def _model_valid(model):
    return (type(model) is dict and _ns(model.get("period_ns"))
            and MIN_PERIOD_NS <= model["period_ns"] <= MAX_PERIOD_NS
            and _ns(model.get("epoch_ns")) and _ns(model.get("last_sample_ns"))
            and _number(model.get("residual_cycles"))
            and 0 <= model["residual_cycles"] <= MAX_RESIDUAL_CYCLES
            and model.get("device_timing_verified") is False
            and model.get("dispatch_timing_calibrated") is False
            and model.get("clock_source") == "http_midpoint_unverified")


def next_target(model, now_ns, lead_ns=DEFAULT_LEAD_NS):
    """now+leadより後の拍。150msは未校正の試験値でありRTT/2ではない。"""
    if (not _model_valid(model) or not _ns(now_ns) or not _ns(lead_ns)
            or lead_ns > 1_000_000_000 or not 0 <= now_ns - model["last_sample_ns"] <= FRESH_NS):
        return None
    period, epoch = model["period_ns"], model["epoch_ns"]
    target = epoch + ((now_ns + lead_ns - epoch) // period + 1) * period
    return target if _ns(target) else None


def compatible(model, sample):
    """新しいHTTP中点での位相整合だけを検査。実移動の成功判定ではない。"""
    if (not _model_valid(model) or not _sample_valid(sample)
            or not 0 <= sample["midpoint_ns"] - model["last_sample_ns"] <= FRESH_NS):
        return False
    expected = ((model["epoch_ns"] - sample["midpoint_ns"]) % model["period_ns"]) / model["period_ns"]
    tolerance = min(MAX_SINGLE_RESIDUAL_CYCLES, max(0.08, 3 * model["residual_cycles"]))
    return abs(_distance(sample["q"], expected)) <= tolerance
