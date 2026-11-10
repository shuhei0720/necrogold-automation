"""TEST065: a qualified unissued replan can miss its original publication beat.

TEST064 capture92 committed just before D and its C processing ended after D.
These procedural scenes/clocks test the pending-SAME/FRESH control boundary;
they do not invent the device's unrecorded model or future game images.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_unsent_continuous as unsent

CORE = unsent.CORE
SECOND = fixture.SECOND


class NativeDevice065Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = unsent.CORE
        try:
            unsent.CORE = CORE
            unsent.NativeUnsentContinuousTests.setUpClass.__func__(cls)
        finally:
            unsent.CORE = previous

    @classmethod
    def tearDownClass(cls):
        unsent.NativeUnsentContinuousTests.tearDownClass.__func__(cls)

    setUp = unsent.NativeUnsentContinuousTests.setUp
    scene = unsent.NativeUnsentContinuousTests.scene
    observe = unsent.NativeUnsentContinuousTests.observe
    observe_actual = unsent.NativeUnsentContinuousTests.observe_actual
    tick = unsent.NativeUnsentContinuousTests.tick
    status = unsent.NativeUnsentContinuousTests.status
    events = unsent.NativeUnsentContinuousTests.events
    motion_wait = unsent.NativeUnsentContinuousTests.motion_wait
    recovery = unsent.NativeUnsentContinuousTests.recovery
    ack = unsent.NativeUnsentContinuousTests.ack
    fit = unsent.NativeUnsentContinuousTests.fit
    next_move = unsent.NativeUnsentContinuousTests.next_move
    fresh_engine = unsent.NativeUnsentContinuousTests.fresh_engine
    observed_result = unsent.NativeUnsentContinuousTests.observed_result
    publish_procedural_candidate = unsent.NativeUnsentContinuousTests.publish_procedural_candidate
    continuous_walk = unsent.NativeUnsentContinuousTests.continuous_walk
    scene_details = unsent.NativeUnsentContinuousTests.scene_details
    armed = unsent.NativeUnsentContinuousTests.armed
    frozen = unsent.NativeUnsentContinuousTests.frozen
    next_recovery_ticket = unsent.NativeUnsentContinuousTests.next_recovery_ticket

    def pending(self, policy='same', terrain=None, command=None):
        if terrain is None:
            if policy == 'same_drift':
                terrain, changed, command = fixture.NativeControllerTests.continuous_vantage_drift(self)
                before = fixture.nav.choose(terrain, (-2, 0))
                self.assertEqual({'direction':'left', 'reason':'observed_floor_vantage',
                                  'target':(-4,0)}, before)
                self.assertEqual({**before, 'target':(-3,0)},
                                 fixture.nav.choose(changed, (-2,0)))
            else:
                terrain, command = self.armed()
                changed = deepcopy(terrain)
        else:
            changed = deepcopy(terrain)
        changed.tiles[(-10, 4)] = 'dirt' if changed.tiles.get((-10, 4)) == 'stone' else 'stone'
        if policy == 'fresh':
            changed.tiles[(0, -1)] = 'dirt'
        # Device92: end D-25.952ms, observe-start D-3.816ms; the next
        # actual tick sees the C work finish at D+3.152ms, then D+3.357ms.
        end = command.deadline_ns - 25_952_141
        commit = command.deadline_ns - 3_816_349
        self.now = end
        frame = self.scene(2, 2, changed, beat=True)
        self.assertEqual(1, self.observe_actual(frame, start=end-17_012_708, end=end, commit=commit))
        self.now = commit
        self.assertEqual((0, 0, 0), (self.status().reason, self.status().input_state,
                                    self.status().current_command_id))
        self.assertEqual(12 if policy == 'fresh' else 2, self.scene_details()[-1].validation)
        self.assertEqual((3, 17, 0), (self.events()[-1].outcome,
                                    self.events()[-1].reason, self.events()[-1].begin_ns))
        return changed, command

    def assert_pending_recovered(self, command, old_events, pose):
        s = self.status(); r = self.recovery()
        self.assertEqual((0, 0, 4, 0, 0), (s.reason, s.terminal, s.phase,
                                          s.input_state, s.current_command_id),
                         'known-not-sent pending revalidation must reacquire after its original D')
        self.assertEqual(pose, (s.x, s.y, s.inputs, s.moves, s.last_completed_id))
        self.assertEqual(old_events, tuple(bytes(e) for e in self.events()),
                         'already retired command keeps its original outcome/reason/time bytes')
        self.assertEqual(2, r.mode)
        latest = r.records[min(1, r.record_count-1)]
        self.assertEqual((5, 2, self.now, command.id),
                         (latest.reason, latest.clock, latest.at_ns, latest.command_id))
        self.assertEqual(self.verified_commit + 12*SECOND, latest.sync_deadline_ns)

    def test_pending_same_and_fresh_expiry_reacquire_without_rewriting_retired_ticket(self):
        for policy in ('same', 'fresh', 'same_drift'):
            with self.subTest(policy=policy):
                self.fresh_engine(); terrain, command = self.pending(policy)
                s = self.status(); pose = (s.x, s.y, s.inputs, s.moves, s.last_completed_id)
                old_events = tuple(bytes(e) for e in self.events())
                self.now = command.deadline_ns + 3_356_859
                ready, issued = self.tick()
                self.assertEqual((0, 0), (ready, issued.kind))
                self.assert_pending_recovered(command, old_events, pose)
                next_command = self.next_recovery_ticket(terrain)
                self.assertNotEqual(command.id, next_command.id)
                self.assertGreater(next_command.not_before_ns, command.deadline_ns)
                self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
                before = self.frozen()
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id,
                    self.now+30*SECOND, 1, 0, 1))
                for outcome in (-1, 0, 1):
                    self.assertEqual(0, self.lib.ng2_controller_complete(self.engine,
                        command.id, self.now+30*SECOND, outcome))
                self.assertEqual(before, self.frozen())

    def test_pending_original_deadline_equality_still_reissues_only_the_same_beat(self):
        for policy in ('same', 'fresh'):
            with self.subTest(policy=policy):
                self.fresh_engine(); _, command = self.pending(policy)
                self.now = command.deadline_ns
                ready, issued = self.tick()
                self.assertEqual((1, 4), (ready, issued.kind))
                self.assertEqual((command.target_ns, command.not_before_ns, command.deadline_ns,
                                  command.ordinal), (issued.target_ns, issued.not_before_ns,
                                  issued.deadline_ns, issued.ordinal))
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.assertEqual(1, self.lib.ng2_controller_begin(self.engine,
                    issued.id, self.now, 1, 0, 1))

    def test_repeated_pending_expiry_preserves_verified_progress_budget_and_episode(self):
        terrain, command = self.pending()
        self.now = command.deadline_ns + 1; self.tick()
        first = self.recovery()
        self.assertEqual((2, 1), (first.mode, first.post_move_reacquisitions))
        original_deadline = first.records[0].sync_deadline_ns
        new = self.next_recovery_ticket(terrain)
        terrain, new = self.pending(terrain=terrain, command=new)
        old_events = tuple(bytes(e) for e in self.events())
        s = self.status(); pose = (s.x, s.y, s.inputs, s.moves, s.last_completed_id)
        self.now = new.deadline_ns + 1; self.tick()
        self.assert_pending_recovered(new, old_events, pose)
        r = self.recovery()
        self.assertEqual((first.episode_id, 1), (r.episode_id, r.post_move_reacquisitions))
        self.assertEqual(original_deadline, r.records[min(1, r.record_count-1)].sync_deadline_ns)

    def test_pending_expiry_cannot_reopen_sync_walk_or_session_budget(self):
        for budget, reason in (('sync', 8), ('walk', 14), ('session', 15)):
            with self.subTest(budget=budget):
                self.fresh_engine(); _, command = self.pending()
                status = self.status()
                self.now = (self.verified_commit+12*SECOND if budget == 'sync' else
                    status.walk_started_ns+45*SECOND if budget == 'walk' else status.started_ns+180*SECOND)
                self.tick()
                self.assertEqual(reason, self.status().reason)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.assertEqual((2, 2), (self.status().inputs, self.status().moves))

    def test_pending_expiry_retains_authority_goods_and_latest_visual_guards(self):
        for fault in ('foreground', 'locked', 'owner', 'cancel', 'goods', 'partial',
                      'signature', 'origin', 'protected', 'gold_late_commit',
                      'protected_late_commit', 'route_late_commit'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.pending()
                flags = (1, 0, 1)
                if fault in ('foreground', 'locked', 'owner'):
                    flags = {'foreground': (0,0,1), 'locked': (1,1,1), 'owner': (1,0,0)}[fault]
                elif fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                else:
                    changed = deepcopy(terrain)
                    if fault in ('goods', 'partial'): changed.goods = 'visible' if fault == 'goods' else 'partial'
                    elif fault == 'signature': changed.signature = bytes([40])*23296
                    elif fault == 'origin': changed.tiles[(0,0)] = 'stone'
                    elif fault == 'gold_late_commit': changed.tiles[(8,3)] = 'gold'
                    elif fault == 'route_late_commit': changed.tiles[(0,-1)] = 'dirt'
                    else: changed.protected.add((-10,4))
                    self.now = command.deadline_ns-1 if fault.endswith('_late_commit') else self.now+2
                    self.observe_actual(self.scene(2, 2, changed, beat=True),
                        commit=command.deadline_ns+1 if fault.endswith('_late_commit') else self.now)
                self.now = command.deadline_ns + 1; self.tick(*flags)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
                if fault == 'goods': self.assertEqual(1, self.status().goods)
                if fault in ('foreground','locked','owner','cancel'):
                    self.assertEqual({'foreground':3,'locked':4,'owner':5,'cancel':2}[fault], self.status().reason)

    def test_pending_old_callbacks_and_backdated_clocks_cannot_trigger_recovery(self):
        terrain, command = self.pending()
        before = self.frozen()
        for outcome in (-1, 0, 1):
            self.assertEqual(0, self.lib.ng2_controller_complete(self.engine,
                command.id, command.deadline_ns+30*SECOND, outcome))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
            command.id, command.deadline_ns+30*SECOND, 1, 0, 1))
        self.assertEqual(before, self.frozen())
        self.now = command.deadline_ns-1
        frame = self.scene(2, 2, terrain, beat=True)
        self.observe_actual(frame, commit=command.deadline_ns+1)
        self.assertEqual(-1, self.tick()[0])
        self.assertEqual(0, self.recovery().post_move_reacquisitions)
        self.now = command.deadline_ns+1
        old_events = tuple(bytes(e) for e in self.events())
        s = self.status(); pose = (s.x, s.y, s.inputs, s.moves, s.last_completed_id)
        self.tick()
        self.assert_pending_recovered(command, old_events, pose)


if __name__ == '__main__':
    unittest.main()
