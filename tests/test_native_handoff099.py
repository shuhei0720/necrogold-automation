"""TEST099 only explicit normal cutoffs can hand a completed run to a client.

All classifications and UI callbacks are procedural trust-boundary fixtures;
no old LIMIT/NEGATIVE field is independently a next-run certificate.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests.test_native_stop099 import stop_detail


class Handoff(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32)] + [
        (name, C.c_int32) for name in ('kind', 'allowed', 'reason', 'reserved')] + [
        (name, C.c_uint64) for name in ('qualified_ns', 'source_capture_id', 'source_prefix',
                                     'pause_capture_id', 'completed_prefix')]


def handoff(lib, engine):
    value = Handoff()
    query = getattr(lib, 'ng2_controller_handoff', None)
    if query is not None:
        query.argtypes = [C.c_void_p, C.POINTER(Handoff)]
        query(engine, C.byref(value))
    return value


class NativeHandoff099Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp(); self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def proof(self):
        return handoff(self.lib, self.h.engine)

    def four_negative_shops(self, before_last_tick=None):
        for number in range(1, 5):
            self.q.goods(); self.q.assess(3, 2); self.q.pause_observed()
            self.assertEqual(1, self.q.durable())
            source = self.q.cycle()
            if number == 4:
                if before_last_tick: before_last_tick()
                self.assertEqual(0, self.h.tick()[0])
                return source
            ready, restart = self.h.tick(); self.assertEqual((1, 3), (ready, restart.kind))
            self.assertEqual(1, self.q.intent(restart)); self.q.next_floor(restart)
            current = self.q.cycle()
            self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
                current.job_id, current.next_floor_capture_id, self.h.prefix, self.h.now))
            self.h.now += 20_000_000

    def clear_restart_limit(self, count=12, initial_fingerprint=0):
        h = self.h; fingerprint = initial_fingerprint; initial_count = h.status().restarts
        h.now += 2
        h.observe(h.scene(2, 1))
        for number in range(count):
            ready, pause = h.tick(); self.assertEqual((1, 2), (ready, pause.kind))
            h.ack(pause); h.now += 200_000_000; h.observe(h.scene())
            ready, restart = h.tick(); self.assertEqual((1, 3), (ready, restart.kind)); h.ack(restart)
            h.now += 200_000_002; clear = h.scene(2, 1); fingerprint = 0 if fingerprint == 12 else 12
            for k in (0, 1, 2, 8, 9, 10): clear.fingerprint[k] = fingerprint
            h.observe(clear); self.assertEqual(initial_count + number + 1, h.status().restarts)
            h.now += 200_000_002; h.observe(clear)
        self.assertEqual(0, h.tick()[0]); self.assertEqual(14, h.status().reason)
        return clear

    def cleanup(self, floor=None, outcome=1):
        h = self.h
        if floor is not None:
            h.now += 10_000_000; h.observe(floor)
        ready, pause = h.tick(); self.assertEqual((1, 2), (ready, pause.kind))
        if outcome == 1: h.ack(pause)
        else:
            h.now = max(h.now, pause.not_before_ns)
            self.assertEqual(1, self.lib.ng2_controller_begin(h.engine, pause.id, h.now, 1, 0, 1))
            h.now += 50_000_000
            self.lib.ng2_controller_complete(h.engine, pause.id, h.now, outcome)
            return pause
        h.now += 210_000_000; h.observe(h.scene(state=1))
        return pause

    def test_only_fourth_durable_negative_limit_mints_classified_source_handoff(self):
        source = self.four_negative_shops(before_last_tick=lambda:
            self.assertEqual((0, 0), (self.proof().kind, self.proof().allowed),
                             'four complete old fields cannot mint proof before the explicit normal cutoff'))
        value = self.proof()
        self.assertEqual((1, 1, 14, source.capture_id, source.prefix, source.pause_capture_id, self.h.prefix),
            (value.kind, value.allowed, value.reason, value.source_capture_id, value.source_prefix,
             value.pause_capture_id, value.completed_prefix),
            'only the normal negative cutoff with actual durable PAUSE may permit a new UUID')
        self.assertEqual((1, 0), (self.h.status().terminal, self.h.status().input_state))
        self.assertGreaterEqual(value.qualified_ns, source.durable_ns)
        frozen = bytes(value); self.h.now += 100; self.h.tick()
        self.assertEqual(frozen, bytes(self.proof()))

    def test_clear_search_twelve_needs_actual_cleanup_pause_before_allowed(self):
        clear = self.clear_restart_limit()
        self.assertEqual((2, 0), (self.proof().kind, self.proof().allowed))
        original_stop = bytes(stop_detail(self.lib, self.h.engine))
        self.cleanup()
        out = self.proof()
        pause = self.h.events()[-1]
        self.assertEqual((2, 1, 14, pause.command.source_capture_id, pause.observed_capture_id, pause.command.id),
            (out.kind, out.allowed, out.reason, out.source_capture_id, out.pause_capture_id, out.completed_prefix))
        self.assertEqual(pause.command.id - 1, out.source_prefix)
        self.assertEqual(original_stop, bytes(stop_detail(self.lib, self.h.engine)))
        self.assertEqual((0, 0, 12), (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))

    def test_clear_cutoff_requalifies_and_freezes_a_new_clear_pause_source(self):
        clear = self.clear_restart_limit()
        old_source = self.h.number
        self.h.now += 10_000_000; self.h.observe(native.Scene.from_buffer_copy(bytes(clear)))
        current = self.h.number
        self.cleanup()
        out = self.proof()
        self.assertEqual((2, 1, current), (out.kind, out.allowed, out.source_capture_id))
        self.assertGreater(current, old_source)
        self.assertEqual(self.h.events()[-1].command.source_capture_id, out.source_capture_id)

    def test_changed_uncertain_gold_goods_candidate_or_protection_never_requalifies_clear_handoff(self):
        for fault in ('gold', 'goods', 'passage', 'protection', 'origin'):
            for phase in ('immediate', 'bad_then_clear', 'after_publication'):
                with self.subTest(fault=fault, phase=phase):
                    self.setUp(); clear = self.clear_restart_limit()
                    terrain = native.textured({(0, 0): 'floor'}); gold = 1
                    if fault == 'gold': terrain.tiles[(-3, -2)] = 'gold'; terrain.gold.add((-3, -2)); gold = 2
                    elif fault == 'goods': terrain.goods = 'partial'
                    elif fault == 'passage':
                        from tests.test_native_passage072 import passage_room
                        terrain = passage_room()
                    elif fault == 'protection': terrain.protected.add((3, 2))
                    else: terrain.tiles[(0, 0)] = 'dirt'
                    pause = None
                    if phase == 'after_publication':
                        ready, pause = self.h.tick(); self.assertEqual((1, 2), (ready, pause.kind))
                    self.h.now += 10_000_000; self.h.observe(self.h.scene(2, gold, terrain))
                    if phase != 'immediate':
                        self.h.now += 10_000_000
                        self.h.observe(native.Scene.from_buffer_copy(bytes(clear)))
                    if pause:
                        frozen = bytes(pause); self.h.ack(pause)
                        self.h.now += 210_000_000; self.h.observe(self.h.scene(state=1))
                        self.assertEqual(frozen, bytes(self.h.events()[-1].command))
                    else: self.cleanup()
                    self.assertEqual(0, self.proof().allowed,
                                     'contradictory cleanup evidence must permanently revoke B even after later CLEAR')

    def test_residual_negative_does_not_turn_generic_walk_or_session_limit_into_handoff(self):
        for fault in ('walk', 'session', 'cancel', 'storage'):
            with self.subTest(fault=fault):
                self.setUp(); self.q.negative_restart()
                self.assertEqual(3, self.q.cycle().outcome)
                if fault == 'walk': self.h.now = self.h.status().walk_started_ns + 45 * native.SECOND; self.h.tick()
                elif fault == 'session': self.h.now = self.h.status().started_ns + 180 * native.SECOND; self.h.tick()
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                else: self.lib.ng2_controller_cycle_storage_failed(self.h.engine, self.q.cycle().job_id, self.h.now)
                self.assertEqual((0, 0), (self.proof().kind, self.proof().allowed))

    def test_earlier_durable_negative_history_needs_a_new_clear_level_and_explicit_search_cutoff(self):
        self.earlier_negative_clear_limit()
        self.cleanup()
        self.assertEqual((2, 1), (self.proof().kind, self.proof().allowed),
                         'earlier negative is compatible history, while this explicit new clear-level cutoff grants proof')
        self.setUp(); clear = self.earlier_negative_clear_limit()
        self.h.now = self.h.status().walk_started_ns + 45 * native.SECOND
        self.h.observe(native.Scene.from_buffer_copy(bytes(clear)))
        self.cleanup()
        self.assertEqual(0, self.proof().allowed,
                         'cleanup at the old walk boundary cannot renew a previously minted handoff')

    def earlier_negative_clear_limit(self):
        restart = self.q.negative_restart(); self.assertEqual(1, self.q.intent(restart))
        self.h.ack(restart); self.h.now += 210_000_000
        clear = self.h.scene(2, 1); clear.fingerprint[:] = bytes([80]) * 48
        self.assertEqual(1, self.h.observe(clear))
        current = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            current.job_id, current.next_floor_capture_id, self.h.prefix, self.h.now))
        self.h.now += 200_000_002; self.h.observe(native.Scene.from_buffer_copy(bytes(clear)))
        clear = self.clear_restart_limit(count=11, initial_fingerprint=80)
        self.assertEqual((1, 3, 12), (self.q.cycle().job_id, self.q.cycle().outcome, self.h.status().restarts))
        return clear

    def test_target_candidate_unknown_and_unknown_pause_cannot_handoff(self):
        for outcome in (0, 1, 2):
            with self.subTest(outcome=outcome):
                self.setUp(); self.q.goods(partial=outcome != 0); self.q.assess(outcome)
                self.q.pause_observed(); self.q.durable(); self.h.tick()
                self.assertEqual((0, 0), (self.proof().kind, self.proof().allowed))
        self.setUp(); self.clear_restart_limit(); self.cleanup(outcome=-1)
        self.assertEqual((1, 4, 0), (self.h.status().terminal, self.h.status().input_state, self.proof().allowed))

    def test_read_only_handoff_companion_has_separate_abi_and_inert_missing_controller(self):
        before = bytes(self.h.status()), bytes(self.q.cycle()), tuple(bytes(e) for e in self.h.events())
        value = self.proof(); self.assertEqual((1, 64, 0, 0),
            (value.abi_version, value.struct_size, value.kind, value.allowed))
        self.assertEqual(bytes(value), bytes(self.proof()))
        self.assertEqual(before, (bytes(self.h.status()), bytes(self.q.cycle()), tuple(bytes(e) for e in self.h.events())))
        self.assertEqual(bytes(Handoff()), bytes(handoff(self.lib, None)))


if __name__ == '__main__':
    unittest.main()
