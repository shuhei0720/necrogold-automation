"""Positive-only top ITEM fallback from public procedural target pixels.

No device image is embedded. These checks establish finite kernel/HUD and
candidate-preservation boundaries, not phone timing or unknown-run accuracy.
"""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_native_perception import NativeScene
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests import test_native_ring_bank094 as bank
from tests.test_native_shop_coverage102 import _put, set_tile, shop_pixels, shop_scene
from tests.test_target_assessment087 import FEATURES, WIDTH, HEIGHT, shop


ROOT = Path(__file__).resolve().parents[1]
RING = Path(os.environ.get('NECRO124_RING_SOURCE',
    str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))


def item_scene(x=0, y=-4, *, item=True):
    scene = NativeScene(abi_version=1, struct_size=C.sizeof(NativeScene),
                        state=2, gold_state=2, goods=1)
    set_tile(scene, 0, 0, 1)
    set_tile(scene, -2, -4, 2)
    if item:
        set_tile(scene, x, y, 6)
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            xx, yy = x+dx, y+dy
            if -11 <= xx <= 11 and -5 <= yy <= 4:
                scene.protected_cells[(yy+5)*23+xx+11] = 1
    return scene


def target_at(pixels, x=431, y=72, *, damage=0):
    """Paint only fixed derived samples; no name, price, or SHOP sign."""
    sprite = FEATURES['icons'][1]
    for yy in range(y, y+sprite['height']):
        for xx in range(x, x+sprite['width']):
            _put(pixels, xx, yy, (0, 0, 0))
    for index, (dx, dy, r, g, b) in enumerate(sprite['bright']):
        _put(pixels, x+dx, y+dy,
             (0, 0, 0) if damage and index % damage == 0 else (r, g, b))
    for dx, dy in sprite['dark']:
        _put(pixels, x+dx, y+dy, (0, 0, 0))


def positive_pixels(*, hud=True, safe=True, x=431, y=72):
    pixels = bytearray(bytes((0, 0, 0, 255))*(WIDTH*HEIGHT))
    if hud:
        target_at(pixels, x=x, y=39)
    if safe:
        target_at(pixels, x=x, y=y, damage=10)
    return bytes(pixels)


def semantic_bytes(value):
    """Additional real checkpoints may change only these clock diagnostics."""
    copy = Result.from_buffer_copy(bytes(value))
    copy.started_ns = copy.finished_ns = copy.checks = 0
    return bytes(copy)


class NativePartialPositive124Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='partial-positive124-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = bank.NativeRingBank094Tests.build_library(RING,
            Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int
        # Existing exported canonical kernel is only a fixture oracle. The
        # behavior under test always enters ng2_ring_assess_rgba normally.
        cls.lib.ring_icon.argtypes = [C.c_void_p, C.c_size_t, C.c_int,
            C.c_int, C.c_int, C.c_void_p, C.POINTER(C.c_double),
            C.POINTER(C.c_int)]
        cls.lib.ring_icon.restype = C.c_int

    def assess(self, pixels=None, scene=None, *, mode=2, now=100,
               deadline=1000000000, cancel_after=None, expire_after=None):
        pixels = positive_pixels() if pixels is None else pixels
        scene = item_scene() if scene is None else scene
        calls = [0]
        def clock(_):
            calls[0] += 1
            return deadline if expire_after is not None and calls[0] > expire_after else now
        clock_fn = Clock(clock)
        cancel_fn = Cancelled(lambda _: int(cancel_after is not None
            and calls[0] > cancel_after))
        options = Options(abi=1, size=C.sizeof(Options), mode=mode,
            deadline_ns=deadline, now_ns=clock_fn, cancelled=cancel_fn,
            scene=C.addressof(scene), fast=1)
        result = Result()
        buffer = C.create_string_buffer(pixels)
        before = bytes(scene)
        status = self.lib.ng2_ring_assess_rgba(buffer, len(pixels), WIDTH*4,
            C.byref(options), C.byref(result))
        self.assertEqual(status, result.status)
        self.assertEqual(before, bytes(scene), 'normal immutable Scene is not rewritten')
        self.assertEqual(pixels, buffer.raw[:-1], 'normal immutable RGBA is not rewritten')
        return status, result, calls[0]

    def kernel(self, pixels, sy, cx=448):
        buffer = C.create_string_buffer(pixels)
        score, box = C.c_double(), (C.c_int*4)()
        self.assertEqual(0, self.lib.ring_icon(buffer, len(pixels), cx, sy,
            0, None, C.byref(score), box))
        return score.value, tuple(box)

    def candidate(self, pixels=None, scene=None):
        pixels = positive_pixels() if pixels is None else pixels
        status, value, _ = self.assess(pixels, scene)
        self.assertEqual((0, 1, 1, 0, 1, -1, 0, 0),
            (status, value.outcome, value.coverage, value.row_count,
             value.partial_count, value.selected_row, value.selected_partial,
             value.partial_safe_no_positive),
            'a clear non-HUD target-like ITEM must be held without requiring a sign, name, or price')
        slot = value.partial[0]
        self.assertEqual((448, 15, 1), (slot.cx, slot.sy, slot.icon_score_exact),
            'the safe kernel probe does not invent a shifted observed item row')
        self.assertGreaterEqual(slot.icon_score, .80)
        self.assertEqual(1, slot.outcome)
        self.assertGreaterEqual(slot.icon_box[1], 45)
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)),
            'positive-only evidence cannot become an absence certificate')
        return value

    def test_stronger_hud_maximum_does_not_hide_safe_second_best(self):
        pixels = positive_pixels()
        original_score, original_box = self.kernel(pixels, 15)
        safe_score, safe_box = self.kernel(pixels, 21)
        self.assertEqual(39, original_box[1])
        self.assertLess(original_box[1], 45)
        self.assertGreater(original_score, safe_score)
        self.assertGreaterEqual(safe_score, .80)
        self.assertGreaterEqual(safe_box[1], 45)
        value = self.candidate(pixels)
        self.assertEqual(round(safe_score, 9), value.partial[0].icon_score)
        self.assertEqual(safe_box, tuple(value.partial[0].icon_box))

    def test_candidate_without_name_or_price_and_with_other_observed_items(self):
        for others in (False, True):
            scene = item_scene()
            if others:
                for x in (-4, -3, -2):
                    set_tile(scene, x, 2, 6)
                    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                        scene.protected_cells[(2+dy+5)*23+x+dx+11] = 1
            with self.subTest(other_items=others):
                self.candidate(positive_pixels(hud=False), scene)

    def test_high_confidence_icon_and_price_still_grant_candidate_only(self):
        pixels = bytearray(positive_pixels(hud=False, safe=False))
        target_at(pixels, y=45)
        for y in range(93, 100):
            for x in range(443, 454):
                if (x+y) % 2: _put(pixels, x, y, (245, 245, 245))
        score, _ = self.kernel(bytes(pixels), 21)
        self.assertGreaterEqual(score, .94)
        value = self.candidate(bytes(pixels))
        self.assertNotEqual(16, value.certificate.policy_version,
            'the added probe does not manufacture a shifted image/price proof')
        self.assertEqual(0, value.certificate.observed_prices)

    def test_no_hit_preserves_original_unknown_and_never_grants_safe_partial(self):
        for pixels in (positive_pixels(hud=False, safe=False),
                       positive_pixels(safe=False)):
            with self.subTest(only_hud=pixels != positive_pixels(hud=False, safe=False)):
                _, baseline, _ = self.assess(pixels, item_scene(item=False))
                _, value, _ = self.assess(pixels)
                self.assertEqual((0, 1, 0, 0, 0), (value.outcome,
                    value.coverage, value.row_count, value.partial_count,
                    value.partial_safe_no_positive))
                self.assertEqual(semantic_bytes(baseline), semantic_bytes(value),
                    'a failed positive search cannot alter original UNKNOWN authority')

    def test_mode_scene_and_item_eligibility_remain_narrow(self):
        cases = []
        for mode in (0, 1):
            cases.append(('mode'+str(mode), item_scene(), mode))
        for field, value in (('abi_version', 2), ('struct_size', 0),
                             ('state', 1), ('goods', 0), ('goods', 2),
                             ('gold_state', 0)):
            scene = item_scene(); setattr(scene, field, value)
            cases.append((field+str(value), scene, 2))
        cases.append(('no_item', item_scene(item=False), 2))
        scene = item_scene(); set_tile(scene, -2, -4, 0)
        cases.append(('no_actual_gold', scene, 2))
        for name, scene, mode in cases:
            with self.subTest(case=name):
                status, value, _ = self.assess(scene=scene, mode=mode)
                expected = 3 if name in ('abi_version2', 'struct_size0') else 0
                self.assertEqual((expected, 0, 0), (status, value.outcome, value.partial_count))

    def test_original_hud_crossing_and_complete_kernel_envelope_are_required(self):
        for x, y, sprite_x, sprite_y in ((-1, -4, 395, 72),
                (1, -4, 467, 72), (0, -5, 431, 72),
                (0, -3, 431, 85), (-11, -4, 0, 72),
                (11, 4, 850, 335)):
            with self.subTest(item=(x, y)):
                pixels = positive_pixels(hud=False, x=sprite_x, y=sprite_y)
                status, value, _ = self.assess(pixels, item_scene(x, y))
                self.assertEqual((0, 0, 0), (status, value.outcome, value.partial_count),
                    'only the original top-central HUD crossing admits the bounded +6 probe')

    def test_existing_row_partial_sign_and_positive_paths_take_precedence(self):
        target = positive_pixels(hud=False)
        for kind in ('row', 'partial', 'sign'):
            pixels = bytearray(shop(icon=False, name=False) if kind == 'row'
                else bytes((0, 0, 0, 255))*(WIDTH*HEIGHT))
            if kind != 'row':
                for y in range(106, 135):
                    for x in range(585, 615): _put(pixels, x, y, (220, 210, 10))
                if kind == 'partial':
                    for y in range(150, 170):
                        for x in range(595, 605): _put(pixels, x, y, (10, 170, 165))
            for y in range(45, 107):
                pixels[4*(y*WIDTH+423):4*(y*WIDTH+473)] = target[4*(y*WIDTH+423):4*(y*WIDTH+473)]
            with self.subTest(existing=kind):
                _, value, _ = self.assess(bytes(pixels))
                self.assertEqual(0, value.outcome)
                if kind == 'row': self.assertGreater(value.row_count, 0)
                elif kind == 'partial': self.assertGreater(value.partial_count, 0)
                else: self.assertEqual((0, 0), (value.row_count, value.partial_count))
        _, value, _ = self.assess(shop())
        self.assertEqual(2, value.outcome, 'the original normal target keeps precedence')
        status, value, _ = self.assess(shop_pixels(), shop_scene())
        self.assertEqual((0, 3, 2), (status, value.outcome, value.coverage))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_non_ok_cancel_and_original_deadline_are_propagated(self):
        for now, deadline in ((100, 100), (101, 100)):
            with self.subTest(now=now, deadline=deadline):
                status, value, _ = self.assess(now=now, deadline=deadline)
                self.assertEqual((2, 0, 0, 0), (status, value.outcome,
                    value.coverage, value.partial_safe_no_positive))
        status, value, _ = self.assess(cancel_after=-1)
        self.assertEqual((1, 0, 0, 0), (status, value.outcome,
            value.coverage, value.partial_safe_no_positive))
        pixels = bytearray(positive_pixels()); pixels[3] = 254
        status, value, _ = self.assess(bytes(pixels))
        self.assertEqual((3, 0, 0, 0), (status, value.outcome,
            value.coverage, value.partial_safe_no_positive))

    def test_expiration_during_added_positive_work_cannot_restore_old_ok(self):
        # Derive the end of the original normal scan from the same pixels and
        # an ineligible Scene, rather than encoding an implementation count.
        _, original, original_calls = self.assess(scene=item_scene(item=False))
        self.assertEqual((0, 0), (original.outcome, original.partial_count))
        for fault in ('cancel', 'deadline'):
            with self.subTest(fault=fault):
                kwargs = {'cancel_after': original_calls} if fault == 'cancel' else {
                    'expire_after': original_calls}
                status, value, _ = self.assess(**kwargs)
                self.assertEqual(1 if fault == 'cancel' else 2, status,
                    'new fallback work owns the original cancellation/deadline')
                self.assertEqual((0, 0, 0), (value.outcome, value.coverage,
                    value.partial_safe_no_positive))


if __name__ == '__main__':
    unittest.main()
