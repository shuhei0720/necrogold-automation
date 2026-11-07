"""TEST038: 一部の金壁と石壁による1歩補強。実画像は調整用の既知例。"""
from copy import deepcopy
import hashlib
import math
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from necroprobe import gold_scan as gold, motion_stats, shop_navigation as nav
import test_shop_walk as old


def actual_images():
    folder = os.environ.get('NECRO_TEST037_FRAMES')
    if not folder:
        raise unittest.SkipTest('external TEST037 frames not supplied')
    result = []
    for name, digest in (
            ('run-105.jpg', '76cb87a61ba9667e8bd11457f024889299a58d739139a1500a7dc6ee55068a0f'),
            ('run-107.jpg', '95071b5d4a42b8c48fcf42f23a4095245da1bd9cd2e1b04d125adc332742d7aa')):
        path = Path(folder) / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise AssertionError('TEST037 evidence hash mismatch')
        with Image.open(path) as image:
            result.append(image.convert('RGB'))
    return result


def shift(point, delta):
    return point[0] + delta[0], point[1] + delta[1]


def synthetic(direction='down', amount=9):
    """Independent scan metadata and genuinely translated random terrain pixels."""
    dx, dy = nav.DIRECTIONS[direction]
    delta = (-dx * amount // 9, -dy * amount // 9)
    rng = random.Random(38038)
    pixels = bytes(rng.randrange(20, 100) for _ in range(224 * 104))
    tiles = {(-2, 2): 'gold', (0, -1): 'stone', (8, 0): 'stone'}
    before = nav.Scene(tiles, {(-2, 2)}, 'unknown', set(), pixels)
    after = deepcopy(before)
    after.tiles = {shift(p, delta): kind for p, kind in tiles.items()}
    after.gold = {shift(p, delta) for p in before.gold} | {(-6, -3)}
    after.tiles[(-6, -3)] = 'gold'
    translated = Image.new('L', (224, 104))
    translated.paste(Image.frombytes('L', translated.size, pixels), (-dx * amount, -dy * amount))
    after.signature = translated.tobytes()
    return before, after


def ranked(sx=0, sy=-9, best=.6, runner=.9):
    positions = [(0, 0)] + [(n * dx, n * dy) for n in range(1, 19)
                           for dx, dy in nav.DIRECTIONS.values()]
    return [(best if (x, y) == (sx, sy) else runner, x, y) for x, y in positions]


def controlled_motion(before, after, direction='down', expected_steps=1, scores=None):
    # Coarse ranking is controlled; all geometry and signed texture checks execute.
    rows = ranked() if scores is None else scores
    with patch.object(motion_stats, 'scores', side_effect=lambda *args: list(rows)):
        return nav.motion(before, after, direction, expected_steps)


class PartialGoldMotionTests(unittest.TestCase):
    def test_actual_down_step_through_driver(self):
        # Terrain moves up36px: a down step. This is replay, not device E2E.
        with tempfile.TemporaryDirectory() as folder:
            driver, _ = old.SyncDeadlineTests.build(self, folder)
            observations = []
            for image in actual_images():
                observation = gold.analyze_image(image)
                observation['_extra'] = driver.analyze_frame(image, observation)
                observations.append(observation)
            self.assertEqual(['floor', 'floor'], [o['state'] for o in observations])
            self.assertEqual([{(-2, 2)}, {(-2, -1), (-2, 1)}],
                             [driver.scene(o).gold for o in observations])
            self.assertEqual('moved', driver.movement(*observations, 'down'))
            self.assertEqual('unexpected', driver.movement(*observations, 'up'))
            for count in (2, 3, 4):
                self.assertEqual('unknown', driver.movement(*observations, 'down', count))
            self.assertEqual('unknown', driver.goods(observations[-1]))
            self.assertEqual({'direction': 'left', 'reason': 'approach_gate', 'target': (-1, 0)},
                             driver.choose(observations[-1]))
            self.assertEqual(0, driver.state['moves_confirmed'])
            self.assertIsNone(driver.entrance)
            self.assertFalse(driver.pending)

    def test_all_directions_are_measured_independently_of_requested_direction(self):
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            before, after = synthetic(direction)
            scores = ranked(-9 * dx, -9 * dy)
            for requested in nav.DIRECTIONS:
                with self.subTest(observed=direction, requested=requested):
                    self.assertEqual('moved' if requested == direction else 'unexpected',
                                     controlled_motion(before, after, requested, scores=scores))

    def test_partial_gold_path_cannot_confirm_partial_or_multiple_steps(self):
        before, after = synthetic()
        for count in (2, 3, 4):
            self.assertEqual('unknown', controlled_motion(before, after, expected_steps=count))
        # A geometrically coherent two-tile shift is outside the added path too.
        before, after = synthetic(amount=18)
        self.assertEqual('unknown', controlled_motion(before, after, scores=ranked(0, -18)))

    def test_gold_must_expand_from_exactly_one_and_keep_known_correspondence(self):
        base, moved = synthetic()
        for fault in ('before_zero', 'before_two', 'after_zero', 'after_one', 'lost_known'):
            before, after = deepcopy(base), deepcopy(moved)
            if fault == 'before_zero':
                before.gold.clear(); before.tiles.pop((-2, 2))
            elif fault == 'before_two':
                before.gold.add((4, 3)); before.tiles[(4, 3)] = 'gold'
            elif fault == 'after_zero':
                after.gold.clear()
            elif fault == 'after_one':
                after.gold.remove((-6, -3)); after.tiles.pop((-6, -3))
            else:
                after.gold.remove((-2, 1)); after.tiles.pop((-2, 1))
                after.gold.add((5, 4)); after.tiles[(5, 4)] = 'gold'
            self.assertEqual('unknown', controlled_motion(before, after), fault)

    def test_two_observed_stones_and_non_collinearity_are_required(self):
        for count in (0, 1):
            before, after = synthetic()
            for p in ((0, -1), (8, 0))[count:]:
                after.tiles.pop(shift(p, (0, -1)))
            self.assertEqual('unknown', controlled_motion(before, after), count)
        before, after = synthetic()
        before.tiles = {(-2, 2): 'gold', (-2, 0): 'stone', (-2, -2): 'stone'}
        after.tiles = {shift(p, (0, -1)): kind for p, kind in before.tiles.items()}
        after.tiles[(-6, -3)] = 'gold'
        self.assertEqual('unknown', controlled_motion(before, after))

    def test_stone_label_contradictions_are_rejected_in_both_directions(self):
        for label in ('floor', 'gold', 'door', 'dirt'):
            for reverse in (False, True):
                before, after = synthetic()
                # The two original anchors still match. A third observed location contradicts them.
                if reverse:
                    before.tiles[(4, 3)] = label; after.tiles[(4, 2)] = 'stone'
                else:
                    before.tiles[(4, 3)] = 'stone'; after.tiles[(4, 2)] = label
                with self.subTest(label=label, reverse=reverse):
                    self.assertEqual('unknown', controlled_motion(before, after))

    def test_unobserved_and_explicit_unknown_stones_are_neither_votes_nor_conflicts(self):
        for unknown in (False, True):
            for reverse in (False, True):
                before, after = synthetic()
                source, target, source_point, target_point = (
                    (after, before, (4, 2), (4, 3)) if reverse else
                    (before, after, (4, 3), (4, 2)))
                source.tiles[source_point] = 'stone'
                if unknown: target.tiles[target_point] = 'unknown'
                with self.subTest(unknown=unknown, reverse=reverse):
                    self.assertEqual('moved', controlled_motion(before, after))
            before, after = synthetic()
            after.tiles.pop((8, -1))
            if unknown: after.tiles[(8, -1)] = 'unknown'
            # One observed stone plus an unknown destination is insufficient.
            self.assertEqual('unknown', controlled_motion(before, after))

    def test_stationary_and_two_tile_geometry_aliases_are_checked_without_score_entries(self):
        for delta in ((0, 0), (0, 1), (-1, 0), (1, 0),
                      (0, 2), (0, -2), (2, 0), (-2, 0)):
            before, after = synthetic()
            for point, label in before.tiles.items():
                after.tiles[shift(point, delta)] = label
            after.gold.add(shift((-2, 2), delta))
            # Deliberately omit the competing shift: geometry must still enumerate it.
            self.assertEqual('unknown', controlled_motion(
                before, after, scores=[(.6, 0, -9), (.9, 1, 0)]), delta)

    def test_noninteger_stationary_and_nonfinite_coarse_candidates_are_rejected(self):
        before, after = synthetic()
        for winner in ((0, 0), (0, -8), (1, -8), (0, -18)):
            rows = [(.6, *winner), (.9, 1, 0)]
            self.assertEqual('unknown', controlled_motion(before, after, scores=rows), winner)
        for score in (float('inf'), float('nan')):
            self.assertEqual('unknown', controlled_motion(
                before, after, scores=[(score, 0, -9), (float('inf'), 0, 0)]))

    def test_coarse_margin_keeps_exact_threshold_and_just_below(self):
        before, after = synthetic()
        for runner, expected in ((.68, 'moved'), (math.nextafter(.68, 0), 'unknown')):
            self.assertEqual(expected, controlled_motion(before, after, scores=ranked(best=.6, runner=runner)))

    def test_stationary_pixels_moving_actors_and_periodic_texture_do_not_confirm(self):
        before, after = synthetic()
        after.signature = before.signature
        self.assertEqual('unknown', controlled_motion(before, after))
        rng = random.Random(38039)
        raw = Image.new('L', (224, 104), 40)
        actor = Image.frombytes('L', (15, 14), bytes(rng.randrange(20, 100) for _ in range(15 * 14)))
        raw.paste(actor, (105, 52))
        before.signature = raw.tobytes()
        moved = Image.new('L', raw.size, 40); moved.paste(actor, (105, 43))
        after.signature = moved.tobytes()
        self.assertEqual('unknown', controlled_motion(before, after))
        stripe = bytes(rng.randrange(20, 100) for _ in range(224 * 9))
        before.signature = after.signature = (stripe * 12)[:224 * 104]
        self.assertEqual('unknown', controlled_motion(before, after))

    def test_large_textured_object_cannot_overrule_stationary_textured_background(self):
        before, after = synthetic()
        rng = random.Random(38040)
        stationary = Image.new('L', (224, 104), 40)
        def texture(box):
            width, height = box[2] - box[0], box[3] - box[1]
            return Image.frombytes('L', (width, height),
                                   bytes(rng.randrange(20, 100) for _ in range(width * height)))
        # Thin stationary patches have no overlap with their shifted copies.
        # Both patches lie in the original terrain mask, outside actor/text exclusions.
        for box in ((44, 68, 85, 76), (140, 55, 178, 63)):
            stationary.paste(texture(box), box[:2])
        initial, changed = stationary.copy(), stationary.copy()
        # One moving object spans two independently checked terrain regions.
        for box in ((44, 29, 178, 35), (44, 50, 85, 58)):
            patch_image = texture(box)
            initial.paste(patch_image, box[:2])
            changed.paste(patch_image, (box[0], box[1] - 9))
        before.signature, after.signature = initial.tobytes(), changed.tobytes()
        _, old_texture, old_positive = nav._motion_view(before.signature)
        _, new_texture, new_positive = nav._motion_view(after.signature)
        count, bad, matched, box = nav._texture_match(
            old_texture, new_texture, old_positive, new_positive, 0, -9)
        static_count, static_bad, _, _ = nav._texture_match(
            old_texture, new_texture, old_positive, new_positive, 0, 0)
        self.assertGreater(count, 300)
        self.assertLessEqual(20 * bad, count)
        full = Image.new('L', (224, 104)); full.paste(matched, box[:2])
        self.assertGreaterEqual(full.crop((40, 20, 179, 36)).histogram()[255], 100)
        self.assertGreaterEqual(full.crop((40, 36, 90, 79)).histogram()[255], 100)
        self.assertGreaterEqual(static_count, 300)
        # The actual static texture is a stronger competing explanation. The object
        # alone passes support/polarity/regions, so the competition check is required.
        self.assertGreater(3 * count * static_count,
                           20 * (static_bad * count - bad * static_count))
        self.assertEqual('unknown', controlled_motion(before, after))

    def texture_boundary(self, support=400, bad=20, competitor_count=400,
                         competitor_bad=80, regions=None, competitor=(0, 0)):
        before, after = synthetic()
        full = Image.new('L', (224, 104))
        amounts = (support // 2, support - support // 2, 0) if regions is None else regions
        for box, amount in zip(((40, 20, 179, 36), (40, 36, 90, 79), (139, 36, 179, 79)), amounts):
            points = [(x, y) for y in range(box[1], box[3]) for x in range(box[0], box[2])]
            for point in points[:amount]: full.putpixel(point, 255)
        calls = []
        def match(*args):
            sx, sy = args[-2:]; calls.append((sx, sy))
            count, opposite = ((support, bad) if (sx, sy) == (0, -9) else
                               (competitor_count, competitor_bad) if (sx, sy) == competitor else (0, 0))
            return count, opposite, full, (0, 0, 224, 104)
        with patch.object(nav, '_texture_match', side_effect=match):
            result = controlled_motion(before, after)
        return result, calls

    def test_texture_support_polarity_and_competing_margin_boundaries(self):
        for kwargs, expected in (
                ({'support': 299, 'bad': 0}, 'unknown'),
                ({'support': 300, 'bad': 15}, 'moved'),
                ({'bad': 20}, 'moved'), ({'bad': 21}, 'unknown'),
                ({'competitor_bad': 80}, 'moved'), ({'competitor_bad': 79}, 'unknown'),
                ({'competitor_count': 299, 'competitor_bad': 0}, 'moved'),
                ({'competitor_count': 300, 'competitor_bad': 0}, 'unknown')):
            with self.subTest(**kwargs):
                self.assertEqual(expected, self.texture_boundary(**kwargs)[0])

    def test_two_spatial_regions_need_one_hundred_votes_each(self):
        for regions, expected in (((100, 200, 0), 'moved'), ((99, 201, 0), 'unknown'),
                                  ((300, 0, 0), 'unknown'), ((0, 100, 200), 'moved')):
            self.assertEqual(expected, self.texture_boundary(
                support=300, bad=15, regions=regions)[0], regions)

    def test_all_seventy_three_texture_competitors_include_static_and_worst_rank(self):
        result, calls = self.texture_boundary()
        self.assertEqual('moved', result)
        self.assertEqual({(x, y) for _, x, y in ranked()}, set(calls))
        self.assertEqual('unknown', self.texture_boundary(competitor=(0, 18), competitor_bad=0)[0])

    def test_original_closed_gate_high_score_path_still_handles_multi_step_partial(self):
        before, after = synthetic()
        before.tiles = {(-1, -2): 'gold', (1, -2): 'gold', (0, -2): 'door'}
        before.gold = {(-1, -2), (1, -2)}
        after.tiles = {shift(p, (0, -1)): kind for p, kind in before.tiles.items()}
        after.gold = {shift(p, (0, -1)) for p in before.gold}
        self.assertEqual('moved', controlled_motion(before, after))
        self.assertEqual('partial', controlled_motion(before, after, expected_steps=2))
        self.assertEqual('unexpected', controlled_motion(before, after, direction='up'))


class ActualNativeParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse only the established host compiler fixture, not its expected outputs.
        import test_motion_stats
        test_motion_stats.MotionStatsTests.setUpClass.__func__(cls)

    def test_test037_all_scores_and_public_decision_match_pillow(self):
        from test_motion_stats import reference
        before, after = [nav.scan(image) for image in actual_images()]
        old_view = nav._motion_view(before.signature)[0]
        new_view = nav._motion_view(after.signature)[0]
        expected, _ = reference(old_view, new_view)
        with patch.object(motion_stats, '_native', self.lib):
            self.assertEqual(expected, motion_stats.scores(old_view, new_view))
            self.assertEqual('moved', nav.motion(before, after, 'down'))
            self.assertEqual('unexpected', nav.motion(before, after, 'up'))
        with patch.object(motion_stats, '_native', None):
            self.assertEqual(expected, nav._pillow_motion_scores(old_view, new_view))
            self.assertEqual('moved', nav.motion(before, after, 'down'))
            self.assertEqual('unexpected', nav.motion(before, after, 'up'))


if __name__ == '__main__':
    unittest.main()
