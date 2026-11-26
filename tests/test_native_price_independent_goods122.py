"""Explicit price-independent offer proof; procedural pixels are not phone acceptance."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_goods_coverage121 as prior
from tests import test_native_ring_bank094 as bank
from tests import test_native_single_sign_shop103 as single
from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests.test_native_ring094 import Result
from tests.test_native_perception import NativeScene
from tests.test_native_shop_coverage102 import normal_assess, _put
from tests.test_target_assessment087 import FEATURES

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ.get('NECRO122_GOODS_RING_SOURCE',
    str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))


def shop_scene():
    scene = single.shop_scene()
    for x in (-5, -4, -3):
        single.set_tile(scene, x, 1, 1)
    return scene


def shop_pixels(**kwargs):
    pixels = bytearray(single.shop_pixels(**kwargs))
    # Prices and catalog names are absent. The physical face, merchant,
    # three bodies, floor caps and the original target domain remain.
    for y0, y1 in ((160, 173), (222, 244)):
        for y in range(y0, y1):
            for x in range(249, 357):
                rgb = pixels[4*(y*896+x):4*(y*896+x)+3]
                if y0 == 222 or (min(rgb) > 140 and max(rgb)-min(rgb) < 40):
                    _put(pixels, x, y, (27, 17, 15))
    return bytes(pixels)


def consumer_library(directory):
    core = CORE.parent
    source = directory/'consumer.c'
    source.write_text('#include "'+str(core/'NG2Controller.c')+'"\n'
        'int goods122_consumer(const NG2Scene *s,const NG2RingResult *r){\n'
        ' NG2Controller p={0};p.cycle.full_seen=1;p.cycle_anchor=*s;\n'
        ' return cycle_negative_witness(&p,r);}\n')
    objects = []
    for path in (source, core/'NG2Beat.c', core/'NG2Navigation.c', core/'NG2Perception.c'):
        obj = directory/(path.stem+'.o')
        flags = ['-O0'] if path.stem in ('consumer', 'NG2Beat') else [
            '-O2', '-fno-fast-math', '-ffp-contract=off', '-frounding-math']
        subprocess.run(['cc', '-std=c11', *flags, '-Wall', '-Wextra', '-Werror',
            '-pedantic', '-fPIC', '-I'+str(core), '-c', str(path), '-o', str(obj)],
            check=True, capture_output=True)
        objects.append(str(obj))
    target = directory/'consumer.so'
    subprocess.run(['cc', '-shared', *objects, '-lm', '-o', str(target)],
        check=True, capture_output=True)
    lib = C.CDLL(str(target))
    lib.goods122_consumer.argtypes = [C.POINTER(NativeScene), C.POINTER(Result)]
    lib.goods122_consumer.restype = C.c_int
    return lib


class NativePriceIndependentGoods122Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='goods122-')
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

    def negative(self, pixels=None, scene=None):
        pixels = shop_pixels() if pixels is None else pixels
        scene = shop_scene() if scene is None else scene
        frozen = bytes(scene)
        status, value = normal_assess(self.lib, pixels, scene)
        self.assertEqual((0, 3, 2, 21, 4, 21), (status, value.outcome,
            value.coverage, value.certificate.policy_version,
            value.certificate.layout_version, value.certificate.board_mode),
            'observed complete merchandise and target absence do not require prices or catalog names')
        self.assertEqual(frozen, bytes(scene))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        return value

    def test_price_independent_full_strip_requires_real_goods_auth_and_observation(self):
        value = self.negative()
        w = value.certificate
        self.assertEqual((3, 3, 0, 0), (w.observed_items, w.non_target_items,
            w.observed_prices, w.unmatched_prices))
        self.assertTrue(all(list(box) == [0, 0, 0, 0] for box in w.price_boxes))
        self.assertTrue(all(list(box) == [0, 0, 0, 0] for box in w.name_boxes))
        self.assertGreaterEqual(w.merchant_score, .94)
        self.assertEqual(1, self.independent().goods122_consumer(
            C.byref(shop_scene()), C.byref(value)))
        cases = {'merchant_missing': shop_pixels(missing_merchant=True),
            'extra_board': shop_pixels(extra_board=True)}
        missing = bytearray(shop_pixels())
        for y in range(177, 219):
            for x in range(249, 285):
                _put(missing, x, y, (27, 17, 15))
        cases['body_missing'] = bytes(missing)
        cap = bytearray(shop_pixels())
        for y in range(189, 214):
            for x in range(219, 244):
                _put(cap, x, y, (0, 0, 0))
        cases['cap_unobserved'] = bytes(cap)
        for name, pixels in cases.items():
            with self.subTest(raw=name):
                self.assertNotEqual(3, normal_assess(self.lib, pixels, shop_scene())[1].outcome)
        for name in ('item', 'below', 'halo', 'rail', 'partial'):
            scene = shop_scene()
            if name == 'item': single.set_tile(scene, -4, 0, 0)
            elif name == 'below': single.set_tile(scene, -4, 1, 0)
            elif name == 'halo': scene.protected_cells[0] = 1
            elif name == 'rail': single.set_tile(scene, -7, -2, 0)
            else: scene.goods = 1
            with self.subTest(scene=name):
                self.assertNotEqual(3, normal_assess(self.lib, shop_pixels(), scene)[1].outcome)

    def test_every_cell_and_original_partial_keeps_image_and_word_candidate_priority(self):
        self.negative()
        sprite = FEATURES['icons'][0]
        for cell in range(-2, 4):
            pixels = bytearray(shop_pixels())
            sx, top = 267+36*cell-sprite['width']//2, 188
            for y in range(top, top+sprite['height']):
                for x in range(sx, sx+sprite['width']):
                    _put(pixels, x, y, (27, 17, 12))
            for x, y, r, g, b in sprite['bright']:
                _put(pixels, sx+x, top+y, (r, g, b))
            for x, y in sprite['dark']:
                _put(pixels, sx+x, top+y, (0, 0, 0))
            with self.subTest(cell=cell):
                value = normal_assess(self.lib, bytes(pixels), shop_scene())[1]
                self.assertIn(value.outcome, (1, 2))
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        pixels = bytearray(shop_pixels())
        for y, bits in enumerate(FEATURES['word']['rows_hex']):
            for x in range(84):
                if int(bits, 16) >> x & 1:
                    _put(pixels, 167+x, 135+y, (245, 245, 245))
        self.assertIn(normal_assess(self.lib, bytes(pixels), shop_scene())[1].outcome, (1, 2))

    def test_numeric_price_free_tag_and_own_anchor_reject_forged_fields(self):
        base = self.negative()
        lib = self.independent()
        mutations = {
            'old_policy': lambda r: setattr(r.certificate, 'policy_version', 7),
            'old_layout': lambda r: setattr(r.certificate, 'layout_version', 1),
            'wrong_mode': lambda r: setattr(r.certificate, 'board_mode', 7),
            'fake_prices': lambda r: setattr(r.certificate, 'observed_prices', 3),
            'unmatched_price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
            'price_box': lambda r: r.certificate.price_boxes[0].__setitem__(0, 1),
            'merchant_nan': lambda r: setattr(r.certificate, 'merchant_score', float('nan')),
            'merchant_weak': lambda r: setattr(r.certificate, 'merchant_score', .939),
            'missing_item': lambda r: setattr(r.certificate, 'observed_items', 2),
            'cap_missing': lambda r: setattr(r.certificate.endcaps[0], 'black_count', 63),
            'candidate': lambda r: setattr(r.rows[r.selected_row].slots[1], 'outcome', 1),
            'alias_int32_min': lambda r: setattr(r.rows[0], 'left', -(1 << 31)),
            'partial_overflow': lambda r: setattr(r, 'partial_count', 13),
            'partial_bad_word': lambda r: setattr(r.partial[0], 'word_iou', float('nan')),
        }
        for name, mutate in mutations.items():
            value = Result.from_buffer_copy(bytes(base)); mutate(value)
            with self.subTest(mutation=name):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
                self.assertEqual(0, lib.goods122_consumer(C.byref(shop_scene()), C.byref(value)))
        # These are untrusted-boundary cuts, never normal producer packets.
        alias = Result.from_buffer_copy(bytes(base))
        alias.row_count = 2; alias.rows[1] = alias.rows[0]
        alias.rows[1].slots[2].outcome = 1
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(alias)))
        self.assertEqual(0, lib.goods122_consumer(C.byref(shop_scene()), C.byref(alias)))
        tail = Result.from_buffer_copy(bytes(base)); tail.partial_count = 3
        extra = tail.partial[2]
        extra.cx, extra.sy = 195, 153
        extra.icon_score = extra.icon_upper_bound = .1
        extra.icon_box[:] = (179, 177, 32, 28)
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(tail)))
        self.assertEqual(1, lib.goods122_consumer(C.byref(shop_scene()), C.byref(tail)))
        for name in ('candidate', 'duplicate', 'bad_coordinate', 'bad_word'):
            value = Result.from_buffer_copy(bytes(tail))
            if name == 'candidate': value.partial[2].outcome = 1
            elif name == 'duplicate': value.partial[2] = value.partial[0]
            elif name == 'bad_coordinate': value.partial[2].cx = -(1 << 31)
            else: value.partial[2].word_iou = float('nan')
            with self.subTest(tail=name):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
                self.assertEqual(0, lib.goods122_consumer(C.byref(shop_scene()), C.byref(value)))
        for name in ('item', 'below', 'halo', 'rail'):
            scene = shop_scene()
            if name == 'item': single.set_tile(scene, -4, 0, 0)
            elif name == 'below': single.set_tile(scene, -4, 1, 0)
            elif name == 'halo': scene.protected_cells[0] = 1
            else: single.set_tile(scene, -7, -2, 0)
            with self.subTest(own_anchor=name):
                self.assertEqual(0, lib.goods122_consumer(C.byref(scene), C.byref(base)))

    def test_normal_price_free_producer_reaches_durable_public_restart(self):
        value = self.negative(); scene = shop_scene(); lib = self.independent()
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
