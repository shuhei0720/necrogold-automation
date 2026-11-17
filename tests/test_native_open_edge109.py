"""TEST109 direct-opening observation with a clipped outer partial domain.

Original56b522 is UNKNOWN, not a negative. Its cx195 partial name-search
margin starts at135 while its observed icon core starts at177. A LEFT input
would move the already-visible potential pixels right, without losing them.
Public C fixtures below use procedural texture/clocks and later responses;
no unsaved post-adoption phone frame or real entry is claimed.
"""
import ctypes as C
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_open_full108 as opened
from tests import test_native_full_framing101 as legacy


class NativeOpenEdge109Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            frozen = os.environ.get('NECRO_TEST109_CONTROLLER_CORE')
            if frozen:
                native.CORE = Path(frozen)
            opened.NativeOpenFull108Tests.setUpClass.__func__(cls)
        finally:
            native.CORE = previous

    tearDownClass = classmethod(opened.NativeOpenFull108Tests.tearDownClass.__func__)
    setUp = opened.NativeOpenFull108Tests.setUp
    rotate = staticmethod(opened.NativeOpenFull108Tests.rotate)
    pending = opened.NativeOpenFull108Tests.pending
    admitted = opened.NativeOpenFull108Tests.admitted
    ticket = opened.NativeOpenFull108Tests.ticket
    moved = opened.NativeOpenFull108Tests.moved

    @staticmethod
    def result(value, direction=1):
        opened.NativeOpenFull108Tests.result(value, direction)
        value.partial[0].cx = 195 if direction == 1 else 611

    def test_direct_opening_keeps_visible_outer_domain_and_enters_on_new_proof(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                source, opening, state, moves, command = self.ticket(direction=direction)
                self.assertGreater(command.target_ns, self.h.now+50_000_000)
                self.h.ack(command)
                self.assertEqual(moves, self.h.status().moves, 'opening/entry ACK is not displacement')
                latest = native.translated(source, direction)
                self.h.observed_result(command, latest)
                event = next(e for e in self.h.events() if e.command.id == command.id)
                self.assertEqual((2, 1, *native.DIRS[direction]),
                    (event.outcome, event.motion, event.dx, event.dy))
                self.assertEqual((moves+1, state.job_id+1, 1),
                    (self.h.status().moves, self.q.cycle().job_id, self.q.cycle().pending))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opening.id,
                    self.h.now, 1, 0, 1))

    def test_icon_core_and_every_visible_search_pixel_must_remain_central(self):
        cases = ((1, 150, None), (2, 650, None), (1, 620, None), (2, 180, None),
                 (1, 195, 70), (1, 195, 201))
        for direction, cx, sy in cases:
            with self.subTest(direction=direction, cx=cx, sy=sy):
                def bad(value):
                    value.partial[0].cx = cx
                    if sy is not None:
                        value.partial[0].sy = sy
                self.pending(direction=direction, mutate=bad)
                self.assertEqual(7, self.q.cycle().state)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_target_upper_bound_or_name_priority_does_not_gain_edge_permission(self):
        cases = ('target', 'candidate', 'icon', 'name', 'safe_partial', 'row_edge')
        for fault in cases:
            with self.subTest(fault=fault):
                def positive(value):
                    if fault in ('target', 'candidate'):
                        value.outcome = 1 if fault == 'target' else 2
                    elif fault == 'icon': value.partial[0].icon_upper_bound = .80
                    elif fault == 'name':
                        value.partial[0].word_present = 1
                        value.partial[0].word_iou, value.partial[0].word_coverage = .82, .90
                    elif fault == 'safe_partial': value.partial_safe_no_positive = 1
                    else: value.rows[0].left = 240
                self.pending(mutate=positive)
                self.assertEqual(7, self.q.cycle().state)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_old_unknown_entry_history_does_not_inherit_direct_opening_edge_domain(self):
        old = legacy.NativeFullFraming101Tests(methodName='runTest')
        old.lib = self.lib
        old.setUp()
        self.addCleanup(old.doCleanups)
        def result(value):
            legacy.NativeFullFraming101Tests.result(value)
            value.partial[0].cx = 195
        old.result = result
        _, command, state, moves = old.pending()
        event = old.h.events()[-1]
        self.assertEqual((command.id, 2, 0), (event.command.id, event.outcome, event.motion))
        self.assertEqual((7, 1), (state.state, state.completed_shops))
        self.assertEqual(moves, old.h.status().moves)

    def test_edge_entry_target_is_held_and_second_unknown_never_repeats_move(self):
        for target in (True, False):
            with self.subTest(target=target):
                _, _, state, moves, _ = self.moved()
                self.q.assess(1 if target else 0, 1, None if target else self.result)
                current = self.q.cycle()
                self.assertEqual((7, 1, int(target)),
                    (current.state, current.completed_shops, current.candidate_latched))
                self.assertEqual(moves+1, self.h.status().moves)
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertNotEqual(3, self.h.tick()[1].kind)
                self.assertGreater(current.job_id, state.job_id)

    def test_edge_requires_fresh_current_prefix_and_original_deadline(self):
        for fault in ('prefix', 'unstable', 'deadline', 'cancel', 'replay'):
            with self.subTest(fault=fault):
                source, opening, state, moves = self.admitted()
                self.h.now = state.continuation_deadline_ns+1 if fault == 'deadline' else self.h.now+10_000_000
                if fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                options = {'prefix': self.h.prefix+1} if fault == 'prefix' else {}
                if fault == 'unstable': options['stable'] = 0
                frame = self.h.scene(2, 2, source, beat=True)
                if fault == 'replay':
                    self.assertEqual(0, self.lib.ng2_controller_observe_at(self.h.engine, C.byref(frame),
                        self.h.number, self.h.now-2, self.h.now, self.h.prefix, 1, self.h.now))
                else:
                    self.h.observe_actual(frame, **options)
                self.assertEqual(moves, self.h.status().moves)
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opening.id,
                    self.h.now, 1, 0, 1))

    def test_edge_never_resends_an_unknown_sent_input(self):
        source, _, _, moves, command = self.ticket()
        self.h.now = command.not_before_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now+1, -1))
        self.h.now += 10_000_000
        self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
        self.assertEqual((4, moves), (self.h.status().input_state, self.h.status().moves))
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
