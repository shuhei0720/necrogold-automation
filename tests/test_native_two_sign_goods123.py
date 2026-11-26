"""Finite two-SIGN offer proofs from public procedural pixels.

These checks model the TEST123 boundaries; they embed no phone image and do
not establish iPhone timing, classification accuracy, or real restart success.
"""
import ctypes as C
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_goods_coverage121 as prior
from tests import test_native_ring_bank094 as bank
from tests import test_native_shop_coverage102 as bottom
from tests.test_native_perception import NativeScene
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests.test_native_shop_coverage102 import normal_assess, _put
from tests.test_target_assessment087 import FEATURES, WIDTH

ROOT = Path(__file__).resolve().parents[1]
RING = Path(os.environ.get('NECRO123_RING_SOURCE',
    str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
CONTROLLER = Path(os.environ.get('NECRO123_CONTROLLER_SOURCE',
    str(RING.parent/'NG2Controller.c')))


def shop_scene(left=301, sy=117):
    ax, ay = round((left-448)/36), round((sy+48-207)/36)
    scene = bottom.shop_scene(ax=ax, ay=ay)
    for x in range(ax, ax+3):
        bottom.set_tile(scene, x, ay+1, 1)
    return scene


def vertical_cap(pixels, left, sy, side=1):
    """Fixed complete 12x25/13x25 partition, with the old floor predicate.

    Blue texture supplies positive variance without changing the medians by
    a post-hoc threshold. The horizontal upper median fails the old floor
    test; both vertical halves and the whole/lower samples pass it.
    """
    x0, y0 = left+(-48 if side == 0 else 96), sy+36
    for yy in range(25):
        for xx in range(25):
            if yy < 12:
                colour = (39, 23, 21) if xx < 12 else (46, 26, 22)
            else:
                colour = (27, 18, 17) if xx < 12 else (38, 23, 21)
            r, g, b = colour
            _put(pixels, x0+xx, y0+yy,
                 (r, g, b+6 if (xx+2*yy) % 4 == 0 else b))


def shop_pixels(kind='horizontal', *, prices=False, vertical=False, **kwargs):
    left, sy = (483, 44) if kind == 'hud_edge' else (301, 117)
    faces = ((-14, -14, 29, 29), (-13, -14, 29, 29))
    if kind == 'fragment':
        faces = ((-14, -14, 29, 29), (-14, -14, 29, 23))
    elif kind == 'hud_edge':
        faces = ((-14, -14, 29, 29), (-14, -14, 29, 17))
    elif kind == 'right_master':
        faces = ((-14, -14, 29, 23), (-14, -14, 29, 29))
    pixels = bytearray(bottom.shop_pixels(left=left, sy=sy,
        face_boxes=faces, **kwargs))
    # Catalog names and price glyphs are optional. Removing neutral white
    # names does not remove the two yellow physical faces or item bodies.
    for y in range(max(0, sy-6), sy+24):
        for x in range(left-18, left+90):
            rgb = pixels[4*(y*WIDTH+x):4*(y*WIDTH+x)+3]
            if min(rgb) > 140 and max(rgb)-min(rgb) < 40:
                _put(pixels, x, y, (27, 17, 15))
    if not prices:
        for y in range(sy+69, sy+91):
            for x in range(left-54, left+126):
                rgb = pixels[4*(y*WIDTH+x):4*(y*WIDTH+x)+3]
                if min(rgb) > 140 and max(rgb)-min(rgb) < 40:
                    _put(pixels, x, y, (27, 17, 15))
    if vertical:
        vertical_cap(pixels, left, sy)
    return bytes(pixels)


def consumer_library(directory):
    """Independent own-anchor numeric cut; not historical private state."""
    core = CONTROLLER.parent
    source = directory/'consumer123.c'
    source.write_text('#include "'+str(CONTROLLER)+'"\n'
        'int goods123_consumer(const NG2Scene*s,const NG2RingResult*r){\n'
        ' NG2Controller p={0};p.cycle.full_seen=1;p.cycle_anchor=*s;\n'
        ' return cycle_negative_witness(&p,r);}\n')
    objects = []
    for path in (source, core/'NG2Beat.c', core/'NG2Navigation.c', core/'NG2Perception.c'):
        target = directory/(path.stem+'.o')
        flags = ['-O0'] if path.stem in ('consumer123', 'NG2Beat') else [
            '-O2', '-fno-fast-math', '-ffp-contract=off', '-frounding-math']
        subprocess.run(['cc', '-std=c11', *flags, '-Wall', '-Wextra', '-Werror',
            '-pedantic', '-fPIC', '-I'+str(core), '-c', str(path), '-o', str(target)],
            check=True, capture_output=True)
        objects.append(str(target))
    target = directory/'consumer123.so'
    subprocess.run(['cc', '-shared', *objects, '-lm', '-o', str(target)],
        check=True, capture_output=True)
    lib = C.CDLL(str(target))
    lib.goods123_consumer.argtypes = [C.POINTER(NativeScene), C.POINTER(Result)]
    lib.goods123_consumer.restype = C.c_int
    return lib


def put_target(pixels, cx, sy):
    sprite = FEATURES['icons'][0]
    x0, y0 = cx-sprite['width']//2, sy+35
    for y in range(y0, y0+sprite['height']):
        for x in range(x0, x0+sprite['width']):
            _put(pixels, x, y, (27, 17, 12))
    for x, y, r, g, b in sprite['bright']:
        _put(pixels, x0+x, y0+y, (r, g, b))
    for x, y in sprite['dark']:
        _put(pixels, x0+x, y0+y, (0, 0, 0))


class NativeTwoSignGoods123Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='goods123-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = bank.NativeRingBank094Tests.build_library(RING,
            Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    @classmethod
    def independent(cls):
        if not hasattr(cls, '_consumer'):
            cls._consumer = consumer_library(Path(cls.tmp.name))
        return cls._consumer

    def negative(self, kind='horizontal', *, pixels=None, scene=None, vertical=False):
        left, sy = (483, 44) if kind == 'hud_edge' else (301, 117)
        scene = shop_scene(left, sy) if scene is None else scene
        pixels = shop_pixels(kind, vertical=vertical) if pixels is None else pixels
        frozen = bytes(scene)
        status, value = normal_assess(self.lib, pixels, scene)
        self.assertEqual((0, 3, 2, 22, 5, 22), (status, value.outcome,
            value.coverage, value.certificate.policy_version,
            value.certificate.layout_version, value.certificate.board_mode),
            'one observed physical two-board row needs complete price-free coverage')
        self.assertEqual(frozen, bytes(scene))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        self.assertEqual(1, self.independent().goods123_consumer(C.byref(scene), C.byref(value)))
        return value

    def rejected(self, value, scene=None):
        scene = shop_scene() if scene is None else scene
        with self.subTest(verifier='ring'):
            self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        with self.subTest(verifier='independent_controller'):
            self.assertEqual(0, self.independent().goods123_consumer(C.byref(scene), C.byref(value)))

    def test_normal_bbox_seed_set_and_deterministic_master(self):
        expected = {'horizontal': [(301, 117), (302, 117)],
            'fragment': [(301, 117), (301, 114)],
            'right_master': [(301, 117), (301, 114)],
            'hud_edge': [(483, 44), (483, 38)]}
        for kind, rows in expected.items():
            with self.subTest(kind=kind):
                value = self.negative(kind)
                self.assertEqual((0, 0, 2), (value.selected_row,
                    value.certificate.row_index, value.row_count))
                self.assertEqual(rows, [(r.left, r.sy) for r in value.rows[:value.row_count]])
                self.assertEqual([-1]*value.row_count,
                    [r.word_slot for r in value.rows[:value.row_count]],
                    'price-free rows do not assign an observed target-name slot')
                self.assertGreaterEqual(value.partial_count, 4)
                self.assertEqual([(left+36*k, sy) for left, sy in rows for k in (-1, 3)],
                    [(p.cx, p.sy) for p in value.partial[:4]])
                w = value.certificate
                self.assertEqual((3, 3, 0, 0), (w.observed_items, w.non_target_items,
                    w.observed_prices, w.unmatched_prices))
                self.assertTrue(all(list(box) == [0]*4 for box in w.price_boxes))
                self.assertTrue(all(list(box) == [0]*4 for box in w.name_boxes))
                self.assertEqual((0, 0), (w.merchant_score, w.merchant_coverage))

    def test_fixed_vertical_cap_covers_all625(self):
        value = self.negative(vertical=True)
        w = value.certificate
        self.assertEqual([1, 3], [cap.floor_upper for cap in w.endcaps])
        cap = w.endcaps[1]
        self.assertEqual((625, 1, 1), (cap.count, cap.floor_full, cap.floor_lower))
        left, right = list(w.sign_boxes[1]), list(w.board_edge_counts[1])
        bright = list(w.board_corner_counts[1])
        self.assertEqual((cap.black_count, cap.bright_count),
            (left[3]+right[3], bright[0]+bright[1]))
        self.assertEqual((1, 1), tuple(bright[2:]))
        # Both fixed halves are present. Blacking either half cannot be
        # replaced by the other half or by the full-sample median.
        for x0, width in ((397, 12), (409, 13)):
            pixels = bytearray(shop_pixels(vertical=True))
            for y in range(153, 178):
                for x in range(x0, x0+width):
                    _put(pixels, x, y, (0, 0, 0))
            self.assertNotEqual(3, normal_assess(self.lib, bytes(pixels), shop_scene())[1].outcome)

    def test_missing_observation_or_actual_face_stays_unknown(self):
        self.negative()
        for name in ('item', 'below', 'halo', 'extra_item', 'partial'):
            scene = shop_scene()
            if name == 'item': bottom.set_tile(scene, -4, -1, 0)
            elif name == 'below': bottom.set_tile(scene, -4, 0, 0)
            elif name == 'halo': scene.protected_cells[0] = 1
            elif name == 'extra_item': bottom.set_tile(scene, 8, 3, 6)
            else: scene.goods = 1
            with self.subTest(scene=name):
                self.assertNotEqual(3, normal_assess(self.lib, shop_pixels(), scene)[1].outcome)
        for name in ('body_missing', 'cap_unobserved', 'extra_board', 'actual_hud'):
            pixels = bytearray(shop_pixels(extra_board=name == 'extra_board'))
            if name == 'body_missing':
                for y in range(141, 184):
                    for x in range(283, 319): _put(pixels, x, y, (27, 17, 15))
            elif name == 'cap_unobserved':
                for y in range(153, 178):
                    for x in range(253, 278): _put(pixels, x, y, (0, 0, 0))
            elif name == 'actual_hud':
                pixels = bytearray(shop_pixels('hud_edge'))
                # Move the physical left face into the fixed right HUD.
                bottom.draw_faces(pixels, 483, 44, ((-14, -20, 29, 29), (-14, -20, 29, 17)))
            with self.subTest(raw=name):
                scene = shop_scene(483, 44) if name == 'actual_hud' else shop_scene()
                self.assertNotEqual(3, normal_assess(self.lib, bytes(pixels), scene)[1].outcome)

    def test_all_alias_edges_and_tail_keep_candidate_priority(self):
        self.negative('fragment')
        for left, sy in ((301, 117), (301, 114)):
            for cell in (-1, 0, 1, 2, 3):
                pixels = bytearray(shop_pixels('fragment'))
                put_target(pixels, left+36*cell, sy)
                with self.subTest(alias=(left, sy), cell=cell):
                    value = normal_assess(self.lib, bytes(pixels), shop_scene())[1]
                    self.assertIn(value.outcome, (1, 2))
                    self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        base = self.negative()
        for where in ('alias_slot', 'alias_outer', 'tail'):
            value = Result.from_buffer_copy(bytes(base))
            if where == 'alias_slot': slot = value.rows[1].slots[2]
            elif where == 'alias_outer': slot = value.partial[3]
            else:
                prefix = 2*value.row_count
                if value.partial_count > prefix:
                    slot = value.partial[prefix]
                else:
                    slot = value.partial[value.partial_count]
                    value.partial_count += 1
                    slot.cx, slot.sy = 229, 117
                    slot.icon_score = slot.icon_upper_bound = .1
                    slot.icon_box[:] = (213, 141, 32, 28)
                # A structurally valid safe tail is accepted before its
                # positive outcome is introduced at the untrusted boundary.
                self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
                self.assertEqual(1, self.independent().goods123_consumer(
                    C.byref(shop_scene()), C.byref(value)))
            slot.outcome = 1
            with self.subTest(candidate=where): self.rejected(value)
        pixels = bytearray(shop_pixels('fragment'))
        for y, bits in enumerate(FEATURES['word']['rows_hex']):
            for x in range(84):
                if int(bits, 16) >> x & 1:
                    _put(pixels, 205+x, 100+y, (245, 245, 245))
        self.assertIn(normal_assess(self.lib, bytes(pixels), shop_scene())[1].outcome, (1, 2))

    def test_numeric_expected_rows_and_full_outer_prefix_reject_deletion_or_reorder(self):
        base = self.negative('fragment')
        mutations = {
            'whole_alias_and_outer_pair': lambda r: (setattr(r, 'row_count', 1),
                setattr(r, 'partial_count', r.partial_count-2)),
            'missing_row': lambda r: setattr(r, 'row_count', 1),
            'extra_row': lambda r: setattr(r, 'row_count', 3),
            'duplicate_row': lambda r: r.rows.__setitem__(1, r.rows[0]),
            'row_reorder': lambda r: self.swap(r.rows, 0, 1),
            'missing_outer': lambda r: setattr(r, 'partial_count', 3),
            'duplicate_outer': lambda r: r.partial.__setitem__(3, r.partial[2]),
            'outer_reorder': lambda r: self.swap(r.partial, 2, 3),
            'wrong_outer_strip': lambda r: r.partial[3].non_target_icon_box.__setitem__(0,
                r.partial[3].non_target_icon_box[0]+1),
            'bad_seed': lambda r: setattr(r.rows[1], 'left', r.rows[1].left+36),
            'bad_board_center': lambda r: r.certificate.board_boxes[1].__setitem__(0,
                r.certificate.board_boxes[1][0]+36),
            'row_nan_word': lambda r: setattr(r.rows[1].slots[1], 'word_iou', float('nan')),
            'row_name_slot': lambda r: setattr(r.rows[1], 'word_slot', 0),
            'row_sy_int32_max': lambda r: (setattr(r.rows[0], 'sy', (1 << 31)-1),
                r.certificate.row.__setitem__(1, (1 << 31)-1)),
            'row_sy_int32_min': lambda r: (setattr(r.rows[0], 'sy', -(1 << 31)),
                r.certificate.row.__setitem__(1, -(1 << 31))),
            'row_left_int32_max': lambda r: (setattr(r.rows[0], 'left', (1 << 31)-1),
                r.certificate.row.__setitem__(0, (1 << 31)-1)),
            'row_left_int32_min': lambda r: (setattr(r.rows[0], 'left', -(1 << 31)),
                r.certificate.row.__setitem__(0, -(1 << 31))),
            'outer_nan_word': lambda r: setattr(r.partial[3], 'word_iou', float('nan')),
        }
        for name, mutate in mutations.items():
            value = Result.from_buffer_copy(bytes(base)); mutate(value)
            with self.subTest(mutation=name): self.rejected(value)
        for name in ('below', 'halo', 'item'):
            scene = shop_scene()
            if name == 'below': bottom.set_tile(scene, -3, 0, 0)
            elif name == 'item': bottom.set_tile(scene, -3, -1, 0)
            else: scene.protected_cells[0] = 1
            with self.subTest(own_anchor=name):
                self.assertEqual(0, self.independent().goods123_consumer(C.byref(scene), C.byref(base)))

    @staticmethod
    def swap(array, a, b):
        first, second = type(array[a]).from_buffer_copy(bytes(array[a])), type(array[b]).from_buffer_copy(bytes(array[b]))
        array[a], array[b] = second, first

    def test_vertical_numeric_stats_and_tags_reject_forgery(self):
        base = self.negative(vertical=True)
        mutations = {
            'marker_without_proof': lambda r: r.certificate.sign_boxes[1].__setitem__(2, 0),
            'missing_half': lambda r: r.certificate.board_edge_counts[1].__setitem__(0, 0),
            'black_sum': lambda r: r.certificate.sign_boxes[1].__setitem__(3, 1),
            'bright_sum': lambda r: r.certificate.board_corner_counts[1].__setitem__(0, 1),
            'no_texture': lambda r: r.certificate.board_corner_counts[1].__setitem__(2, 0),
            'invalid_spread': lambda r: r.certificate.board_corner_counts[1].__setitem__(3, 2),
            'rgb_negative': lambda r: r.certificate.sign_boxes[1].__setitem__(0, -1),
            'rgb_overflow': lambda r: r.certificate.board_edge_counts[1].__setitem__(2, 256),
            'black_negative': lambda r: r.certificate.sign_boxes[1].__setitem__(3, -1),
            'black_overflow': lambda r: r.certificate.board_edge_counts[1].__setitem__(3, 326),
            'marker_mixed_with_old_policy': lambda r: setattr(r.certificate, 'policy_version', 20),
            'old_layout': lambda r: setattr(r.certificate, 'layout_version', 4),
            'old_mode': lambda r: setattr(r.certificate, 'board_mode', 21),
            'fake_prices': lambda r: setattr(r.certificate, 'observed_prices', 3),
            'price_box': lambda r: r.certificate.price_boxes[0].__setitem__(0, 1),
            'fake_merchant': lambda r: setattr(r.certificate, 'merchant_score', .99),
            'two_vertical_caps': lambda r: setattr(r.certificate.endcaps[0], 'floor_upper', 3),
        }
        for name, mutate in mutations.items():
            value = Result.from_buffer_copy(bytes(base)); mutate(value)
            with self.subTest(mutation=name): self.rejected(value)
        ordinary = self.negative()
        ordinary.certificate.sign_boxes[0][0] = 1
        self.rejected(ordinary)
        # Numeric trust-boundary cuts isolate the existing 90% visibility
        # and area-scaled bright bounds; they are not normal raw packets.
        for name, accepted, rejected in (('black_left', 30, 31),
                ('bright_left', 11, 12), ('bright_right', 12, 13)):
            for amount, expected in ((accepted, 1), (rejected, 0)):
                value = Result.from_buffer_copy(bytes(base)); w = value.certificate
                if name == 'black_left':
                    w.sign_boxes[1][3] = w.endcaps[1].black_count = amount
                else:
                    half = 0 if name == 'bright_left' else 1
                    w.board_corner_counts[1][half] = w.endcaps[1].bright_count = amount
                with self.subTest(boundary=name, amount=amount):
                    self.assertEqual(expected, self.lib.ng2_ring_negative_certificate(C.byref(value)))
                    self.assertEqual(expected, self.independent().goods123_consumer(
                        C.byref(shop_scene()), C.byref(value)))

    def test_deadline_cancel_mode_boundaries(self):
        self.negative()
        pixels, scene = shop_pixels(), shop_scene()
        for at, expected in ((99, 0), (100, 2), (101, 2)):
            clock, cancel = Clock(lambda _, at=at: at), Cancelled(lambda _: 0)
            options = Options(abi=1, size=C.sizeof(Options), mode=2,
                deadline_ns=100, now_ns=clock, cancelled=cancel,
                scene=C.addressof(scene), fast=1)
            value = Result(); buf = C.create_string_buffer(pixels)
            with self.subTest(at=at):
                self.assertEqual(expected, self.lib.ng2_ring_assess_rgba(buf,
                    len(pixels), WIDTH*4, C.byref(options), C.byref(value)))
                if at == 99: self.assertEqual(3, value.outcome)
                else: self.assertNotEqual(3, value.outcome)
        value = normal_assess(self.lib, pixels, scene, cancelled=True)[1]
        self.assertEqual(1, value.status)
        self.assertNotEqual(3, value.outcome)
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.assertNotEqual(22, normal_assess(self.lib, pixels, scene, mode=mode)[1].certificate.policy_version)

    def test_normal_durable_public_restart(self):
        value, scene, lib = self.negative(), shop_scene(), self.independent()
        prior.cycle_functions(lib)
        h = native.NativeControllerTests(methodName='runTest'); h.lib = lib; h.setUp()
        self.addCleanup(h.doCleanups)
        h.engine = lib.ng2_controller_create_cycle(native.SECOND)
        h.addCleanup(lib.ng2_controller_destroy, h.engine)
        q = cycle.NativeCycle094Tests(methodName='runTest'); q.lib, q.h = lib, h
        self.assertEqual(1, h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        job = q.cycle()
        self.assertEqual(1, lib.ng2_controller_cycle_worker_begin(h.engine,
            job.job_id, job.capture_id, job.prefix, h.now))
        value.started_ns, value.finished_ns = h.now, h.now+1; h.now += 2
        self.assertEqual(1, lib.ng2_controller_cycle_assess(h.engine,
            job.job_id, job.capture_id, job.prefix, h.now, C.byref(value)))
        self.assertEqual((3, 0, 4), (q.cycle().outcome, q.cycle().status, q.cycle().state))
        q.pause_observed()
        self.assertEqual(0, h.tick()[0])
        self.assertEqual(1, q.durable())
        ready, restart = h.tick(); self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, lib.ng2_controller_begin(h.engine, restart.id, h.now, 1, 0, 1))
        self.assertEqual(1, q.intent(restart)); q.next_floor(restart)
        waiting = q.cycle()
        self.assertEqual(1, lib.ng2_controller_cycle_outcome_commit(h.engine,
            waiting.job_id, waiting.next_floor_capture_id, h.prefix, h.now))
        self.assertEqual((job.level_id+1, 0), (q.cycle().level_id, q.cycle().state))
