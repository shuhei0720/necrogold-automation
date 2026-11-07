"""観測済みfloorの直交2入力と、方向に依存しない2次元変位照合。"""
import math

from PIL import Image, ImageChops, ImageStat

from . import shop_navigation as nav


_SIGNATURE_SIZE = (224, 104)
_DIAGONALS = tuple((x, y) for cx in (-9, 9) for cy in (-9, 9)
                   for x in range(cx-1, cx+2) for y in range(cy-1, cy+2))
_GEOMETRY_SHIFTS = ((0, 0),) + tuple((n*dx, n*dy) for n in (1, 2)
                    for dx, dy in nav.DIRECTIONS.values()) + tuple(
                    (x, y) for x in (-1, 1) for y in (-1, 1))


def _point(value):
    return (type(value) is tuple and len(value) == 2
            and all(type(v) is int for v in value))


def snapshot(scene):
    """待機中のSceneのin-place変更も検出できる、固定内容のtoken材料。"""
    if (not isinstance(scene, nav.Scene) or type(scene.tiles) is not dict
            or type(scene.gold) is not set or type(scene.protected) is not set
            or scene.goods not in ('unknown', 'partial', 'visible')
            or type(scene.signature) is not bytes
            or any(not _point(p) or type(kind) is not str for p, kind in scene.tiles.items())
            or any(not _point(p) for p in scene.gold | scene.protected)
            or any(scene.tiles.get(p) != 'gold' for p in scene.gold)):
        return None
    return (tuple(sorted(scene.tiles.items())), frozenset(scene.gold), scene.goods,
            frozenset(scene.protected), scene.signature)


def _noncollinear(gold, stones):
    for gx, gy in gold:
        vectors = [(x-gx, y-gy) for x, y in stones if (x, y) != (gx, gy)]
        if vectors:
            ax, ay = vectors[0]
            if any(ax*by != ay*bx for bx, by in vectors[1:]):
                return True
    return False


def mixed_pair(scene, decision, position=(0, 0), entrance=None):
    """各入力の不受理を含む全到達セルが安全な、選択済み経路の先頭2方向。"""
    if (snapshot(scene) is None or len(scene.signature) != 224*104
            or scene.goods != 'unknown' or not scene.gold
            or type(decision) is not dict
            or decision.get('reason') not in ('approach_gate', 'observed_floor_vantage')
            or type(decision.get('direction')) is not str
            or decision['direction'] not in nav.DIRECTIONS):
        return ()
    if type(position) is list:
        position = tuple(position)
    if not _point(position):
        return ()
    target = decision.get('target')
    if type(target) is list:
        target = tuple(target)
    if not _point(target):
        return ()
    routed, _ = nav._route_scene(scene, position, entrance)
    if routed is None or not _noncollinear(scene.gold,
            {p for p, kind in scene.tiles.items() if kind == 'stone'}):
        return ()
    paths = (nav._gate_paths(routed)[0] if decision['reason'] == 'approach_gate'
             else nav._floor_paths(routed))
    directions = paths.get(target, ())[:2]
    if (len(directions) != 2 or directions[0] != decision['direction']
            or sum(a*b for a, b in zip(nav.DIRECTIONS[directions[0]],
                                      nav.DIRECTIONS[directions[1]])) != 0):
        return ()
    reachable = {(0, 0)}
    gates = nav._gates(routed.tiles)
    for direction in (None, *directions):
        if direction is not None:
            dx, dy = nav.DIRECTIONS[direction]
            reachable |= {(x+dx, y+dy) for x, y in reachable}
        if any(routed.tiles.get(p) != 'floor' or p in gates or p in routed.protected
               or any(nav._add(p, delta) in routed.protected for delta in nav.DIRECTIONS.values())
               for p in reachable):
            return ()
    return directions


def _diagonal_scores(before_signature, after_signature):
    """追加36候補だけ既存Pillow式を使う。旧73候補のnative計算は変更しない。"""
    old = Image.frombytes('L', _SIGNATURE_SIZE, before_signature)
    new = Image.frombytes('L', _SIGNATURE_SIZE, after_signature)
    valid = Image.new('L', _SIGNATURE_SIZE)
    valid.paste(255, (40, 20, 179, 79))
    valid.paste(0, (90, 36, 139, 79))
    active_old = ImageChops.darker(old.point([255 if v > 6 else 0 for v in range(256)]), valid)
    active_new = ImageChops.darker(new.point([255 if v > 6 else 0 for v in range(256)]), valid)
    result = []
    for sx, sy in _DIAGONALS:
        box = (max(0, -sx), max(0, -sy), min(224, 224-sx), min(104, 104-sy))
        other = (box[0]+sx, box[1]+sy, box[2]+sx, box[3]+sy)
        a, b = old.crop(box), new.crop(other)
        mask = ImageChops.darker(active_old.crop(box), active_new.crop(other))
        value = float('inf')
        if mask.histogram()[255] >= 300:
            sa, sb = ImageStat.Stat(a, mask), ImageStat.Stat(b, mask)
            contrast = (sa.stddev[0] + sb.stddev[0]) / 2
            if contrast >= 2.5 and min(sa.mean[0], sb.mean[0]) >= 6:
                gain = max(.65, min(1.55, sa.mean[0] / sb.mean[0]))
                b = b.point([min(255, round(v*gain)) for v in range(256)])
                value = ImageStat.Stat(ImageChops.difference(a, b), mask).mean[0] / contrast
        result.append((value, sx, sy))
    return result


def _candidate_scores(old, new):
    from . import motion_stats
    axis = motion_stats.scores(old, new)
    if axis is None:
        axis = nav._pillow_motion_scores(old, new)
    return sorted(list(axis) + _diagonal_scores(old, new))


def _unique_landmarks(before, after, sx, sy):
    if sx % 9 or sy % 9 or (sx//9, sy//9) not in _GEOMETRY_SHIFTS or not before.gold:
        return False
    old_stones = {p for p, kind in before.tiles.items() if kind == 'stone'}
    new_stones = {p for p, kind in after.tiles.items() if kind == 'stone'}
    matches = []
    for tx, ty in _GEOMETRY_SHIFTS:
        if not {(x+tx, y+ty) for x, y in before.gold}.issubset(after.gold):
            continue
        if any(after.tiles.get((x+tx, y+ty), 'unknown') not in ('stone', 'unknown')
               for x, y in old_stones):
            continue
        if any(before.tiles.get((x-tx, y-ty), 'unknown') not in ('stone', 'unknown')
               for x, y in new_stones):
            continue
        supported = {(x, y) for x, y in old_stones if (x+tx, y+ty) in new_stones}
        if _noncollinear(before.gold, supported):
            matches.append((tx, ty))
    return matches == [(sx//9, sy//9)]


def motion(before, after, directions):
    """実送信prefixを照合し、確認したplayer変位だけ返す。unknownに変位を作らない。"""
    answer = {'motion': 'unknown', 'delta': None}
    if (type(directions) is not tuple or not 1 <= len(directions) <= 2
            or any(type(d) is not str or d not in nav.DIRECTIONS for d in directions)
            or snapshot(before) is None or snapshot(after) is None
            or len(before.signature) != 224*104 or len(after.signature) != 224*104):
        return answer
    if len(directions) == 1 or directions[0] == directions[1]:
        outcome = nav.motion(before, after, directions[0], expected_steps=len(directions))
        delta = None
        if outcome == 'moved':
            dx, dy = nav.DIRECTIONS[directions[0]]
            delta = (dx*len(directions), dy*len(directions))
        elif outcome == 'partial':
            delta = nav.DIRECTIONS[directions[0]]
        elif outcome in ('blocked', 'door_opened', 'terrain_opened'):
            delta = (0, 0)
        return {'motion': outcome, 'delta': delta}
    dx, dy = nav.DIRECTIONS[directions[0]]
    ex, ey = nav.DIRECTIONS[directions[1]]
    if dx*ex + dy*ey != 0:
        return answer
    views = [nav._motion_view(scene.signature, full_texture=True) for scene in (before, after)]
    candidates = _candidate_scores(views[0][0], views[1][0])
    best, sx, sy = candidates[0]
    if (not math.isfinite(best) or best > .45 or candidates[1][0]-best < .08
            or not _unique_landmarks(before, after, sx, sy)):
        return answer
    textures = [nav._texture_mask(view[1]) for view in views]
    support, bad, matched, box = nav._texture_match(
        *textures, views[0][2], views[1][2], sx, sy)
    if support < 300 or 20*bad > support:
        return answer
    full = Image.new('L', _SIGNATURE_SIZE)
    full.paste(matched, box[:2])
    if sum(full.crop(region).histogram()[255] >= 100
           for region in ((40, 20, 179, 36), (40, 36, 90, 79), (139, 36, 179, 79))) < 2:
        return answer
    for _, tx, ty in candidates[1:]:
        count, opposite, _, _ = nav._texture_match(
            *textures, views[0][2], views[1][2], tx, ty)
        if count >= 300 and 20*(opposite*support-bad*count) < 3*count*support:
            return answer
    delta = (-sx//9, -sy//9)
    expected = (dx+ex, dy+ey)
    outcome = ('moved' if delta == expected else 'blocked' if delta == (0, 0)
               else 'partial' if delta in (nav.DIRECTIONS[directions[0]], nav.DIRECTIONS[directions[1]])
               else 'unexpected')
    return {'motion': outcome, 'delta': delta}
