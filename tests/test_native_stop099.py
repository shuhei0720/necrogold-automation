"""TEST099 read-only stop companion; public procedural C, not device replay."""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_entry097 as entry
from tests import test_native_passage072 as passage


class StopDetail(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32)] + [
        (name, C.c_int32) for name in ('valid', 'stage', 'reason', 'wait_kind', 'passage_bit',
            'passage_unlocalized_gold', 'x', 'y', 'validation', 'motion_kind', 'motion_dx', 'motion_dy')] + [
        ('passage_pending', C.c_uint32), ('passage_unresolved', C.c_uint32)] + [
        (name, C.c_uint64) for name in ('at_ns', 'source_capture_id', 'observed_capture_id',
            'anchor_capture_id', 'prefix', 'deadline_ns', 'last_comparison_capture_id')]


def stop_detail(lib, engine):
    out = StopDetail()
    query = getattr(lib, 'ng2_controller_stop_detail', None)
    if query is not None:
        query.argtypes = [C.c_void_p, C.POINTER(StopDetail)]
        query(engine, C.byref(out))
    # Before the companion exists, zero is an honest missing diagnostic. The
    # expected snapshot assertions provide the semantic Red, not compilation.
    return out


class NativeStop099Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry.NativePartialEntry097Tests.setUpClass()
        cls.lib = entry.NativePartialEntry097Tests.lib

    @classmethod
    def tearDownClass(cls):
        entry.NativePartialEntry097Tests.tearDownClass()

    def setUp(self):
        self.p = entry.NativePartialEntry097Tests(methodName='runTest')
        self.p.setUp(); self.addCleanup(self.p.doCleanups)
        self.h, self.q = self.p.h, self.p.q

    def detail(self):
        return stop_detail(self.lib, self.h.engine)

    def test_first_generic_stop_is_frozen_before_cleanup_and_late_callbacks(self):
        self.h.now += 10
        at = self.h.now
        self.lib.ng2_controller_cancel(self.h.engine, at, 2)
        value = self.detail()
        self.assertEqual((1, 1, 2, at), (value.valid, value.stage, value.reason, value.at_ns),
                         'first cancellation must have an immutable, independently queryable stop snapshot')
        frozen = bytes(value)
        self.lib.ng2_controller_cancel(self.h.engine, at + 50, 5)
        self.h.now += 100; self.h.tick()
        self.assertEqual(frozen, bytes(self.detail()))

    def test_post_credit_failure_reports_exact_comparison_and_original_anchor(self):
        terrain, _ = self.p.pending()
        source = self.q.cycle()
        self.p.observe(terrain)
        self.assertEqual(0, self.q.cycle().state)
        changed = deepcopy(terrain); changed.protected.add((8, 4))
        self.p.observe(changed)
        out = self.detail()
        self.assertEqual((1, 4, 17, source.capture_id, self.h.number, source.capture_id, self.h.prefix),
            (out.valid, out.stage, out.reason, out.source_capture_id, out.observed_capture_id,
             out.anchor_capture_id, out.prefix),
            'the after-credit rejection must retain its first actual frame and frozen classifier source')
        self.assertEqual((9, source.continuation_deadline_ns), (out.validation, out.deadline_ns))
        frozen = bytes(out)
        self.h.now += 10_000_000; self.h.tick()
        self.assertEqual(frozen, bytes(self.detail()))

    def test_post_credit_motion_unknown_still_stops_and_reports_zero_credit(self):
        terrain, _ = self.p.pending()
        source = self.q.cycle(); self.p.observe(terrain)
        changed = deepcopy(terrain); changed.signature = bytes(255-n for n in terrain.signature)
        self.p.observe(changed)
        out = self.detail()
        self.assertEqual((1, 4, 17, 11, 0, 0, 0),
            (out.valid, out.stage, out.reason, out.validation, out.motion_kind, out.motion_dx, out.motion_dy))
        self.assertEqual((source.capture_id, self.h.number), (out.source_capture_id, out.observed_capture_id))
        self.assertEqual((7, 2, 1), (self.q.cycle().state, self.h.status().inputs, self.h.status().moves),
                         'diagnostics must preserve the original stop, without speculative walking recovery')

    def test_observe_more_rejection_uses_distinct_stage_without_new_input(self):
        terrain, _ = self.p.pending()
        changed = deepcopy(terrain); changed.tiles[(0, -1)] = 'dirt'
        self.p.observe(changed)
        out = self.detail()
        self.assertEqual((1, 3, 17, 10, self.q.cycle().capture_id, self.h.number),
            (out.valid, out.stage, out.reason, out.validation, out.anchor_capture_id, out.observed_capture_id))
        self.assertEqual((2, 1), (self.h.status().inputs, self.h.status().moves))

    def test_live_passage_anchor_last_failed_comparison_and_timeout_are_preserved(self):
        h = passage.NativePassage072Tests(methodName='runTest')
        h.lib = self.lib; h.setUp(); self.addCleanup(h.doCleanups)
        terrain, _ = h.walk_to_goal()
        live = stop_detail(self.lib, h.engine)
        self.assertEqual((0, 2, 1, h.number), (live.valid, live.stage, live.wait_kind, live.anchor_capture_id),
                         'a live wait anchor must be visible before failure so Runtime can retain its image')
        bad = deepcopy(terrain); bad.signature = bytes(255-n for n in terrain.signature)
        h.now += 100_000_000; h.observe(bad)
        compared = stop_detail(self.lib, h.engine)
        self.assertEqual((h.number, 11, 0),
            (compared.last_comparison_capture_id, compared.validation, compared.motion_kind))
        h.now = live.deadline_ns + 1; h.tick()
        stopped = stop_detail(self.lib, h.engine)
        self.assertEqual((1, 2, 12, 1, live.anchor_capture_id, compared.last_comparison_capture_id),
            (stopped.valid, stopped.stage, stopped.reason, stopped.wait_kind,
             stopped.anchor_capture_id, stopped.last_comparison_capture_id))
        self.assertNotEqual(0, stopped.passage_unresolved)

    def test_companion_query_is_read_only_null_safe_and_keeps_old_abi(self):
        terrain, _ = self.p.pending()
        before = bytes(self.h.status()), bytes(self.q.cycle()), tuple(bytes(e) for e in self.h.events())
        first = bytes(self.detail()); self.assertEqual(first, bytes(self.detail()))
        self.assertEqual(before, (bytes(self.h.status()), bytes(self.q.cycle()), tuple(bytes(e) for e in self.h.events())))
        self.assertEqual((23864, 192, 128, 216, 120),
            (C.sizeof(native.Scene), C.sizeof(native.Status), C.sizeof(native.Event),
             C.sizeof(entry.cycle094.Cycle), C.sizeof(StopDetail)))
        self.assertEqual(1, self.detail().abi_version)
        self.assertEqual(120, self.detail().struct_size)
        self.assertEqual(bytes(StopDetail()), bytes(stop_detail(self.lib, None)))


if __name__ == '__main__':
    unittest.main()
