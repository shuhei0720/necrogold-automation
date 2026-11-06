"""TEST-023: 実測範囲を明示したHUDの拍取得と、確立した周期の継続追跡。

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
ZONE1_1_PROFILE = 'zone1-1-measured-v1'
_ZONE1_1_METADATA = {
    'id': ZONE1_1_PROFILE, 'period_min_ns': 515_000_000, 'period_max_ns': 530_000_000,
    'minimum_samples': 4, 'minimum_span_ns': 2_000_000_000, 'maximum_span_ns': 20_000_000_000,
    'evidence': 'two-known-videos-51-heart-expansions', 'scope': 'recognized-zone1-floor1',
}
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


def fit(samples, profile=None):
    """ライブ標本から周期とHTTP中点基準のepochを推定。別解競合はNone。

    端点間の整数拍数と半拍ずれの初期候補を全列挙するため、探索量は有限。
    residualは中点への当てはまりであり、capture遅延の上限を表さない。
    通常は8〜12標本/2〜20秒。測定済み1-1 profileは4〜12標本/2〜20秒で
    .515〜.530秒へ限定する条件付き推定。同等以上の範囲外別解があれば拒否。
    既知動画の範囲は未知曲の保証ではなく、epochも周期も今回の標本で回帰する。
    """
    if profile is not None and (type(profile) is not str or profile != ZONE1_1_PROFILE):
        return None
    metadata = dict(_ZONE1_1_METADATA) if profile is not None else None
    minimum_samples = 4 if metadata is not None else 8
    if type(samples) is not list or not minimum_samples <= len(samples) <= 12 or not all(map(_sample_valid, samples)):
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
    outside = []
    if metadata is not None:
        # modelと同じ整数nsで境界を比較し、回帰の浮動小数点丸めで端を落とさない。
        outside = [c for c in distinct if not metadata['period_min_ns'] <= round(1e9/c['frequency']) <= metadata['period_max_ns']]
        distinct = [c for c in distinct if metadata['period_min_ns'] <= round(1e9/c['frequency']) <= metadata['period_max_ns']]
        if not distinct:
            return None
    best = distinct[0]
    if outside and outside[0]['rms'] <= best['rms'] + 1e-9:
        return None
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
            "dispatch_lead_ns": DEFAULT_LEAD_NS, "dispatch_timing_calibrated": False,
            "mode": "acquired", "tracking_error_cycles": None,
            "extrapolation_budget_cycles": None, "gap_ns": 0, "prediction_span_ns": 0,
            "cadence_profile": metadata}


def track(model, samples):
    """確立済み周期を新しいHUDで検証し、同じ周回数の枝で更新する。

    初期取得のalias判定を代用しない。最新の位相をrefit前に確認し、旧周期と
    半周以上離れる回帰は禁止。入力時の3秒鮮度はnext_targetが別に要求する。
    R*(1+2*gap/span)は追跡を打ち切る経験的budgetであり、表示/通信遅延や
    将来誤差の保証ではない。新しい画像の時刻もHTTP中点の推定のままである。
    """
    if (not _model_valid(model) or model.get("mode") not in ("acquired", "tracking")
            or not _ns(model.get("first_sample_ns"))
            or not _number(model.get("max_residual_cycles"))
            or not 0 <= model["max_residual_cycles"] <= MAX_SINGLE_RESIDUAL_CYCLES
            or type(samples) is not list or not 3 <= len(samples) <= 12
            or not all(map(_sample_valid, samples))):
        return None
    mids = [s["midpoint_ns"] for s in samples]
    if any(b <= a for a, b in zip(mids, mids[1:])):
        return None
    old_span = model["last_sample_ns"] - model["first_sample_ns"]
    gap = mids[-1] - model["last_sample_ns"]
    if (not 2_000_000_000 <= old_span <= 20_000_000_000
            or not 0 < gap <= old_span or model["last_sample_ns"] not in mids):
        return None
    budget = model["max_residual_cycles"] * (1 + 2 * gap / old_span)
    if budget > MAX_SINGLE_RESIDUAL_CYCLES:
        return None
    tolerance = min(MAX_SINGLE_RESIDUAL_CYCLES, max(0.08, 3 * model["residual_cycles"]))
    errors = []
    for sample in samples:
        if sample["midpoint_ns"] > model["last_sample_ns"]:
            expected = ((model["epoch_ns"] - sample["midpoint_ns"]) % model["period_ns"]) / model["period_ns"]
            errors.append(_distance(sample["q"], expected))
    if any(abs(error) > tolerance for error in errors):
        return None
    # 歩行の間隔が長くても過去20秒まで。初期の8枚を毎回要求し直さない。
    window = [s for s in samples if mids[-1] - s["midpoint_ns"] <= 20_000_000_000]
    if len(window) < 3 or window[-1]["midpoint_ns"] - window[0]["midpoint_ns"] < 2_000_000_000:
        return None
    times = [(s["midpoint_ns"] - window[0]["midpoint_ns"]) / 1e9 for s in window]
    frequency = 1e9 / model["period_ns"]
    candidate = _candidate(times, [s["q"] for s in window], frequency)
    if (candidate is None or candidate["rms"] > MAX_RESIDUAL_CYCLES
            or candidate["maximum"] > MAX_SINGLE_RESIDUAL_CYCLES
            or abs(candidate["frequency"] - frequency) * (old_span / 1e9) >= 0.5):
        return None
    period = round(1e9 / candidate["frequency"])
    profile = model.get('cadence_profile')
    if profile is not None and not profile['period_min_ns'] <= period <= profile['period_max_ns']:
        return None
    epoch = window[0]["midpoint_ns"] + round(candidate["intercept"] * period)
    epoch += ((mids[-1] - epoch) // period) * period
    updated = dict(model)
    updated.update(period_ns=period, epoch_ns=epoch,
                   first_sample_ns=window[0]["midpoint_ns"], last_sample_ns=mids[-1],
                   sample_count=len(window), residual_cycles=candidate["rms"],
                   max_residual_cycles=candidate["maximum"],
                   runner_up_residual_cycles=None, alias_gap_cycles=None, candidate_count=1,
                   http_half_width_max_ns=max(s["http_half_width_ns"] for s in window),
                   mode="tracking", tracking_error_cycles=errors[-1],
                   extrapolation_budget_cycles=budget, gap_ns=gap, prediction_span_ns=old_span)
    return updated


def _model_valid(model, required_profile=None):
    if type(model) is not dict:
        return False
    profile = model.get('cadence_profile')
    if required_profile is not None and (type(profile) is not dict or profile.get('id') != required_profile):
        return False
    if profile is not None:
        if (type(profile) is not dict or set(profile) != set(_ZONE1_1_METADATA)
                or any(type(profile[key]) is not type(value) or profile[key] != value
                       for key, value in _ZONE1_1_METADATA.items())
                or model.get('mode') not in ('acquired', 'tracking')
                or type(model.get('sample_count')) is not int
                or not (4 if model['mode'] == 'acquired' else 3) <= model['sample_count'] <= 12
                or not _ns(model.get('first_sample_ns')) or not _ns(model.get('last_sample_ns'))
                or not 2_000_000_000 <= model['last_sample_ns'] - model['first_sample_ns'] <= 20_000_000_000
                or not _ns(model.get('period_ns'))
                or not profile['period_min_ns'] <= model['period_ns'] <= profile['period_max_ns']):
            return False
    elif model.get('mode') == 'acquired' and (type(model.get('sample_count')) is not int or model['sample_count'] < 8):
        return False
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
