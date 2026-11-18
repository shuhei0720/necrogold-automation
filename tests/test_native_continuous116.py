"""Explicit continuous-mode boundary over the normal public native lifecycle.

The before adapter keeps the old restart-yield implementation enabled and
lets its ordinary tick emit PAUSE. Failure is the forbidden PAUSE/lack of an
unpaused terminal, rather than a missing new symbol or compilation failure.
No iPhone speed or queue-drain acceptance is claimed here.
"""
import ctypes as C
import os
import unittest

from tests import test_native_restart_yield112 as yield112
from tests.test_native_handoff099 import handoff


class Continuous(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32)] + [
        (name, C.c_int32) for name in ('enabled', 'successor_floor', 'qualified', 'reserved')
    ] + [(name, C.c_uint64) for name in (
        'root_deadline_ns', 'qualified_ns', 'parent_deadline_ns', 'old_job_id',
        'restart_command_id', 'new_floor_capture_id', 'source_capture_id',
        'source_start_ns', 'source_prefix')]


class NativeContinuous116Tests(unittest.TestCase):
    # Reuse the old public lifecycle helpers, without inheriting its old-mode
    # test methods as contradictory new-mode discovery cases.
    setUp = yield112.NativeRestartYield112Tests.setUp
    state = yield112.NativeRestartYield112Tests.state
    permit = yield112.NativeRestartYield112Tests.permit
    first_pause = yield112.NativeRestartYield112Tests.first_pause
    walked_negative = yield112.NativeRestartYield112Tests.walked_negative
    new_floor = yield112.NativeRestartYield112Tests.new_floor
    goods = yield112.NativeRestartYield112Tests.goods
    probe = yield112.NativeRestartYield112Tests.probe

    @classmethod
    def setUpClass(cls):
        yield112.NativeRestartYield112Tests.setUpClass.__func__(cls)
        cls.has_continuous = hasattr(cls.lib, 'ng2_controller_enable_continuous')
        if not cls.has_continuous and os.environ.get('NECRO116_CONTINUOUS_BEFORE') != '1':
            raise RuntimeError('Missing API is not a semantic Red; select explicit before adapter')
        if cls.has_continuous:
            cls.lib.ng2_controller_enable_continuous.argtypes = [C.c_void_p, C.c_int32, C.c_uint64]
            cls.lib.ng2_controller_continuous_status.argtypes = [C.c_void_p, C.POINTER(Continuous)]
            cls.lib.ng2_controller_continuous_finish.argtypes = [C.c_void_p] + [C.c_uint64] * 4

    @classmethod
    def tearDownClass(cls):
        yield112.NativeRestartYield112Tests.tearDownClass.__func__(cls)

    def engine(self, enabled=True, successor=False, deadline=None):
        self.successor = successor
        self.root_deadline = deadline
        return yield112.NativeRestartYield112Tests.engine(self, enabled=enabled)

    def enable(self):
        if not self.has_continuous:
            return yield112.NativeRestartYield112Tests.enable(self)
        self.root_deadline = self.root_deadline or self.h.status().started_ns + 2880_000_000_000
        return self.lib.ng2_controller_enable_continuous(
            self.h.engine, int(self.successor), self.root_deadline)

    def continuous(self):
        value = Continuous()
        if self.has_continuous:
            self.lib.ng2_controller_continuous_status(self.h.engine, C.byref(value))
        return value

    def finish_continuous(self, capture=None, start=None, prefix=None):
        state = self.h.status()
        capture = state.last_capture_id if capture is None else capture
        start = state.last_capture_start_ns if start is None else start
        prefix = self.h.prefix if prefix is None else prefix
        if self.has_continuous:
            return self.lib.ng2_controller_continuous_finish(
                self.h.engine, capture, start, prefix, self.h.now)
        # Before feature: a real known permit is consumed by old PAUSE tick.
        self.permit(capture, start, prefix)
        self.h.tick()
        return self.h.status().terminal

    def test116_normal_negative_restart_finishes_without_pause_or_budget_reset(self):
        old, restart, _floor, new_floor, _start = self.new_floor()
        before = self.h.status()
        count = len(self.h.events())
        spent = (before.inputs, before.moves, before.restarts)
        self.assertEqual(1, self.permit())
        self.finish_continuous()
        after = self.h.status()
        self.assertEqual((1, 0, count, 0),
                         (after.terminal, after.input_state, len(self.h.events()), after.paused),
                         'normal real RS/new floor must end with no added PAUSE or input')
        self.assertEqual(spent, (after.inputs, after.moves, after.restarts))
        proof = self.continuous()
        self.assertEqual((1, 1, 0, old.job_id, restart.id, new_floor),
                         (proof.enabled, proof.qualified, proof.successor_floor,
                          proof.old_job_id, proof.restart_command_id, proof.new_floor_capture_id))
        self.assertEqual(0, handoff(self.lib, self.h.engine).allowed,
                         'old paused handoff must never be fabricated')

    def test116_finish_requires_exact_source_permit_and_original_parent(self):
        for fault in ('no_permit', 'capture', 'start', 'prefix', 'parent', 'cancel'):
            with self.subTest(fault=fault):
                self.engine(); self.new_floor(); state = self.state()
                if fault != 'no_permit': self.assertEqual(1, self.permit())
                capture, start, prefix = None, None, None
                if fault == 'capture': capture = self.h.status().last_capture_id + 1
                if fault == 'start': start = self.h.status().last_capture_start_ns + 1
                if fault == 'prefix': prefix = self.h.prefix + 1
                if fault == 'parent': self.h.now = state.parent_deadline_ns + 1
                if fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                self.assertEqual(0, self.finish_continuous(capture, start, prefix))
                self.assertEqual(0, self.continuous().qualified)

    def test116_unprocessed_or_positive_new_floor_cannot_finish(self):
        for outcome in (None, 1, 2):
            with self.subTest(outcome=outcome):
                self.engine(); _old, _restart, floor, ident, start = self.new_floor(goods=2)
                if outcome is not None:
                    self.assertEqual(1, self.goods(floor, ident, start, start + 1))
                    self.probe(outcome)
                self.assertEqual(0, self.permit())
                self.assertEqual(0, self.finish_continuous())
                self.assertEqual(0, self.continuous().qualified)

    def test116_root_requires_pause_and_trusted_child_requires_fresh_floor(self):
        for successor, bad_state in ((False, 2), (True, 1), (True, 3), (True, 0)):
            with self.subTest(successor=successor, state=bad_state):
                self.engine(successor=successor)
                self.h.observe(self.h.scene(state=bad_state, gold=1))
                self.assertEqual(0, self.h.tick()[0])
                self.assertEqual([], self.h.events())
        self.engine(successor=True)
        self.h.observe(self.h.scene(state=2, gold=1))
        self.assertEqual(0, self.h.status().terminal)
        self.assertEqual(1, self.state().initial_pause_seen,
                         'trusted successor accepts a new FLOOR without issuing RESUME')
        self.assertEqual([], self.h.events())

    def test116_root_deadline_cannot_be_extended_or_issue_at_equality(self):
        self.engine(deadline=2_000_000_000)
        # The fixture's clock is 1 second; this short root bound is independent
        # of the old child session180 seconds and all later fitting work.
        self.first_pause()
        self.h.now = self.root_deadline
        ready, command = self.h.tick()
        self.assertEqual(0, ready)
        self.assertNotEqual(4, command.kind)
        self.assertEqual(15, self.h.status().reason)
        if self.has_continuous:
            self.assertEqual(0, self.lib.ng2_controller_enable_continuous(
                self.h.engine, 0, self.root_deadline + 1))

    def test116_successor_unknown_waits_within_original_transition_then_needs_own_floor(self):
        self.engine(successor=True)
        self.h.observe(self.h.scene(state=0))
        self.assertEqual((0, 0, []), (self.h.status().terminal, self.h.tick()[0], self.h.events()))
        self.assertEqual(0, self.state().initial_pause_seen)
        self.h.now += 100_000_000
        self.h.observe(self.h.scene(state=2, gold=1))
        self.assertEqual((0, 1, []),
                         (self.h.status().terminal, self.state().initial_pause_seen, self.h.events()))
        self.assertEqual(0, self.h.status().lead_confirmed)
        self.engine(successor=True)
        self.h.observe(self.h.scene(state=0))
        self.h.now = self.h.status().started_ns + 4_000_000_000
        self.h.tick()
        self.assertEqual((1, 17, []),
                         (self.h.status().terminal, self.h.status().reason, self.h.events()))


if __name__ == '__main__':
    unittest.main()
