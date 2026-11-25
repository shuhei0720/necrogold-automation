"""Complete offer proofs from procedural pixels; not phone acceptance.

The public Controller lifecycle uses host clocks, PAUSE/RESTART command
qualification and modeled ACK/new-floor observations. It executes no iPhone,
Runtime gesture, real UI restart, or future game image. Original 5572's real
device restart is separate received evidence, not an outcome of these tests.
"""
import ctypes as C
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_ring_bank094 as bank
from tests import test_native_single_sign_shop103 as single
from tests import test_native_shop_coverage102 as bottom
from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests.test_native_ring094 import Result
from tests.test_native_shop_coverage102 import normal_assess, _put
from tests.test_target_assessment087 import WIDTH, FEATURES
from tests.test_native_perception import NativeScene

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ.get('NECRO121_GOODS_RING_SOURCE',
    str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))


def relative_single_scene():
    scene = single.shop_scene()
    for x in (-5, -4, -3):
        single.set_tile(scene, x, 1, 1)
    return scene


def relative_single_pixels(small_sign_seed=False, **kwargs):
    """Use the old public glyph, with warm dark ink and its observed face."""
    pixels = bytearray(single.shop_pixels(missing_merchant=True,
        faces=((-15, -15, 30, 30), None), **kwargs))
    glyph = bank.auth_data()['shop_glyphs'][0]
    for dy, bits in enumerate(glyph['rows_hex']):
        for dx in range(glyph['width']):
            if int(bits, 16) >> dx & 1:
                _put(pixels, 255+dx, 147+dy, (75, 62, 29))
    if small_sign_seed:
        # The tiny component sorts before the full face's first pixel, but
        # remains inside its bbox. Its pixels do not own the face median.
        for x in range(252, 281):
            _put(pixels, x, 138, (27, 17, 15))
        _put(pixels, 253, 138, (220, 210, 10))
        _put(pixels, 253, 139, (27, 17, 15))
    return bytes(pixels)


def grouped_scene(mirror=False):
    scene = bottom.shop_scene(mirror=mirror)
    for x in (-4, -3, -2):
        bottom.set_tile(scene, x, 0, 1)
    return scene


def textured_patch(pixels, x0, y0, width, height, colour):
    """Keep exact medians, with positive old material texture evidence."""
    for y in range(y0, y0+height):
        for x in range(x0, x0+width):
            r, g, b = colour
            _put(pixels, x, y, (r+6 if (x+2*y) % 4 == 0 else r, g, b))


def grouped_pixels(mirror=False, upper=(44, 26, 22), left=301, sy=117, **kwargs):
    """Three original components close exactly two physical 29x29 faces.

    The fragments have disjoint pixels but overlapping boxes. No phone pixel
    or new matcher feature is embedded in this procedural coverage fixture.
    """
    pixels = bytearray(bottom.shop_pixels(left=left, sy=sy,
        truncated_side=None, **kwargs))
    cx = left if mirror else left+72
    x0, y0 = cx-14, sy-14
    for y in range(29):
        for x in range(29):
            top = y <= 8 or (9 <= y <= 16 and x <= 12)
            low = y >= 18 or (10 <= y <= 17 and x >= 15)
            _put(pixels, x0+x, y0+y,
                 (220, 210, 10) if top or low else (27, 17, 15))
    # Only one cap needs the alternate upper proof. Both diagonals and the
    # lower half remain ordinary positive material samples.
    textured_patch(pixels, left-48, sy+36, 12, 12, (36, 22, 21))
    textured_patch(pixels, left-36, sy+36, 13, 12, upper)
    textured_patch(pixels, left-48, sy+48, 25, 13, (30, 19, 18))
    return bytes(pixels)


def consumer_library(directory):
    """Existing independent C verifier with an explicit unit context.

    Only full_seen and the procedural source Scene are declared. This is a
    certificate trust-boundary cut, not a phone or opaque-state replay.
    """
    core = CORE.parent
    source = directory/'consumer.c'
    source.write_text('#include "'+str(core/'NG2Controller.c')+'"\n'
        'int goods121_consumer(const NG2Scene *s,const NG2RingResult *r){\n'
        ' NG2Controller p={0};p.cycle.full_seen=1;p.cycle_anchor=*s;\n'
        ' return cycle_negative_witness(&p,r);}\n')
    objects = []
    for path in (source, core/'NG2Beat.c', core/'NG2Navigation.c', core/'NG2Perception.c'):
        target = directory/(path.stem+'.o')
        flags = ['-O0'] if path.stem in ('consumer', 'NG2Beat') else [
            '-O2', '-fno-fast-math', '-ffp-contract=off', '-frounding-math']
        subprocess.run(['cc', '-std=c11', *flags, '-Wall', '-Wextra', '-Werror',
            '-pedantic', '-fPIC', '-I'+str(core), '-c', str(path), '-o', str(target)],
            check=True, capture_output=True)
        objects.append(str(target))
    target = directory/'consumer.so'
    subprocess.run(['cc', '-shared', *objects, '-lm', '-o', str(target)],
        check=True, capture_output=True)
    lib = C.CDLL(str(target))
    lib.goods121_consumer.argtypes = [C.POINTER(NativeScene), C.POINTER(Result)]
    lib.goods121_consumer.restype = C.c_int
    return lib


def cycle_functions(lib):
    lib.ng2_controller_create.argtypes = [C.c_uint64]
    lib.ng2_controller_create.restype = C.c_void_p
    lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
    lib.ng2_controller_create_cycle.restype = C.c_void_p
    lib.ng2_controller_destroy.argtypes = [C.c_void_p]
    lib.ng2_controller_observe.argtypes = [C.c_void_p, C.POINTER(native.Scene),
        C.c_uint64, C.c_uint64, C.c_uint64, C.c_uint64, C.c_int32]
    lib.ng2_controller_tick.argtypes = [C.c_void_p, C.c_uint64, C.c_int32,
        C.c_int32, C.c_int32, C.POINTER(native.Command)]
    lib.ng2_controller_begin.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64,
        C.c_int32, C.c_int32, C.c_int32]
    lib.ng2_controller_complete.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64, C.c_int32]
    lib.ng2_controller_status.argtypes = [C.c_void_p, C.POINTER(native.Status)]
    lib.ng2_controller_cycle_status.argtypes = [C.c_void_p, C.POINTER(cycle.Cycle)]
    for name in ('worker_begin', 'durable', 'outcome_commit'):
        getattr(lib, 'ng2_controller_cycle_'+name).argtypes = [C.c_void_p]+[C.c_uint64]*4
    lib.ng2_controller_cycle_assess.argtypes = [C.c_void_p]+[C.c_uint64]*4+[C.POINTER(Result)]
    lib.ng2_controller_cycle_intent_commit.argtypes = [C.c_void_p]+[C.c_uint64]*5


class NativeGoodsCoverage121Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='goods121-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = bank.NativeRingBank094Tests.build_library(CORE,
            Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    @classmethod
    def independent(cls):
        if not hasattr(cls, '_consumer'):
            cls._consumer = consumer_library(Path(cls.tmp.name))
        return cls._consumer

    def negative(self, pixels=None, scene=None, policy=19):
        scene = relative_single_scene() if scene is None else scene
        pixels = relative_single_pixels() if pixels is None else pixels
        frozen = bytes(scene)
        status, result = normal_assess(self.lib, pixels, scene)
        self.assertEqual((0, 3, 2, policy), (status, result.outcome,
            result.coverage, result.certificate.policy_version))
        self.assertEqual(frozen, bytes(scene))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        return result

    def test_complete_single_shop_uses_relative_glyph_without_a_merchant_identity(self):
        scene = relative_single_scene()
        before = bytes(scene)
        status, result = normal_assess(self.lib, relative_single_pixels(), scene)
        self.assertEqual(0, status)
        self.assertEqual(before, bytes(scene), 'coverage cannot relabel the source')
        self.assertEqual((3, 2, 19, 19), (result.outcome, result.coverage,
            result.certificate.policy_version, result.certificate.board_mode),
            'a complete observed row needs positive relative SHOP authority, not a catalog entry')
        self.assertEqual((3, 3, 0), (result.certificate.observed_items,
            result.certificate.observed_prices, result.certificate.unmatched_prices))
        self.assertEqual((0., 0.), (result.certificate.merchant_score,
            result.certificate.merchant_coverage))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        # The original large component still owns the exact full bbox/count.
        # A preceding, disconnected SIGN speck cannot replace or contaminate it.
        self.negative(relative_single_pixels(small_sign_seed=True))

    def test_three_owned_components_and_one_diagonal_floor_prove_complete_grouped_offer(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                scene = grouped_scene(mirror)
                before = bytes(scene)
                status, result = normal_assess(self.lib, grouped_pixels(mirror), scene)
                self.assertEqual((0, 3, 2, 20, 1, 20),
                    (status, result.outcome, result.coverage,
                     result.certificate.policy_version,
                     result.certificate.layout_version, result.certificate.board_mode),
                    'three owned components and the bounded cap proof must reach normal coverage')
                self.assertEqual((3, 3, 0, 0),
                    (result.certificate.observed_items, result.certificate.observed_prices,
                     result.certificate.unmatched_boards, result.certificate.unmatched_prices))
                self.assertEqual([2, 1], [cap.floor_upper for cap in result.certificate.endcaps])
                self.assertEqual(before, bytes(scene))
                self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_relative_glyph_needs_complete_ink_sign_support_and_exact_offer_scene(self):
        self.negative()
        glyph = bank.auth_data()['shop_glyphs'][0]
        cases = {}
        missing = bytearray(relative_single_pixels())
        for y, bits in enumerate(glyph['rows_hex']):
            for x in range(glyph['width']//4):
                if int(bits, 16) >> x & 1:
                    _put(missing, 255+x, 147+y, (220, 210, 10))
        cases['missing_letter'] = bytes(missing)
        extra = bytearray(relative_single_pixels())
        zeros = [(x, y) for y, bits in enumerate(glyph['rows_hex'])
                 for x in range(glyph['width']) if not (int(bits, 16) >> x & 1)]
        for x, y in zeros[:12]:
            _put(extra, 255+x, 147+y, (75, 62, 29))
        cases['extra_ink'] = bytes(extra)
        wrong = bytearray(relative_single_pixels())
        for y in range(glyph['height']):
            for x in range(glyph['width']):
                _put(wrong, 255+x, 147+y, (220, 210, 10))
        for y in range(glyph['height']):
            for x in range(glyph['width']):
                if x % 7 == y % 7:
                    _put(wrong, 255+x, 147+y, (75, 62, 29))
        cases['wrong_letter'] = bytes(wrong)
        few = bytearray(relative_single_pixels())
        keep = {(x, y) for y in range(30) for x in range(30)
                if x in (0, 29) or y in (0, 29)}
        for y in range(1, 29):
            for x in range(1, 29):
                if len(keep) < 149:
                    keep.add((x, y))
        self.assertEqual(149, len(keep))
        for y in range(30):
            for x in range(30):
                _put(few, 252+x, 138+y,
                     (220, 210, 10) if (x, y) in keep else (27, 17, 15))
        cases['background149'] = bytes(few)
        for name, pixels in cases.items():
            with self.subTest(raw=name):
                self.assertNotEqual(3, normal_assess(self.lib, pixels, relative_single_scene())[1].outcome)
        for name in ('rail', 'support_floor', 'extra_item', 'protection'):
            scene = relative_single_scene()
            if name == 'rail':
                single.set_tile(scene, -7, -2, 0)
                single.set_tile(scene, 10, 4, 2)
            elif name == 'support_floor':
                single.set_tile(scene, -4, 1, 0)
            elif name == 'extra_item':
                single.set_tile(scene, 9, 3, 6)
            else:
                scene.protected_cells[1] = 1
            with self.subTest(scene=name):
                self.assertNotEqual(3, normal_assess(self.lib, relative_single_pixels(), scene)[1].outcome)

    def test_group_ownership_and_diagonal_floor_cannot_discard_other_boards_or_support(self):
        self.negative(grouped_pixels(), grouped_scene(), 20)
        self.assertNotEqual(3, normal_assess(self.lib,
            grouped_pixels(extra_board=True), grouped_scene())[1].outcome)
        first = bytearray(grouped_pixels())
        second = grouped_pixels(left=625, sy=189)
        for y in range(144, 300):
            for x in range(535, 790):
                at = 4*(y*WIDTH+x)
                first[at:at+4] = second[at:at+4]
        scene = grouped_scene()
        other = bottom.shop_scene(ax=5, ay=1)
        for x in (5, 6, 7):
            bottom.set_tile(other, x, 2, 1)
        for i in range(len(scene.tiles)):
            if other.tiles[i]:
                scene.tiles[i] = other.tiles[i]
            scene.protected_cells[i] |= other.protected_cells[i]
        self.assertNotEqual(3, normal_assess(self.lib, bytes(first), scene)[1].outcome,
            'two physical pairs cannot become one complete shop by dropping components')
        for name in ('UL_missing', 'LR_missing', 'gap85', 'fragment_shift'):
            pixels = bytearray(grouped_pixels(upper=(48, 28, 24) if name == 'gap85' else (44, 26, 22)))
            if name == 'UL_missing':
                for y in range(153, 165):
                    for x in range(253, 265):
                        _put(pixels, x, y, (0, 0, 0))
            elif name == 'LR_missing':
                for y in range(165, 178):
                    for x in range(265, 278):
                        _put(pixels, x, y, (0, 0, 0))
            elif name == 'fragment_shift':
                # Move the lower fragment one pixel; the same-face endpoints
                # no longer match. Both components remain observed evidence.
                for y in range(121, 132):
                    for x in range(359, 389):
                        _put(pixels, x, y, (220, 210, 10) if x >= 360 else (27, 17, 15))
            with self.subTest(fault=name):
                self.assertNotEqual(3, normal_assess(self.lib, bytes(pixels), grouped_scene())[1].outcome)
        for colour, gap in (((52, 32, 27), 5), ((46, 27, 23), 75)):
            self.assertEqual(gap, 55*colour[0]-100*colour[2]-155)
            self.negative(grouped_pixels(upper=colour), grouped_scene(), 20)
        # Integer RGB reaches gaps5/75 within the fixed nonblue range. Gap0
        # is ordinary positive floor and must retain its old proof first.
        old_floor = bytearray(bottom.shop_pixels(truncated_side=None))
        zero_gap = grouped_pixels(upper=(41, 25, 21))
        for y in range(153, 178):
            for x in range(253, 278):
                at = 4*(y*WIDTH+x)
                old_floor[at:at+4] = zero_gap[at:at+4]
        value = self.negative(bytes(old_floor), grouped_scene(), 6)
        self.assertEqual(1, value.certificate.endcaps[0].floor_upper)

    def test_every_numeric_alias_keeps_five_cell_target_candidate_priority(self):
        sprite = FEATURES['icons'][0]
        for policy, source, scene in ((19, relative_single_pixels(), relative_single_scene()),
                                       (20, grouped_pixels(), grouped_scene())):
            base = self.negative(source, scene, policy)
            self.assertGreater(base.partial_count, 2,
                'outside partial evidence must remain after the two selected-proof entries')
            self.assertLessEqual(base.partial_count, 12)
            aliases = {(r.left, r.sy) for r in base.rows[:base.row_count]}
            self.assertTrue(aliases)
            for left, sy in sorted(aliases):
                for cell in range(-1, 4):
                    pixels = bytearray(source)
                    cx, top = left+36*cell, sy+35
                    sx = cx-sprite['width']//2
                    for y in range(top, top+sprite['height']):
                        for x in range(sx, sx+sprite['width']):
                            _put(pixels, x, y, (27, 17, 12))
                    for x, y, r, g, b in sprite['bright']:
                        _put(pixels, sx+x, top+y, (r, g, b))
                    for x, y in sprite['dark']:
                        _put(pixels, sx+x, top+y, (0, 0, 0))
                    with self.subTest(policy=policy, alias=(left, sy), cell=cell):
                        value = normal_assess(self.lib, bytes(pixels), scene)[1]
                        self.assertIn(value.outcome, (1, 2),
                            'a target/candidate in any swept alias cell must veto absence')
                        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
                pixels = bytearray(source)
                for y in range(sy-18, sy-5):
                    for x in range(left-100, left-16):
                        _put(pixels, x, y, (27, 17, 12))
                for y, bits in enumerate(FEATURES['word']['rows_hex']):
                    for x in range(84):
                        if int(bits, 16) >> x & 1:
                            _put(pixels, left-100+x, sy-18+y, (245, 245, 245))
                with self.subTest(policy=policy, alias=(left, sy), wider_word=True):
                    value = normal_assess(self.lib, bytes(pixels), scene)[1]
                    self.assertIn(value.outcome, (1, 2),
                        'the wider name union must veto absence outside merchandise image boxes')
            for tail in base.partial[2:base.partial_count]:
                pixels = bytearray(source)
                top, sx = tail.sy+35, tail.cx-sprite['width']//2
                for y in range(top, top+sprite['height']):
                    for x in range(sx, sx+sprite['width']):
                        _put(pixels, x, y, (27, 17, 12))
                for x, y, r, g, b in sprite['bright']:
                    _put(pixels, sx+x, top+y, (r, g, b))
                for x, y in sprite['dark']:
                    _put(pixels, sx+x, top+y, (0, 0, 0))
                with self.subTest(policy=policy, retained_tail=(tail.cx, tail.sy)):
                    value = normal_assess(self.lib, bytes(pixels), scene)[1]
                    self.assertIn(value.outcome, (1, 2))

    def test_new_numeric_tags_caps_and_auth_fields_are_independently_rechecked(self):
        for policy, pixels, scene in ((19, relative_single_pixels(), relative_single_scene()),
                                       (20, grouped_pixels(), grouped_scene())):
            base = self.negative(pixels, scene, policy)
            independent = self.independent()
            self.assertEqual(1, independent.goods121_consumer(C.byref(scene), C.byref(base)))
            self.assertGreater(base.partial_count, 2)
            changes = {
                'policy_swap': lambda w: setattr(w.certificate, 'policy_version', 39-policy),
                'all_tags_swap': lambda w: (setattr(w.certificate, 'policy_version', 39-policy),
                    setattr(w.certificate, 'board_mode', 39-policy)),
                'board_mode_swap': lambda w: setattr(w.certificate, 'board_mode', 39-policy),
                'layout': lambda w: setattr(w.certificate, 'layout_version', 2),
                'merchant': lambda w: setattr(w.certificate, 'merchant_score', .99),
                'prices': lambda w: setattr(w.certificate, 'observed_prices', 2),
                'extra_board': lambda w: setattr(w.certificate, 'unmatched_boards', 1),
                'cap_count': lambda w: setattr(w.certificate.endcaps[0], 'count', 624),
                'candidate': lambda w: setattr(w.rows[w.selected_row].slots[0], 'outcome', 1),
                'word_present_invalid_box': lambda w: (
                    setattr(w.rows[w.selected_row].slots[0], 'word_present', 1),
                    setattr(w.rows[w.selected_row].slots[0], 'word_iou', .1),
                    setattr(w.rows[w.selected_row].slots[0], 'word_coverage', .1),
                    w.rows[w.selected_row].slots[0].word_box.__setitem__(0, -1)),
                'word_absent_nonfinite': lambda w: (
                    setattr(w.rows[w.selected_row].slots[0], 'word_present', 0),
                    setattr(w.rows[w.selected_row].slots[0], 'word_iou', float('nan'))),
                'word_absent_nonzero_box': lambda w: (
                    setattr(w.rows[w.selected_row].slots[0], 'word_present', 0),
                    w.rows[w.selected_row].slots[0].word_box.__setitem__(0, 1)),
                'tail_target': lambda w: setattr(w.partial[2], 'outcome', 1),
                'tail_word': lambda w: (setattr(w.partial[2], 'word_present', 1),
                    setattr(w.partial[2], 'word_iou', .90),
                    setattr(w.partial[2], 'word_coverage', .95)),
                'tail_duplicate': lambda w: w.partial.__setitem__(2, w.partial[0]),
                'tail_bad_coordinates': lambda w: setattr(w.partial[2], 'cx', -1),
                # The separate private UBSan cut proves the old arithmetic
                # overflow. These public numeric checks assert refusal only.
                'tail_cx_int32_min': lambda w: setattr(w.partial[2], 'cx', -(1 << 31)),
                'tail_cx_int32_max': lambda w: setattr(w.partial[2], 'cx', (1 << 31)-1),
                'tail_sy_int32_min': lambda w: setattr(w.partial[2], 'sy', -(1 << 31)),
                'tail_sy_int32_max': lambda w: setattr(w.partial[2], 'sy', (1 << 31)-1),
                'tail_bad_box': lambda w: w.partial[2].icon_box.__setitem__(0, -1),
                'tail_nonfinite': lambda w: setattr(w.partial[2], 'icon_upper_bound', float('nan')),
                'missing_selected_partial': lambda w: setattr(w, 'partial_count', 1),
                'partial_overflow': lambda w: setattr(w, 'partial_count', 13),
            }
            for index in (0, 1):
                changes.update({
                    f'first_partial{index}_word_present_invalid_box': lambda w, i=index: (
                        setattr(w.partial[i], 'word_present', 1),
                        setattr(w.partial[i], 'word_iou', .1),
                        setattr(w.partial[i], 'word_coverage', .1),
                        w.partial[i].word_box.__setitem__(0, -1)),
                    f'first_partial{index}_word_absent_nonfinite': lambda w, i=index: (
                        setattr(w.partial[i], 'word_present', 0),
                        setattr(w.partial[i], 'word_iou', float('nan'))),
                    f'first_partial{index}_word_absent_nonzero_box': lambda w, i=index: (
                        setattr(w.partial[i], 'word_present', 0),
                        w.partial[i].word_box.__setitem__(0, 1)),
                })
            if policy == 19:
                changes.update({
                    'floor2_outside20': lambda w: setattr(w.certificate.endcaps[0], 'floor_upper', 2),
                    'unused_sign': lambda w: w.certificate.sign_iou.__setitem__(1, .99),
                    'nan_sign': lambda w: w.certificate.sign_iou.__setitem__(0, float('nan')),
                    'sign_iou_above_one': lambda w: w.certificate.sign_iou.__setitem__(0, 1.0000001),
                    'sign_coverage_above_one': lambda w: w.certificate.sign_coverage.__setitem__(0, 1.0000001),
                    'glyph_outside_face': lambda w: w.certificate.sign_boxes[0].__setitem__(0,
                        w.certificate.board_boxes[0][0]-1),
                })
            else:
                self.assertGreater(base.row_count, 1)
                self.assertNotEqual(1, base.selected_row,
                    'the alias tampering below targets a non-selected normal row')
                changes.update({
                    'two_alt_caps': lambda w: setattr(w.certificate.endcaps[1], 'floor_upper', 2),
                    'bad_lower': lambda w: setattr(w.certificate.endcaps[0], 'floor_lower', 2),
                    'invented_auth': lambda w: w.certificate.sign_iou.__setitem__(0, .99),
                    'count149': lambda w: w.certificate.board_counts.__setitem__(0, 149),
                    'both_counts149': lambda w: w.certificate.board_counts.__setitem__(slice(None), (149, 149)),
                    'both_counts299': lambda w: w.certificate.board_counts.__setitem__(slice(None), (299, 299)),
                    'group_width_mismatch': lambda w: w.certificate.board_boxes[1].__setitem__(2, 30),
                    'group_height_mismatch': lambda w: w.certificate.board_boxes[1].__setitem__(3, 30),
                    'group_top_mismatch': lambda w: w.certificate.board_boxes[1].__setitem__(1,
                        w.certificate.board_boxes[1][1]+1),
                    'alias_left_int32_min': lambda w: setattr(w.rows[1], 'left', -(1 << 31)),
                    'alias_sy_int32_min': lambda w: setattr(w.rows[1], 'sy', -(1 << 31)),
                    'alias_slot_center': lambda w: setattr(w.rows[1].slots[0], 'cx',
                        w.rows[1].slots[0].cx+1),
                    'alias_domain_box': lambda w: w.rows[1].slots[0].non_target_icon_box.__setitem__(0,
                        w.rows[1].slots[0].non_target_icon_box[0]+1),
                    'alias_pose_box': lambda w: w.rows[1].slots[0].icon_box.__setitem__(2, 35),
                })
            for name, mutate in changes.items():
                value = Result.from_buffer_copy(bytes(base))
                mutate(value)
                with self.subTest(policy=policy, mutation=name):
                    self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
                    self.assertEqual(0, independent.goods121_consumer(C.byref(scene), C.byref(value)))
        old_scene = bottom.shop_scene()
        old = self.negative(bottom.shop_pixels(truncated_side=None), old_scene, 6)
        self.assertEqual(2, old.partial_count)
        self.assertEqual(1, self.independent().goods121_consumer(C.byref(old_scene), C.byref(old)))
        old.partial[2] = old.partial[0]
        old.partial_count = 3
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(old)))
        self.assertEqual(0, self.independent().goods121_consumer(C.byref(old_scene), C.byref(old)),
            'the new bounded tail is not an extension of any legacy numeric policy')

    def test_normal_new_producer_reaches_public_C_durable_restart_and_next_floor(self):
        for policy, pixels, scene in ((19, relative_single_pixels(), relative_single_scene()),
                                       (20, grouped_pixels(), grouped_scene())):
            with self.subTest(policy=policy):
                value = self.negative(pixels, scene, policy)
                lib = self.independent()
                cycle_functions(lib)
                h = native.NativeControllerTests(methodName='runTest')
                h.lib = lib
                h.setUp()
                self.addCleanup(h.doCleanups)
                h.engine = lib.ng2_controller_create_cycle(native.SECOND)
                h.addCleanup(lib.ng2_controller_destroy, h.engine)
                q = cycle.NativeCycle094Tests(methodName='runTest')
                q.lib, q.h = lib, h
                self.assertEqual(1, h.observe(native.Scene.from_buffer_copy(bytes(scene))))
                job = q.cycle()
                self.assertEqual(1, lib.ng2_controller_cycle_worker_begin(h.engine,
                    job.job_id, job.capture_id, job.prefix, h.now))
                expected = Result.from_buffer_copy(bytes(value))
                expected.started_ns = expected.finished_ns = 0
                value.started_ns, value.finished_ns = h.now, h.now+1
                normalized = Result.from_buffer_copy(bytes(value))
                normalized.started_ns = normalized.finished_ns = 0
                self.assertEqual(bytes(expected), bytes(normalized),
                    'only worker clocks may change between normal producer and C adoption')
                h.now += 2
                self.assertEqual(1, lib.ng2_controller_cycle_assess(h.engine,
                    job.job_id, job.capture_id, job.prefix, h.now, C.byref(value)))
                self.assertEqual((3, 0, 4),
                    (q.cycle().outcome, q.cycle().status, q.cycle().state))
                q.pause_observed()
                self.assertEqual(0, h.tick()[0], 'normal NEG alone is not durable restart authority')
                self.assertEqual(1, q.durable())
                ready, restart = h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(0, lib.ng2_controller_begin(h.engine,
                    restart.id, h.now, 1, 0, 1), 'durable intent must precede restart begin permission')
                self.assertEqual(1, q.intent(restart))
                q.next_floor(restart)
                self.assertEqual((1, 0), (h.status().restarts, h.status().terminal))
                waiting = q.cycle()
                self.assertEqual(1, lib.ng2_controller_cycle_outcome_commit(h.engine,
                    waiting.job_id, waiting.next_floor_capture_id, h.prefix, h.now))
                self.assertEqual((job.level_id+1, 0), (q.cycle().level_id, q.cycle().state))
