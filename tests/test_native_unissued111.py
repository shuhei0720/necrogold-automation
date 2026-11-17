"""TEST111: two bounded recoveries of definitely unissued MOVE permissions.

Procedural terrain/signatures and public C calls test control semantics. The
independent future proof is synthetic, not a missing TEST110 phone response.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_side_opening098 as side
from tests import test_native_unsent_continuous as unsent

SECOND = fixture.SECOND


class NativeCompositeUnissued111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        side.NativeSideOpening098Tests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        side.NativeSideOpening098Tests.tearDownClass.__func__(cls)

    for _name in ('setUp', 'scene', 'observe', 'observe_actual', 'tick', 'status', 'events',
                  'motion_wait', 'ack', 'fit', 'next_move', 'publish_procedural_candidate',
                  'fresh_engine', 'recovery', 'recovery_samples', 'all_public_bytes',
                  'reject_old_callbacks_without_mutation', 'observed_result', 'credit',
                  'choice', 'motion', 'preparation_epoch', 'trigger', 'prove_and_issue'):
        locals()[_name] = getattr(side.NativeSideOpening098Tests, _name)

    def armed(self, turns=0, side_sign=-1):
        def rotate(x, y):
            x *= -side_sign
            for _ in range(turns):
                x, y = -y, x
            return x, y
        self.rotate = rotate
        # The single remote DIRT already belongs to the source permission.
        # The later STONE restricts that remote cell; it opens no traversal.
        cells = {(0,0): 'floor', (0,1): 'floor', (0,2): 'floor', (-1,-1): 'floor',
            (-2,-2): 'gold', (-1,0): 'dirt', (-2,-1): 'dirt', (0,-1): 'dirt',
            (1,-1): 'dirt', (1,0): 'dirt', (-2,0): 'dirt', (-2,1): 'dirt',
            (-1,1): 'dirt', (1,1): 'dirt', (-1,2): 'stone', (4,4): 'dirt'}
        source = fixture.textured({rotate(*p): kind for p, kind in cells.items()})
        direction = {value: key for key, value in fixture.DIRS.items()}[rotate(0,1)]
        initial = fixture.translated(source, direction)
        self.fit(initial); first = self.next_move(initial); self.ack(first)
        source = fixture.translated(initial, first.direction)
        self.observed_result(first, source)
        old = self.next_move(source)
        self.assertEqual((direction,8,1), (old.direction,self.choice(source)[1],self.choice(source)[4]))
        latest = deepcopy(source)
        self.opening = rotate(-1,0)
        latest.tiles[self.opening] = 'floor'
        rx, ry = rotate(4,4)
        sx, sy = fixture.DIRS[first.direction]
        ix, iy = fixture.DIRS[direction]
        self.remote = (rx-sx-ix, ry-sy-iy)
        self.assertEqual('dirt', source.tiles[self.remote])
        latest.tiles[self.remote] = 'stone'
        self.new_direction = {value: key for key, value in fixture.DIRS.items()}[self.opening]
        self.assertEqual((self.new_direction,8,1),
            (self.choice(latest)[0],self.choice(latest)[1],self.choice(latest)[4]))
        self.assertEqual((2,0,0), self.motion(source,latest,direction))
        return source, latest, old

    def test_composite_side_opening_retires_without_credit_then_requires_independent_fixed_goal(self):
        for turns in range(4):
            for side_sign in (-1,1):
                with self.subTest(turns=turns, side=side_sign):
                    self.fresh_engine()
                    _, latest, old, retired = self.trigger(turns,side_sign)
                    selected = self.choice(latest)
                    new = self.prove_and_issue(latest)
                    self.assertEqual(selected,self.choice(latest))
                    self.assertGreater(new.id,old.id)
                    self.assertGreater(new.target_ns,old.target_ns)
                    self.assertEqual(old.ordinal,new.ordinal)
                    self.assertEqual((1,1), (self.status().inputs,self.status().moves))
                    self.assertEqual(retired,bytes(self.events()[-2]))
                    self.reject_old_callbacks_without_mutation(old)

    def test_composite_admission_rejects_other_material_changes_and_protected_or_goods(self):
        for fault in ('remote_floor','remote_unknown','second_stone','near_stone',
                      'protected_remote','protected_opening','gold','partial'):
            with self.subTest(fault=fault):
                self.fresh_engine(); source, latest, old = self.armed()
                if fault == 'remote_floor': latest.tiles[self.remote]='floor'
                elif fault == 'remote_unknown': latest.tiles.pop(self.remote)
                elif fault == 'second_stone': latest.tiles[(-7,3)]='stone'
                elif fault == 'near_stone': latest.tiles[(1,0)]='stone'
                elif fault == 'protected_remote': latest.protected.add(self.remote)
                elif fault == 'protected_opening': latest.protected.add(self.opening)
                elif fault == 'gold': latest.tiles[(-7,3)]='gold'
                elif fault == 'partial': latest.goods='partial'
                credit = self.credit(); self.now=old.deadline_ns-30_000_000
                self.observe_actual(self.scene(2,2,latest,beat=True))
                self.assertEqual(0,self.recovery().post_move_reacquisitions)
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(credit,self.credit())
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))

    def test_composite_later_proof_preserves_all_tiles_of_the_fixed_new_anchor(self):
        _, latest, old, retired = self.trigger()
        latest.tiles[(-7,3)]='dirt'
        self.now+=20_000_000
        self.observe_actual(self.scene(2,2,latest,beat=True))
        self.assertEqual(17,self.status().reason)
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(self.saved_credit,self.credit())
        self.assertEqual(retired,bytes(next(e for e in self.events() if e.command.id==old.id)))

    test_composite_strict_zero_and_started_unknown_input = side.NativeSideOpening098Tests.test_trigger_requires_strict_zero_and_cannot_reuse_started_or_unknown_input
    test_composite_independent_current_prefix_proof = side.NativeSideOpening098Tests.test_later_proof_requires_independent_current_prefix_capture
    test_composite_original_ticket_and_parent_deadlines = side.NativeSideOpening098Tests.test_original_ticket_and_recovery_horizons_cannot_be_extended
    test_composite_new_ack_unknown_never_resends = side.NativeSideOpening098Tests.test_new_ack_unknown_remains_unresolved_without_resend


class NativeRemoteLate111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compile the actual public controller; compose mechanics without
        # inheriting the historical test collection.
        unsent.NativeUnsentContinuousTests.setUpClass()
        cls.lib = unsent.NativeUnsentContinuousTests.lib

    @classmethod
    def tearDownClass(cls):
        unsent.NativeUnsentContinuousTests.tearDownClass()

    def fixture(self):
        h = unsent.NativeUnsentContinuousTests(methodName='runTest')
        h.lib = self.lib
        h.setUp()
        self.addCleanup(h.doCleanups)
        return h

    def remote_armed(self):
        h = self.fixture()
        # Two proven UP moves expose the remote FLOOR at (2,2). The separated
        # GOLD cells keep this an observed-floor vantage rather than a gate.
        terrain = fixture.textured({
            **{(0,y): 'floor' for y in range(-5,1)},
            (-2,-5): 'gold', (2,-5): 'gold',
            (2,0): 'floor', (-4,-2): 'stone', (5,1): 'stone'})
        terrain, old = h.continuous_walk(moves=2, direction=3, terrain=terrain)
        self.assertEqual((2,2,1,1),
            (h.status().inputs,h.status().moves,h.status().lead_confirmed,h.status().input_state))
        self.assertEqual(3, old.direction)
        self.assertEqual('floor', terrain.tiles[(2,2)])
        changed = deepcopy(terrain)
        changed.tiles[(2,2)] = 'dirt'
        return h, terrain, changed, old

    def deliver_remote(self, h, changed, old):
        h.now = max(h.now+2, old.not_before_ns-20_000_000)
        self.assertLess(h.now, old.deadline_ns)
        self.assertEqual(1, h.observe_actual(h.scene(2,2,changed,beat=True)))
        self.assertEqual((1,old.id,0),
            (h.status().input_state,h.status().current_command_id,h.status().reason),
            'the ordinary in-window quiet path must retain the original unsent ID')

    def test_remote_palette_late_zero_retires_old_window_and_obtains_new_prepared_id(self):
        h, source, changed, old = self.remote_armed()
        self.deliver_remote(h,changed,old)
        pose = (h.status().x,h.status().y,h.status().last_completed_id)
        original = bytes(old)
        self.assertEqual(1,h.late_complete(old,old.deadline_ns+578_962))
        h.assert_retired(old)
        self.assertEqual(pose,(h.status().x,h.status().y,h.status().last_completed_id))
        self.assertEqual(original,bytes(next(e.command for e in h.events() if e.command.id==old.id)))
        recovery = h.recovery(); row = recovery.records[min(1,recovery.record_count-1)]
        self.assertEqual(h.verified_commit+12*fixture.SECOND,row.sync_deadline_ns)
        frozen = h.frozen()
        self.assertEqual(0,h.lib.ng2_controller_complete(h.engine,old.id,h.now+30*fixture.SECOND,0))
        self.assertEqual(frozen,h.frozen(),'an old callback cannot advance clock or refresh budget')
        new = h.next_recovery_ticket(changed)
        self.assertNotEqual(old.id,new.id)
        self.assertGreater(new.target_ns,old.target_ns)
        self.assertGreaterEqual(new.not_before_ns-h.now,50_000_000)
        self.assertLessEqual(new.deadline_ns,row.sync_deadline_ns)
        self.assertEqual((2,2),(h.status().inputs,h.status().moves))

    def test_remote_palette_requires_expired_unstarted_known_input(self):
        for variant in ('equal_deadline','started','ack','unknown','cancel','expired_budget'):
            with self.subTest(variant=variant):
                h, source, changed, old = self.remote_armed()
                self.deliver_remote(h,changed,old)
                if variant in ('started','ack','unknown'):
                    h.now=old.not_before_ns
                    self.assertEqual(1,h.lib.ng2_controller_begin(h.engine,old.id,h.now,1,0,1))
                    if variant!='started':
                        self.assertEqual(1,h.lib.ng2_controller_complete(
                            h.engine,old.id,h.now+1,1 if variant=='ack' else -1))
                elif variant=='cancel':
                    h.lib.ng2_controller_cancel(h.engine,h.now,2)
                at = old.deadline_ns if variant=='equal_deadline' else old.deadline_ns+578_962
                if variant=='expired_budget':at=h.verified_commit+12*fixture.SECOND
                h.late_complete(old,at)
                self.assertEqual(0,h.recovery().post_move_reacquisitions)
                self.assertEqual(2+(variant in ('ack','unknown')),h.status().inputs)
                if variant=='equal_deadline':self.assertEqual(6,h.status().reason)
                if variant=='unknown':self.assertEqual((11,1,4),(h.status().reason,h.status().terminal,h.status().input_state))
                if variant=='expired_budget':self.assertEqual(8,h.status().reason)

    def test_remote_palette_preserves_local_protection_gold_full_choice_and_strict_zero_vetoes(self):
        for variant in ('local','protection','gold','choice','motion_unknown','goods'):
            with self.subTest(variant=variant):
                h, source, changed, old = self.remote_armed()
                if variant=='local':changed.tiles[(0,-1)]='dirt'
                elif variant=='protection':changed.protected.add((2,2))
                elif variant=='gold':changed.tiles[(-2,-3)]='dirt'
                elif variant=='choice':changed.tiles[(0,-3)]='stone'
                elif variant=='motion_unknown':changed.signature=bytes([40])*23296
                else:changed.goods='visible'
                h.now=max(h.now+2,old.not_before_ns-20_000_000)
                self.assertEqual(1,h.observe_actual(h.scene(2,2,changed,beat=True)))
                h.late_complete(old,old.deadline_ns+578_962)
                self.assertEqual(0,h.recovery().post_move_reacquisitions)
                self.assertEqual((2,2),(h.status().inputs,h.status().moves))
                self.assertEqual(0,next(e for e in h.events() if e.command.id==old.id).begin_ns)


if __name__ == '__main__':
    unittest.main()
