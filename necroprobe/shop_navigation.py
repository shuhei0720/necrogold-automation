"""TEST-016: 原寸36px格子と一入力ごとの画像確認による限定歩行。

既知画像に対する暫定規則。未知の配置/暗さでの精度、iSHでの速度、
実入力の向きは未検証。unknownは床にも商品なしにも置き換えない。
画像全体のresize/rotation、旧R12のimport、ネットワーク操作は行わない。
"""
from collections import deque
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageFilter, ImageStat


SIZE = (896, 414)
ORIGIN = (448, 207)
TILE = 36
DIRECTIONS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
_POSITIVE = [0] + [255] * 255
_HUD = ((0, 0, 143, 140), (663, 0, 896, 80), (717, 315, 896, 414),
        (405, 321, 485, 414), (0, 380, 896, 414), (429, 0, 465, 45),
        (866, 45, 896, 290))
_SIGNATURE_SIZE = (224, 104)


def _add(point, delta):
    return point[0] + delta[0], point[1] + delta[1]


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _colour_mask(channels, sign=False):
    red, green, blue = channels
    mask = red.point([255 if value > (57 if sign else 52) else 0 for value in range(256)])
    low_g, high_g, high_b = (865, 1050, 240) if sign else (685, 920, 580)
    for left, right in ((green, red.point([value * low_g // 1000 for value in range(256)])),
                        (red.point([(value * high_g + 999) // 1000 for value in range(256)]), green),
                        (green.point([(value * high_b + 999) // 1000 for value in range(256)]), blue)):
        mask = ImageChops.darker(mask, ImageChops.subtract(left, right).point(_POSITIVE))
    if not sign:
        mask = ImageChops.darker(mask, ImageChops.subtract(
            blue, green.point([value * 7 // 100 for value in range(256)])).point(_POSITIVE))
    for box in _HUD:
        mask.paste(0, box)
    return mask


@dataclass
class Scene:
    tiles: dict
    gold: set
    goods: str
    protected: set
    signature: bytes

    def summary(self):
        return {"tiles": [[*point, kind] for point, kind in sorted(self.tiles.items())],
                "gold": [list(p) for p in sorted(self.gold)], "goods": self.goods,
                "protected": [list(p) for p in sorted(self.protected)]}


def _peaks(mask):
    density = mask.filter(ImageFilter.BoxBlur(14))
    result = []
    for _ in range(12):
        high = density.getextrema()[1]
        if high < 96:
            break
        top = density.point([255 if value == high else 0 for value in range(256)]).getbbox()
        y = top[1]
        row = density.crop((0, y, SIZE[0], y + 1))
        x = row.point([255 if value == high else 0 for value in range(256)]).getbbox()[0]
        result.append((x, y))
        density.paste(0, (max(0, x - 23), max(0, y - 23), min(SIZE[0], x + 24), min(SIZE[1], y + 24)))
    return result


def _merchandise(image, gray, channels):
    """看板候補と同一baselineの価格3列、各商品画素を別々に要求。"""
    peaks = _peaks(_colour_mask(channels, sign=True))
    if not peaks:
        return "unknown", set()
    red, green, blue = channels
    low = ImageChops.darker(red, ImageChops.darker(green, blue))
    high = ImageChops.lighter(red, ImageChops.lighter(green, blue))
    white = ImageChops.darker(low.point([255 if v > 140 else 0 for v in range(256)]),
                            ImageChops.subtract(high, low).point([255 if v < 40 else 0 for v in range(256)]))
    bright = gray.point([255 if v > 55 else 0 for v in range(256)])
    partial = set()
    for x, y in peaks:
        for left in (x, x - 72):
            xs = (left, left + 36, left + 72)
            if xs[0] < 18 or xs[-1] >= 878:
                continue
            for dy in (-4, -2, 0, 2, 4, 6):
                sign_y = y + dy
                cells = {(round((cx - ORIGIN[0]) / TILE), round((sign_y + 48 - ORIGIN[1]) / TILE)) for cx in xs}
                # Protect both possible three-slot interpretations before the
                # prices become readable; missing prices never permit a step.
                partial.update(cells)
                start = sign_y + 69
                if start < 0 or start + 20 >= 414:
                    continue
                price_rows = []
                item_count = 0
                for cx in xs:
                    crop = white.crop((cx - 11, start, cx + 12, start + 20))
                    rows = [sum(crop.crop((0, row, 23, row + 9)).histogram()[255:]) for row in range(12)]
                    price_rows.append(rows)
                    item_box = (cx - 17, sign_y + 24, cx + 18, sign_y + 66)
                    item_count += bright.crop(item_box).histogram()[255] >= 24
                prices = max(sum(values[k] >= 18 for values in price_rows) for k in range(12))
                if prices < 1 or item_count < 1:
                    continue
                full_box = (xs[0] - 18, sign_y + 24, xs[-1] + 18, start + 20)
                if prices == 3 and item_count == 3 and not any(_overlap(full_box, box) for box in _HUD):
                    return "visible", cells
    return ("partial", partial) if partial else ("unknown", set())


def _gates(tiles):
    result = {}
    for point, kind in tiles.items():
        if kind not in ("floor", "door", "dirt", "stone"):
            continue
        x, y = point
        for tangent, normal in (((1, 0), (0, 1)), ((0, 1), (1, 0))):
            if (tiles.get((x - tangent[0], y - tangent[1])) == "gold" and
                    tiles.get((x + tangent[0], y + tangent[1])) == "gold"):
                result[point] = (_add(point, normal), (x - normal[0], y - normal[1]))
    return result


def scan(image):
    if not isinstance(image, Image.Image) or image.size != SIZE or image.mode != "RGB":
        return Scene({}, set(), "unknown", set(), b"")
    gray = image.convert("L")
    from . import navigation_stats
    fast_stats = navigation_stats.scan(image.tobytes())
    channels = image.split()
    gold_mask = _colour_mask(channels)
    tiles = {(0, 0): "floor"}
    for j in range(-5, 5):
        for i in range(-11, 12):
            if i == j == 0:
                continue
            x, y = ORIGIN[0] + TILE * i, ORIGIN[1] + TILE * j
            box = (x - 12, y - 12, x + 13, y + 13)
            if any(_overlap(box, hud) for hud in _HUD):
                continue
            point = (i, j)
            if gold_mask.crop(box).histogram()[255] >= 280:
                tiles[point] = "gold"
                continue
            if fast_stats is None:
                stats = ImageStat.Stat(image.crop(box))
                r, g, b = stats.median
                spread_enough = None
            else:
                offset = ((j + 5) * 23 + i + 11) * 4
                r, g, b, spread_enough = fast_stats[offset:offset + 4]
            if r < 6 or g < 3:
                continue
            # Positive dark-floor evidence. The old catch-all floor branch is
            # deliberately absent; warm dirt and bright grey stone stay blocked.
            dark_floor = (r <= 38 and 44 * r <= 100 * b <= 90 * r
                          and 40 * r <= 100 * g <= 90 * r and abs(g-b) <= max(2,.18*r))
            # TEST019: lit floor around the player reaches medians39..45.
            # This narrow positive band excludes both existing stone (g/r>.69)
            # and dirt (b/r<.55); unknown pixels never become floor by default.
            bright_floor = (38 < r <= 52 and 55*r <= 100*b <= 70*r
                            and 45*r <= 100*g <= 68*r and abs(g-b) <= max(2,.12*r))
            if ((dark_floor or bright_floor)
                    and (spread_enough if spread_enough is not None else max(stats.stddev) >= 2)):
                tiles[point] = "floor"
            elif r > 40 and 100 * b > 53 * r and 100 * g > 69 * r:
                tiles[point] = "stone"
            elif 100 * b < 55 * r and 100 * g > 42 * r:
                tiles[point] = "dirt"
    for point in _gates(tiles):
        if tiles[point] in ("dirt", "stone"):
            tiles[point] = "door"
    goods, items = _merchandise(image, gray, channels)
    protected = set(items)
    for point in items:
        protected.update(_add(point, delta) for delta in DIRECTIONS.values())
        tiles[point] = "item"
    # Direct sparse sampling keeps 36px=9 samples, 32px tween=8 samples. This
    # neither stretches the image nor invents interpolated image pixels.
    raw = gray.tobytes()
    signature = b"".join(raw[y * SIZE[0]:(y + 1) * SIZE[0]:4] for y in range(0, SIZE[1], 4))
    return Scene(tiles, {p for p, kind in tiles.items() if kind == "gold"}, goods, protected, signature)


def choose(scene, position=(0, 0), visits=None):
    def result(direction=None, reason="no_observed_route", target=None):
        return {"direction": direction, "reason": reason, "target": target}
    if scene.goods == "visible":
        return result(reason="goods_visible")
    if any(delta in scene.protected for delta in DIRECTIONS.values()) or (0, 0) in scene.protected:
        return result(reason="goods_adjacent_controls_unverified")
    if not scene.gold or scene.tiles.get((0, 0)) != "floor":
        return result(reason="no_visible_gold_or_origin")
    visits = visits or {}
    paths = {(0, 0): ()}
    queue = deque([(0, 0)])
    while queue:
        point = queue.popleft()
        for name, delta in DIRECTIONS.items():
            nxt = _add(point, delta)
            if nxt not in paths and nxt not in scene.protected and scene.tiles.get(nxt) == "floor":
                paths[nxt] = paths[point] + (name,)
                queue.append(nxt)
    options = []
    for gate, sides in _gates(scene.tiles).items():
        if gate in scene.protected:
            continue
        for near in sides:
            if near not in paths:
                continue
            path = paths[near]
            if not path:
                direction = next((name for name, delta in DIRECTIONS.items() if _add(near, delta) == gate), None)
                if direction:
                    return result(direction, "gate_single_probe", gate)
            else:
                options.append((len(path), path[0], near))
    if options:
        _, direction, target = min(options)
        return result(direction, "approach_gate", target)
    # A partial gold wall may require moving around a corner. Only known floor
    # is eligible; the smallest distance-to-gold and revisit penalty guide it.
    for target, path in paths.items():
        if not path:
            continue
        gap = min(_distance(target, gold) for gold in scene.gold)
        seen = visits.get(_add(position, target), 0)
        options.append((3 * gap + len(path) + 4 * seen, path[0], target))
    if options:
        _, direction, target = min(options)
        return result(direction, "observed_floor_vantage", target)
    return result()


def _pillow_motion_scores(before_signature, after_signature):
    """Native利用不可時の既存73候補。スコア・有効領域・丸めを維持。"""
    old = Image.frombytes("L", _SIGNATURE_SIZE, before_signature)
    new = Image.frombytes("L", _SIGNATURE_SIZE, after_signature)
    valid = Image.new("L", _SIGNATURE_SIZE)
    valid.paste(255, (40, 20, 179, 79))
    valid.paste(0, (90, 36, 139, 79))  # player / opening instructions
    active_old = ImageChops.darker(old.point([255 if v > 6 else 0 for v in range(256)]), valid)
    active_new = ImageChops.darker(new.point([255 if v > 6 else 0 for v in range(256)]), valid)

    def score(sx, sy):
        box = (max(0, -sx), max(0, -sy), min(224, 224 - sx), min(104, 104 - sy))
        other = (box[0] + sx, box[1] + sy, box[2] + sx, box[3] + sy)
        a, b = old.crop(box), new.crop(other)
        mask = ImageChops.darker(active_old.crop(box), active_new.crop(other))
        if mask.histogram()[255] < 300:
            return float("inf")
        sa, sb = ImageStat.Stat(a, mask), ImageStat.Stat(b, mask)
        contrast = (sa.stddev[0] + sb.stddev[0]) / 2
        if contrast < 2.5 or min(sa.mean[0], sb.mean[0]) < 6:
            return float("inf")
        gain = max(.65, min(1.55, sa.mean[0] / sb.mean[0]))
        b = b.point([min(255, round(v * gain)) for v in range(256)])
        return ImageStat.Stat(ImageChops.difference(a, b), mask).mean[0] / contrast

    candidates = [(score(0, 0), 0, 0)]
    for amount in range(1, 19):
        for dx, dy in DIRECTIONS.values():
            sx, sy = amount * dx, amount * dy
            candidates.append((score(sx, sy), sx, sy))
    return candidates


def motion(before, after, direction):
    if (direction not in DIRECTIONS or len(before.signature) != 224 * 104 or
            len(after.signature) != 224 * 104):
        return "unknown"
    from . import motion_stats
    candidates = motion_stats.scores(before.signature, after.signature)
    if candidates is None:
        candidates = _pillow_motion_scores(before.signature, after.signature)
    candidates.sort()
    best, sx, sy = candidates[0]
    # Provisional thresholds include the recorded 119→124 one-tile movement
    # with newly revealed shop terrain; they are not unseen-device calibration.
    if best > .45 or candidates[1][0] - best < .08:
        return "unknown"
    dx, dy = DIRECTIONS[direction]
    if sx == sy == 0:
        next_point = (dx, dy)
        if (before.tiles.get(next_point) == "door" and after.tiles.get(next_point) == "floor"
                and next_point in _gates(after.tiles)):
            return "door_opened"
        return "blocked"
    if (sx, sy) == (-9 * dx, -9 * dy):
        return "moved"
    if any((sx, sy) == (-n * dx, -n * dy) for n in range(1, 9)):
        return "tween"
    return "unexpected"
