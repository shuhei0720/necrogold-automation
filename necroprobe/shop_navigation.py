"""TEST-016: 原寸36px格子と一入力ごとの画像確認による限定歩行。

既知画像に対する暫定規則。未知の配置/暗さでの精度、iSHでの速度、
実入力の向きは未検証。unknownは床にも商品なしにも置き換えない。
画像全体のresize/rotation、旧R12のimport、ネットワーク操作は行わない。
"""
from collections import deque
import heapq
import math
from itertools import count
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


def _merchandise(image, gray, channels, sign_mask=None):
    """看板候補と同一baselineの価格3列、各商品画素を別々に要求。"""
    if sign_mask is None:sign_mask = _colour_mask(channels, sign=True)
    peaks = _peaks(sign_mask) if sign_mask.getbbox() else []
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
        if kind not in ("floor", "door", "dirt", "stone", "wood"):
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
    rgb = image.tobytes()
    fast_stats = navigation_stats.scan(rgb)
    colours = navigation_stats.colours(rgb)
    channels = image.split()
    gold_mask = _colour_mask(channels) if colours is None else None
    sign_mask = Image.frombytes("L", SIZE, colours[1]) if colours is not None else None
    if sign_mask is not None:
        for box in _HUD:sign_mask.paste(0, box)
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
            gold_pixels = (colours[0][(j+5)*23+i+11] if colours is not None
                           else gold_mask.crop(box).histogram()[255])
            if gold_pixels >= 280:
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
            elif (35 <= r <= 140 and g >= 8 and 18*r <= 100*g <= 42*r
                  and 100*b <= 25*r
                  and (spread_enough if spread_enough is not None else max(stats.stddev) >= 2)):
                tiles[point] = "wood"
    for point in _gates(tiles):
        if tiles[point] in ("dirt", "stone", "wood"):
            tiles[point] = "door"
    # 木色だけでは扉にしない。現在見える金壁に両側を挟まれたセルだけ。
    tiles = {p:kind for p,kind in tiles.items() if kind != "wood"}
    goods, items = _merchandise(image, gray, channels, sign_mask)
    protected = set(items)
    for point in items:
        protected.update(_add(point, delta) for delta in DIRECTIONS.values())
        tiles[point] = "item"
    # Direct sparse sampling keeps 36px=9 samples, 32px tween=8 samples. This
    # neither stretches the image nor invents interpolated image pixels.
    raw = gray.tobytes()
    signature = b"".join(raw[y * SIZE[0]:(y + 1) * SIZE[0]:4] for y in range(0, SIZE[1], 4))
    return Scene(tiles, {p for p, kind in tiles.items() if kind == "gold"}, goods, protected, signature)


def _floor_paths(scene):
    """chooseと2入力判定で、同じ最短経路と方向の優先順を使う。"""
    paths = {(0, 0): ()}
    queue = deque([(0, 0)])
    while queue:
        point = queue.popleft()
        for name, delta in DIRECTIONS.items():
            nxt = _add(point, delta)
            if nxt not in paths and nxt not in scene.protected and scene.tiles.get(nxt) == "floor":
                paths[nxt] = paths[point] + (name,)
                queue.append(nxt)
    return paths


def _gate_paths(scene):
    """観測済み入口へだけ茶壁を掘る。床1入力、茶壁は掘り+移動の2入力。"""
    paths={(0,0):()};costs={(0,0):0};serial=count();queue=[(0,next(serial),(0,0))]
    while queue:
        cost,_,point=heapq.heappop(queue)
        if cost!=costs[point]:continue
        for name,delta in DIRECTIONS.items():
            nxt=_add(point,delta);kind=scene.tiles.get(nxt)
            if nxt in scene.protected or kind not in ("floor","dirt"):continue
            total=cost+(2 if kind=="dirt" else 1)
            if total<costs.get(nxt,float("inf")):
                paths[nxt]=paths[point]+(name,);costs[nxt]=total
                heapq.heappush(queue,(total,next(serial),nxt))
    return paths,costs


def closed_gate(scene, direction):
    """閉扉の識別。2入力の許可条件と分け、単発開扉への縮退を防ぐ。"""
    if not isinstance(scene, Scene) or not isinstance(direction, str) or direction not in DIRECTIONS:
        return False
    target = DIRECTIONS[direction]
    return scene.tiles.get(target) == "door" and target in _gates(scene.tiles)


def closed_gate_entry(scene, direction):
    """観測済みの閉じた商店扉だけ、開扉と入口への1歩を続けて許可する。"""
    if (not closed_gate(scene, direction) or scene.goods not in ("unknown", "partial")
            or scene.tiles.get((0, 0)) != "floor"):
        return False
    target = DIRECTIONS[direction]
    return not any(_add(point, delta) in scene.protected
                   for point in ((0, 0), target) for delta in ((0, 0), *DIRECTIONS.values()))


def entered_gate(before, after, direction, position, expected_steps, outcome, door_sequence=False):
    """開いた入口への1歩を地形で確認した時だけ、店内へ進む向きを記憶。"""
    if (not isinstance(before, Scene) or not isinstance(after, Scene)
            or outcome != "moved" or expected_steps != (2 if door_sequence else 1) or direction not in DIRECTIONS):
        return None
    if door_sequence and not closed_gate_entry(before, direction):
        return None
    delta = DIRECTIONS[direction]
    if (before.tiles.get(delta) != ("door" if door_sequence else "floor") or after.tiles.get((0, 0)) != "floor"
            or delta not in _gates(before.tiles) or (0, 0) not in _gates(after.tiles)
            or delta in before.protected or (0, 0) in after.protected):
        return None
    return {"gate": _add(position, delta), "direction": direction}


def _route_scene(scene, position, entrance):
    """進入後の経路だけを絞る。未知セルの補完や元Sceneの変更はしない。"""
    if entrance is None:
        return scene, None
    if (type(entrance) is not dict or set(entrance) != {"gate", "direction"}
            or not isinstance(entrance["direction"], str) or entrance["direction"] not in DIRECTIONS
            or type(entrance["gate"]) not in (tuple, list) or len(entrance["gate"]) != 2
            or any(type(v) is not int for v in entrance["gate"])
            or type(position) not in (tuple, list) or len(position) != 2
            or any(type(v) is not int for v in position)):
        return None, None
    dx, dy = DIRECTIONS[entrance["direction"]]
    gate = (entrance["gate"][0] - position[0], entrance["gate"][1] - position[1])
    if gate[0]*dx + gate[1]*dy > 0:  # 記録した入口より外側なら整合しない。
        return None, None
    # 通過済み入口へ後退しない。横移動は可、未知の店内しかなければ停止。
    # 金壁は通行不可の目印として保持。横向き入口の両脇を失うと2入力が扉を越える。
    tiles = {p:kind for p,kind in scene.tiles.items() if kind == "gold" or p[0]*dx + p[1]*dy >= 0}
    return Scene(tiles, scene.gold, scene.goods, scene.protected, scene.signature), gate


def choose(scene, position=(0, 0), visits=None, entrance=None):
    def result(direction=None, reason="no_observed_route", target=None):
        return {"direction": direction, "reason": reason, "target": target}
    if scene.goods == "visible":
        return result(reason="goods_visible")
    if any(delta in scene.protected for delta in DIRECTIONS.values()) or (0, 0) in scene.protected:
        return result(reason="goods_adjacent_controls_unverified")
    if not scene.gold or scene.tiles.get((0, 0)) != "floor":
        return result(reason="no_visible_gold_or_origin")
    scene, passed_gate = _route_scene(scene, position, entrance)
    if scene is None:
        return result(reason="entrance_unconfirmed")
    visits = visits or {}
    paths,costs = _gate_paths(scene)
    options = []
    for gate, sides in _gates(scene.tiles).items():
        if gate == passed_gate or gate in scene.protected:
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
                options.append((costs[near], path[0], near))
    if options:
        _, direction, target = min(options)
        reason="dig_single_probe" if scene.tiles.get(DIRECTIONS[direction])=="dirt" else "approach_gate"
        return result(direction, reason, target)
    # A partial gold wall may require moving around a corner. Only known floor
    # is eligible; the smallest distance-to-gold and revisit penalty guide it.
    nearest_gold=min(scene.gold,key=lambda p:(_distance((0,0),p),p))
    axis=1 if abs(nearest_gold[1])>=abs(nearest_gold[0]) else 0
    for target, path in _floor_paths(scene).items():
        if not path or target == passed_gate:
            continue
        gap = min(_distance(target, gold) for gold in scene.gold)
        seen = visits.get(_add(position, target), 0)
        # 同じ主スコアなら金壁側へ深く進める床を優先し、横へ行き過ぎない。
        # 非同点・visit加算・床限定は変えず、未知の入口や暗い床を補完しない。
        axial_gap=abs(target[axis]-nearest_gold[axis])
        options.append((3 * gap + len(path) + 4 * seen, axial_gap, path[0], target))
    if options:
        _, _, direction, target = min(options)
        return result(direction, "observed_floor_vantage", target)
    return result()


def burst_count(scene, decision, position=(0, 0), entrance=None, limit=2):
    """選択済み経路の安全な直線部分だけを、指定上限まで続ける。"""
    if type(limit) is not int or not 1 <= limit <= 4:
        return 1
    if (not isinstance(decision, dict) or scene.goods in ("partial", "visible")
            or not scene.gold or scene.tiles.get((0, 0)) != "floor"):
        return 1
    direction, target = decision.get("direction"), decision.get("target")
    if (not isinstance(direction, str) or direction not in DIRECTIONS
            or decision.get("reason") not in ("approach_gate", "observed_floor_vantage")
            or not isinstance(target, (tuple, list)) or len(target) != 2
            or any(type(value) is not int for value in target)):
        return 1
    scene, _ = _route_scene(scene, position, entrance)
    if scene is None:
        return 1
    paths = _gate_paths(scene)[0] if decision.get("reason") == "approach_gate" else _floor_paths(scene)
    path = paths.get(tuple(target), ())
    gates = _gates(scene.tiles)
    point = (0, 0); count = 0
    for step in range(min(limit, len(path)) + 1):
        if (point in scene.protected
                or any(_add(point, delta) in scene.protected for delta in DIRECTIONS.values())):
            break
        if step and (path[step-1] != direction or scene.tiles.get(point) != "floor" or point in gates):
            break
        count = step
        point = _add(point, DIRECTIONS[direction])
    return max(1, count)


def _pillow_motion_scores(before_signature, after_signature, extra=False):
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

    candidates = [] if extra else [(score(0, 0), 0, 0)]
    for amount in (range(19, 37) if extra else range(1, 19)):
        for dx, dy in DIRECTIONS.values():
            sx, sy = amount * dx, amount * dy
            candidates.append((score(sx, sy), sx, sy))
    return candidates


def _motion_view(signature, full_texture=False):
    """明るさの緩やかな変化を除く。元画像・原署名は変更しない。"""
    raw = Image.frombytes('L', _SIGNATURE_SIZE, signature)
    active = raw.point([0] * 7 + [255] * 249)
    detail = ImageChops.subtract(raw, raw.filter(ImageFilter.BoxBlur(1)), offset=128)
    normalized = ImageChops.multiply(detail, active).tobytes()
    # 無地の照明境界だけが動いた場合を除外するため、原画側の質感を要求。
    # 3x3中央値から3以上離れた細部だけを支持票にする。
    # 単調な明暗勾配や、ぼけた照明の境界を質感と数えない。
    median = raw.filter(ImageFilter.MedianFilter(3))
    detail_mask = ImageChops.difference(raw, median)
    texture = ImageChops.darker(detail_mask.point([0] * 3 + [255] * 253), active)
    positive = ImageChops.subtract(raw, median).point([0] * 3 + [255] * 253)
    return normalized, texture if full_texture else _texture_mask(texture), positive


def _texture_mask(texture, expanded=False):
    valid = Image.new('L', _SIGNATURE_SIZE)
    valid.paste(255, (40, 20, 179, 79))
    if expanded:
        # プレイヤーと右側の説明文を除外。中央値フィルタの影響も1px外まで除く。
        valid.paste(0, (103, 43, 122, 61))
        valid.paste(0, (115, 38, 154, 80))
    else:
        valid.paste(0, (90, 36, 139, 79))
    return ImageChops.darker(texture, valid)


def _translated_closed_gate(before, after, sx, sy):
    """強度比較が不成立の時だけ使う、金壁全体と閉扉の独立な対応。"""
    if (sx == sy == 0 or sx % 9 or sy % 9 or len(before.gold) < 2
            or {(x + sx//9, y + sy//9) for x,y in before.gold} != after.gold):
        return False
    old_gates, new_gates = _gates(before.tiles), _gates(after.tiles)
    return any(before.tiles.get(p) == "door"
               and after.tiles.get((p[0]+sx//9, p[1]+sy//9)) == "door"
               and (p[0]+sx//9, p[1]+sy//9) in new_gates for p in old_gates)


def _texture_match(old_texture, new_texture, old_positive, new_positive, sx, sy):
    box = (max(0, -sx), max(0, -sy), min(224, 224 - sx), min(104, 104 - sy))
    other = (box[0] + sx, box[1] + sy, box[2] + sx, box[3] + sy)
    matched = ImageChops.darker(old_texture.crop(box), new_texture.crop(other))
    support = matched.histogram()[255]
    opposite = ImageChops.darker(matched, ImageChops.difference(
        old_positive.crop(box), new_positive.crop(other))).histogram()[255]
    return support, opposite, matched, box


def _structural_motion(before, after, candidates, old_texture, new_texture, old_positive, new_positive):
    _, sx, sy = candidates[0]
    if not _translated_closed_gate(before, after, sx, sy):
        return False
    support, opposite, matched, box = _texture_match(
        old_texture, new_texture, old_positive, new_positive, sx, sy)
    if support < 300 or 20*opposite > support:  # 95%以上の細部が同じ明暗関係。
        return False
    full = Image.new('L', _SIGNATURE_SIZE)
    full.paste(matched, box[:2])
    regions = ((40,20,179,36), (40,36,90,79), (139,36,179,79))
    if sum(full.crop(region).histogram()[255] >= 100 for region in regions) < 2:
        return False
    # 低い強度順位や静止候補も含めて照合。一部の領域だけの対応を採用しない。
    for _, tx, ty in candidates[1:]:
        count, bad, _, _ = _texture_match(old_texture, new_texture, old_positive, new_positive, tx, ty)
        if count >= 300 and 20*(bad*support-opposite*count) < 3*count*support:
            return False  # 符号一致率の差が0.15未満。
    return True


def _unique_gate_shift(before, after, max_steps=2):
    """新しく見えた金壁は許容し、既知の金壁と入口の対応を一意に決める。"""
    if len(before.gold) < 2:
        return None
    old_gates, new_gates = _gates(before.tiles), _gates(after.tiles)
    shifts = [(0, 0)] + [(dx*n, dy*n) for n in range(1, max_steps+1) for dx,dy in DIRECTIONS.values()]
    matches = []
    for tx, ty in shifts:
        if not {(x+tx, y+ty) for x,y in before.gold}.issubset(after.gold):
            continue
        if any((p[0]+tx, p[1]+ty) in new_gates and
               (before.tiles.get(p), after.tiles.get((p[0]+tx, p[1]+ty))) in
               (("door", "door"), ("door", "floor"), ("floor", "floor")) for p in old_gates):
            matches.append((9*tx, 9*ty))
    return matches[0] if len(matches) == 1 else None


def _corridor_motion(before, after, candidates, old_texture, new_texture, old_positive, new_positive):
    """通常の質感範囲が狭すぎる入口だけ、地形対応と追加の細部で裏付ける。"""
    _, sx, sy = candidates[0]
    if _unique_gate_shift(before, after, max_steps=4 if len(candidates)>73 else 2) != (sx, sy):
        return False
    old_texture, new_texture = _texture_mask(old_texture, True), _texture_mask(new_texture, True)
    support, opposite, _, _ = _texture_match(old_texture, new_texture, old_positive, new_positive, sx, sy)
    if support < 300 or 20*opposite > support:
        return False
    # 静止・反復模様も候補に含め、一部の明暗変化だけで移動を確定しない。
    for _, tx, ty in candidates[1:]:
        count, bad, _, _ = _texture_match(old_texture, new_texture, old_positive, new_positive, tx, ty)
        if count >= 300 and 20*(bad*support-opposite*count) < 3*count*support:
            return False
    return True


def motion(before, after, direction, expected_steps=1):
    if (type(expected_steps) is not int or expected_steps not in (1, 2, 3, 4)
            or direction not in DIRECTIONS or len(before.signature) != 224 * 104 or
            len(after.signature) != 224 * 104):
        return "unknown"
    from . import motion_stats
    old, old_raw_texture, old_positive = _motion_view(before.signature, full_texture=True)
    new, new_raw_texture, new_positive = _motion_view(after.signature, full_texture=True)
    old_texture, new_texture = _texture_mask(old_raw_texture), _texture_mask(new_raw_texture)
    candidates = motion_stats.scores(old, new)
    if candidates is None:
        candidates = _pillow_motion_scores(old, new)
    if expected_steps > 2:
        candidates += _pillow_motion_scores(old, new, extra=True)
    candidates.sort()
    best, sx, sy = candidates[0]
    # 元の閾値は維持するが、正規化後の未知実画像での精度保証ではない。
    if not math.isfinite(best) or candidates[1][0] - best < .08:
        return "unknown"
    if best > .45 and not _structural_motion(
            before, after, candidates, old_texture, new_texture, old_positive, new_positive):
        return "unknown"
    support, opposite, _, _ = _texture_match(old_texture, new_texture, old_positive, new_positive, sx, sy)
    if support < 300:
        if best > .45 or not _corridor_motion(before, after, candidates,
                old_raw_texture, new_raw_texture, old_positive, new_positive):
            return 'unknown'
    # 質感が存在するだけでは不十分。同じ変位で明暗の細部が対応すること。
    # 静止した床の上で照明だけが移る場合は、独立な質感の符号が揃わない。
    elif 4 * opposite > support:
        return 'unknown'
    dx, dy = DIRECTIONS[direction]
    if sx == sy == 0:
        next_point = (dx, dy)
        if (expected_steps == 1 and before.tiles.get(next_point) == "door"
                and after.tiles.get(next_point) == "floor"
                and next_point in _gates(after.tiles)):
            return "door_opened"
        if (expected_steps == 1 and before.tiles.get(next_point) == "dirt"
                and after.tiles.get(next_point) == "floor"
                and next_point not in before.protected and next_point not in after.protected):
            return "terrain_opened"
        return "blocked"
    if (sx, sy) == (-9 * expected_steps * dx, -9 * expected_steps * dy):
        return "moved"
    if any((sx, sy) == (-9*n*dx, -9*n*dy) for n in range(1, expected_steps)):
        return "partial"
    if any((sx, sy) == (-n * dx, -n * dy) for n in range(1, 9 * expected_steps)):
        return "tween"
    return "unexpected"
