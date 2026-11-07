"""TEST041: 観測済みの曲がり角2入力。画像再生と模擬制御は実機速度ではない。"""
from copy import deepcopy
import unittest
import hashlib
import math
import os
from pathlib import Path
import random
from unittest.mock import patch

from PIL import Image

from necroprobe import route_sequence as routes, motion_stats

from necroprobe import shop_navigation as nav, shop_walk as walk
import test_shop_walk as old


def route_scene(goods='unknown'):
    tiles = {(x, y): 'floor' for x in range(-3, 2) for y in range(-3, 2)}
    tiles.update({(-3, -2): 'gold', (2, 2): 'stone', (4, 1): 'stone'})
    return nav.Scene(tiles, {(-3, -2)}, goods, set(), bytes(224*104))


def observation(scene):
    result = old.obs()
    result['_extra']['scene'] = scene
    return result


class RouteWalkEntryTests(unittest.TestCase):
    def test_public_walk_uses_safe_corner_pair_before_next_observation(self):
        class ReadyCorner(old.Fake):
            def goods(self, frame):
                return frame['_extra']['scene'].goods
            def choose(self, frame):
                return {'direction': 'left', 'reason': 'observed_floor_vantage', 'target': (-1, -1)}
            def burst_count(self, frame, decision, remaining):
                return nav.burst_count(frame['_extra']['scene'], decision, limit=2)
            def route_directions(self, frame, decision, remaining):
                # Pure planner safety and metadata are tested separately below.
                return ('left', 'up')
            def perform(self, action, frame, model=None, count=1, directions=None):
                if action in walk.MOVE_POINTS:
                    self.requests.append(tuple(directions) if directions is not None else (action,) * count)
                return super().perform(action, frame, model, count)
        before = observation(route_scene())
        after = observation(route_scene('visible'))
        driver = ReadyCorner([before, after])
        driver.requests = []
        driver.state['lead_confirmed'] = True
        walk.walk(driver)
        self.assertEqual([('left', 'up')], driver.requests)
        self.assertTrue(driver.state['goods_visible'])
        self.assertTrue(driver.state['paused'])



def synthetic(directions=('left', 'up')):
    before = route_scene()
    rng = random.Random(41041)
    before.signature = bytes(rng.randrange(20, 100) for _ in range(224 * 104))
    dx = sum(nav.DIRECTIONS[d][0] for d in directions)
    dy = sum(nav.DIRECTIONS[d][1] for d in directions)
    after = deepcopy(before)
    after.tiles = {(x-dx, y-dy): kind for (x, y), kind in before.tiles.items()}
    after.gold = {(x-dx, y-dy) for x, y in before.gold}
    shifted = Image.new('L', (224, 104))
    shifted.paste(Image.frombytes('L', shifted.size, before.signature), (-9*dx, -9*dy))
    after.signature = shifted.tobytes()
    return before, after


def actual040(names=('run-101.jpg', 'run-103.jpg')):
    folder = os.environ.get('NECRO_TEST040_FRAMES')
    if not folder:
        raise unittest.SkipTest('external TEST040 frames not supplied')
    digests = {
        'run-101.jpg': '7171fb1226e34156280a685f1d43fae67c319c66c982b85836770f7a28f44cf7',
        'run-102.jpg': 'fa5b58668bbe2b1ec06088af73406c089d2bd5b6e227e9444883898696c98f73',
        'run-103.jpg': 'bfc3f392d4dd1e3f927033ddf2543735c591a8c8407609a7a19dc3d94b3eba5d',
    }
    result = []
    for name in names:
        path = Path(folder) / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digests[name]:
            raise AssertionError('TEST040 evidence hash mismatch')
        with Image.open(path) as image:
            result.append(nav.scan(image.convert('RGB')))
    return result


class MixedPlannerTests(unittest.TestCase):
    def test_every_perpendicular_order_has_complete_omission_safe_footprint(self):
        for first, a in nav.DIRECTIONS.items():
            for second, b in nav.DIRECTIONS.items():
                if a[0]*b[0]+a[1]*b[1] != 0:
                    continue
                tiles = {(0, 0): 'floor', a: 'floor', b: 'floor',
                         (a[0]+b[0], a[1]+b[1]): 'floor',
                         (4, 3): 'gold', (5, 1): 'stone', (2, 4): 'stone'}
                scene = nav.Scene(tiles, {(4, 3)}, 'unknown', set(), bytes(224*104))
                # Select each order explicitly; the omission safety check itself is real.
                # A separate actual040 test covers production BFS selection.
                target = (a[0]+b[0], a[1]+b[1])
                path = (first, second)
                decision = {'direction': first, 'reason': 'observed_floor_vantage', 'target': target}
                with patch.object(nav, '_floor_paths', return_value={target: path}):
                    self.assertEqual(path, routes.mixed_pair(scene, decision))
                    for omitted in (a, b):
                        for bad in ('dirt', 'stone', 'door', 'unknown', None):
                            broken = deepcopy(scene)
                            if bad is None: broken.tiles.pop(omitted)
                            else: broken.tiles[omitted] = bad
                            self.assertEqual((), routes.mixed_pair(broken, decision), (path, omitted, bad))

    def test_protected_adjacent_cells_and_gates_are_rejected(self):
        scene = route_scene()
        decision = {'direction': 'left', 'reason': 'observed_floor_vantage', 'target': (-1, -1)}
        path = routes.mixed_pair(scene, decision)
        self.assertEqual(('left', 'up'), path)
        for point in ((0, 0), (-1, 0), (0, -1), (-1, -1), (-2, -1), (0, -2), (1, 0)):
            broken = deepcopy(scene); broken.protected.add(point)
            self.assertEqual((), routes.mixed_pair(broken, decision), point)
        gated = deepcopy(scene)
        gated.tiles[(-2, -1)] = gated.tiles[(0, -1)] = 'gold'
        gated.gold.update({(-2, -1), (0, -1)})
        self.assertIn((-1, -1), nav._gates(gated.tiles))
        self.assertEqual((), routes.mixed_pair(gated, decision))

    def test_partial_goods_anchors_invalid_decisions_and_short_paths_do_not_batch(self):
        source = route_scene()
        decision = {'direction': 'left', 'reason': 'observed_floor_vantage', 'target': (-1, -1)}
        for goods in ('partial', 'visible'):
            scene = deepcopy(source); scene.goods = goods
            self.assertEqual((), routes.mixed_pair(scene, decision))
        for bad in ({}, None, dict(decision, direction=[]), dict(decision, target=[True, -1]),
                    dict(decision, target=(-1, 0)), dict(decision, target=(-2, 0)),
                    dict(decision, direction='right'), dict(decision, reason='dig_single_probe')):
            self.assertEqual((), routes.mixed_pair(source, bad), bad)
        for fault in ('gold', 'one_stone', 'collinear'):
            scene = deepcopy(source)
            if fault == 'gold': scene.gold.clear()
            elif fault == 'one_stone': scene.tiles.pop((4, 1))
            else:
                scene.tiles.pop((2, 2)); scene.tiles.pop((4, 1))
                scene.tiles.update({(-1, -2): 'stone', (1, -2): 'stone'})
            self.assertEqual((), routes.mixed_pair(scene, decision), fault)
        self.assertEqual((), routes.mixed_pair(source, decision, position=(True, 0)))
        self.assertEqual((), routes.mixed_pair(source, decision,
                         position=(0, 0), entrance={'gate': (0, 1), 'direction': 'down'}))

    def test_public_planner_rejects_incomplete_motion_signature(self):
        source = route_scene()
        source.signature = bytes(224 * 104)
        decision = {'direction':'left','reason':'observed_floor_vantage','target':(-1,-1)}
        self.assertEqual(('left','up'),routes.mixed_pair(source,decision))
        source.signature = b'short'
        self.assertEqual((),routes.mixed_pair(source,decision))

    def test_snapshot_detects_in_place_mutation_without_changing_original_scene(self):
        scene = route_scene(); saved = deepcopy(scene); token = routes.snapshot(scene)
        self.assertEqual(saved, scene)
        for fault in ('tiles', 'gold', 'goods', 'protected', 'signature'):
            changed = deepcopy(scene)
            if fault == 'tiles': changed.tiles[(0, 0)] = 'dirt'
            elif fault == 'gold': changed.gold.clear()
            elif fault == 'goods': changed.goods = 'visible'
            elif fault == 'protected': changed.protected.add((0, 0))
            else: changed.signature = b'new'
            self.assertNotEqual(token, routes.snapshot(changed), fault)
        self.assertIsNone(routes.snapshot(None))

    def test_actual040_corner_is_safe_but_omission_path_over_dirt_is_not(self):
        first, second, third = actual040(('run-101.jpg', 'run-102.jpg', 'run-103.jpg'))
        self.assertEqual(('left', 'up'), routes.mixed_pair(first, nav.choose(first)))
        self.assertEqual('dirt', second.tiles[(-1, 0)])
        self.assertEqual((), routes.mixed_pair(second, nav.choose(second)))
        self.assertEqual((), routes.mixed_pair(third, nav.choose(third)))  # straight legacy path


class MixedMotionTests(unittest.TestCase):
    def test_full_diagonal_is_measured_independently_of_requested_pair(self):
        for first, a in nav.DIRECTIONS.items():
            for second, b in nav.DIRECTIONS.items():
                if a[0]*b[0]+a[1]*b[1] != 0: continue
                before, after = synthetic((first, second))
                expected = (a[0]+b[0], a[1]+b[1])
                self.assertEqual({'motion': 'moved', 'delta': expected},
                                 routes.motion(before, after, (first, second)))
                opposite = tuple(next(d for d, v in nav.DIRECTIONS.items() if v == (-x, -y))
                                 for x, y in (a, b))
                self.assertEqual({'motion': 'unexpected', 'delta': expected},
                                 routes.motion(before, after, opposite))

    def test_partial_blocked_and_single_actual_prefix_keep_only_measured_credit(self):
        before, partial = synthetic(('left',))
        self.assertEqual({'motion': 'partial', 'delta': (-1, 0)},
                         routes.motion(before, partial, ('left', 'up')))
        self.assertEqual({'motion': 'blocked', 'delta': (0, 0)},
                         routes.motion(before, before, ('left', 'up')))
        self.assertEqual({'motion': 'moved', 'delta': (-1, 0)},
                         routes.motion(before, partial, ('left',)))
        twice, after = synthetic(('left', 'left'))
        self.assertEqual({'motion': 'moved', 'delta': (-2, 0)},
                         routes.motion(twice, after, ('left', 'left')))
        self.assertEqual({'motion': 'unknown', 'delta': None},
                         routes.motion(before, partial, ('left', 'right')))

    def test_missing_conflicting_collinear_or_ambiguous_landmarks_reject(self):
        source, moved = synthetic()
        for fault in ('lost_gold', 'one_stone', 'forward_conflict', 'reverse_conflict',
                      'collinear', 'alias'):
            before, after = deepcopy(source), deepcopy(moved)
            if fault == 'lost_gold': after.gold.clear()
            elif fault == 'one_stone': after.tiles.pop((5, 2))
            elif fault == 'forward_conflict': before.tiles[(7, 0)] = 'stone'; after.tiles[(8, 1)] = 'floor'
            elif fault == 'reverse_conflict': before.tiles[(7, 0)] = 'floor'; after.tiles[(8, 1)] = 'stone'
            elif fault == 'collinear':
                before.tiles.pop((2, 2)); before.tiles.pop((4, 1))
                before.tiles.update({(-1, -2): 'stone', (1, -2): 'stone'})
                after.tiles = {(x+1, y+1): k for (x, y), k in before.tiles.items()}
            else:
                # Keep only observed landmarks so both alignments are coherent,
                # not rejected by an unrelated floor-label contradiction.
                before.tiles = {p:k for p,k in before.tiles.items() if k in ('gold','stone')}
                after.tiles = {p:k for p,k in after.tiles.items() if k in ('gold','stone')}
                after.tiles.update(before.tiles); after.gold.update(before.gold)
                for point in after.gold: after.tiles[point] = 'gold'
                for tx,ty in ((0,0),(1,1)):
                    self.assertTrue({(x+tx,y+ty) for x,y in before.gold}.issubset(after.gold))
                    support={p for p,k in before.tiles.items() if k=='stone'
                             and after.tiles.get((p[0]+tx,p[1]+ty))=='stone'}
                    self.assertTrue(routes._noncollinear(before.gold,support))
            self.assertEqual({'motion': 'unknown', 'delta': None},
                             routes.motion(before, after, ('left', 'up')), fault)

    def test_unknown_stone_destinations_do_not_supply_votes_or_create_conflicts(self):
        for reverse in (False, True):
            before, after = synthetic()
            if reverse:
                after.tiles[(8,1)]='stone';before.tiles[(7,0)]='unknown'
            else:
                before.tiles[(7,0)]='stone';after.tiles[(8,1)]='unknown'
            self.assertEqual({'motion':'moved','delta':(-1,-1)},routes.motion(before,after,('left','up')))
        before,after=synthetic();after.tiles[(5,2)]='unknown'
        self.assertEqual({'motion':'unknown','delta':None},routes.motion(before,after,('left','up')))

    def test_invalid_input_never_invents_a_displacement(self):
        before,after=synthetic()
        for directions in (None, (), ('left','up','right'), ['left','up'], (True,), ('left','bad')):
            self.assertEqual({'motion':'unknown','delta':None},routes.motion(before,after,directions))
        after.signature=b'short'
        self.assertEqual({'motion':'unknown','delta':None},routes.motion(before,after,('left','up')))
        before.tiles[(9,True)]='floor'
        self.assertTrue(routes.snapshot(before) is None)

    def test_all_109_scores_keep_old_73_and_include_every_diagonal_neighbor(self):
        before, after = synthetic()
        a, b = [nav._motion_view(s.signature)[0] for s in (before, after)]
        with patch.object(motion_stats, '_native', None):
            expected = sorted(nav._pillow_motion_scores(a, b))
            actual = routes._candidate_scores(a, b)
        self.assertEqual(109, len(actual))
        self.assertEqual(expected, sorted(row for row in actual if row[1] == 0 or row[2] == 0))
        diagonal = {(x, y) for _, x, y in actual if x and y}
        self.assertEqual({(x, y) for cx in (-9, 9) for cy in (-9, 9)
                          for x in range(cx-1, cx+2) for y in range(cy-1, cy+2)}, diagonal)

    def test_nonfinite_coarse_margin_threshold_and_neighbor_tween_are_bounded(self):
        before, after = synthetic()
        base = [(1.2, x, y) for _, x, y in routes._candidate_scores(
            nav._motion_view(before.signature)[0], nav._motion_view(after.signature)[0])]
        for best, runner, expected in ((.45, .53, 'moved'),
                (math.nextafter(.45, math.inf), .6, 'unknown'),
                (.2, math.nextafter(.28, 0), 'unknown'),
                (float('inf'), float('inf'), 'unknown')):
            rows = [(best if (x, y) == (9, 9) else runner if (x, y) == (0, 0) else v, x, y)
                    for v, x, y in base]
            with patch.object(routes, '_candidate_scores', return_value=sorted(rows)):
                self.assertEqual(expected, routes.motion(before, after, ('left', 'up'))['motion'])
        rows = sorted([(.1 if (x, y) == (8, 9) else v, x, y) for v, x, y in base])
        with patch.object(routes, '_candidate_scores', return_value=rows):
            self.assertEqual('unknown', routes.motion(before, after, ('left', 'up'))['motion'])

    def test_actual040_replay_has_unique_signed_diagonal_with_native_axis_parity(self):
        before, after = actual040()
        self.assertEqual({'motion': 'moved', 'delta': (-1, -1)},
                         routes.motion(before, after, ('left', 'up')))
        self.assertEqual({'motion': 'unexpected', 'delta': (-1, -1)},
                         routes.motion(before, after, ('right', 'down')))


class MixedNativeParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_motion_stats
        test_motion_stats.MotionStatsTests.setUpClass.__func__(cls)

    def test_actual040_all109_native_axis_and_pillow_scores_are_identical(self):
        before, after = actual040()
        old_view, new_view = [nav._motion_view(s.signature)[0] for s in (before, after)]
        with patch.object(motion_stats, '_native', None):
            expected = routes._candidate_scores(old_view, new_view)
        with patch.object(motion_stats, '_native', self.lib):
            self.assertEqual(expected, routes._candidate_scores(old_view, new_view))
            self.assertEqual({'motion': 'moved', 'delta': (-1, -1)},
                             routes.motion(before, after, ('left', 'up')))



class MixedTextureConfidenceTests(unittest.TestCase):
    def boundary(self, support=400, bad=20, competitor_count=400, competitor_bad=80,
                 regions=None, competitor=(0, 0)):
        before, after = synthetic()
        old, new = [nav._motion_view(s.signature)[0] for s in (before, after)]
        rows = [(0.2 if (x, y) == (9, 9) else 9.9 if (x, y) == competitor else 1.2, x, y)
                for _, x, y in routes._candidate_scores(old, new)]
        full = Image.new('L', (224, 104))
        amounts = (support//2, 0, support-support//2) if regions is None else regions
        for box, count in zip(((40,20,179,36), (40,36,90,79), (139,36,179,79)), amounts):
            points = [(x, y) for y in range(box[1], box[3]) for x in range(box[0], box[2])]
            for point in points[:count]: full.putpixel(point, 255)
        calls = []
        def match(*args):
            point = args[-2:]; calls.append(point)
            count, opposite = ((support, bad) if point == (9, 9) else
                               (competitor_count, competitor_bad) if point == competitor else (0, 0))
            return count, opposite, full, (0, 0, 224, 104)
        with patch.object(routes, '_candidate_scores', return_value=sorted(rows)), \
                patch.object(nav, '_texture_match', side_effect=match):
            result = routes.motion(before, after, ('left', 'up'))
        return result, calls

    def test_support_polarity_and_margin_exact_boundaries_are_preserved(self):
        for kwargs, expected in (
                ({'support':299, 'bad':0}, 'unknown'),
                ({'support':300, 'bad':15}, 'moved'),
                ({'bad':20}, 'moved'), ({'bad':21}, 'unknown'),
                ({'competitor_bad':80}, 'moved'), ({'competitor_bad':79}, 'unknown'),
                ({'competitor_count':299, 'competitor_bad':0}, 'moved'),
                ({'competitor_count':300, 'competitor_bad':0}, 'unknown')):
            with self.subTest(**kwargs):
                self.assertEqual(expected, self.boundary(**kwargs)[0]['motion'])

    def test_two_regions_and_all_109_texture_competitors_are_required(self):
        for amounts, expected in (((100,0,200),'moved'), ((99,0,201),'unknown'),
                                  ((300,0,0),'unknown'), ((0,100,200),'moved')):
            self.assertEqual(expected, self.boundary(support=300, bad=15, regions=amounts)[0]['motion'])
        result, calls = self.boundary()
        self.assertEqual('moved', result['motion'])
        self.assertEqual(109, len(set(calls)))
        self.assertEqual('unknown', self.boundary(competitor=(10,10), competitor_bad=0)[0]['motion'])
        self.assertEqual('unknown', self.boundary(competitor=(18,0), competitor_bad=0)[0]['motion'])

    def test_large_moving_object_cannot_override_stationary_texture(self):
        before, after = synthetic()
        rng = random.Random(41042)
        stationary = Image.new('L', (224, 104), 40)
        def texture(box):
            width, height = box[2]-box[0], box[3]-box[1]
            return Image.frombytes('L', (width,height),
                bytes(rng.randrange(20,100) for _ in range(width*height)))
        for box in ((44,65,85,73), (140,22,178,30)):
            stationary.paste(texture(box), box[:2])
        initial, changed = stationary.copy(), stationary.copy()
        for box in ((44,21,120,27), (45,39,85,47)):
            patch_image = texture(box)
            initial.paste(patch_image, box[:2])
            changed.paste(patch_image, (box[0]+9, box[1]+9))
        before.signature, after.signature = initial.tobytes(), changed.tobytes()
        views = [nav._motion_view(s.signature, full_texture=True) for s in (before,after)]
        textures = [nav._texture_mask(v[1]) for v in views]
        count, bad, matched, box = nav._texture_match(*textures, views[0][2], views[1][2], 9,9)
        static_count, static_bad, _, _ = nav._texture_match(*textures, views[0][2], views[1][2], 0,0)
        self.assertGreaterEqual(count,300);self.assertLessEqual(20*bad,count)
        full = Image.new('L',(224,104));full.paste(matched,box[:2])
        self.assertGreaterEqual(full.crop((40,20,179,36)).histogram()[255],100)
        self.assertGreaterEqual(full.crop((40,36,90,79)).histogram()[255],100)
        self.assertGreaterEqual(static_count,300)
        self.assertGreater(3*count*static_count,20*(static_bad*count-bad*static_count))
        rows=[(.2 if (x,y)==(9,9) else 1.2,x,y) for _,x,y in routes._candidate_scores(views[0][0],views[1][0])]
        with patch.object(routes,'_candidate_scores',return_value=sorted(rows)):
            self.assertEqual({'motion':'unknown','delta':None},routes.motion(before,after,('left','up')))


if __name__ == '__main__':
    unittest.main()
