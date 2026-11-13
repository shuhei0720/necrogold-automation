"""TEST093: independently observed opened entry, latest bounded authority.

Procedural surfaces/clocks exercise the shipped C Controller. These are not
missing phone frames, future game responses, or real merchandise acceptance.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_observation072 as observation

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativeOpenedEntry093Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.POINTER(observation.Motion)]

    tearDownClass = classmethod(mechanics.NativeRecoveryTests.tearDownClass.__func__)
    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = fixture.NativeControllerTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch
    choice = observation.NativeObservation072Tests.choice
    motion = observation.NativeObservation072Tests.motion
    credit = observation.NativeObservation072Tests.credit

    def opened(self, direction=3, goods='partial', projection='full'):
        rotate = {1: lambda x,y:(y,-x), 2: lambda x,y:(-y,x),
                  3: lambda x,y:(x,y), 4: lambda x,y:(-x,-y)}[direction]
        tiles = {(0,0):'floor',(0,-1):'floor',(0,-2):'door',
            (-1,-2):'gold',(1,-2):'gold',(0,-3):'dirt' if goods=='unknown' else 'floor',
            (0,-4):'floor',(-4,2):'stone',(5,2):'stone',
            (8,2):'stone' if goods=='unknown' else 'dirt'}
        terrain = fixture.textured({rotate(x,y):kind for (x,y),kind in tiles.items()})
        self.fit(terrain)
        first = self.next_move(terrain); self.assertEqual(direction, first.direction)
        self.ack(first); terrain = fixture.translated(terrain, direction)
        self.observed_result(first, terrain)
        opening = self.next_move(terrain); self.ack(opening)
        terrain = deepcopy(terrain); terrain.tiles[fixture.DIRS[direction]]='floor'
        terrain.goods = goods
        if goods=='partial':
            self.assertEqual(3,direction)
            self.project_top(terrain, projection)
        self.observed_result(opening, terrain)
        self.assertEqual((1,1), (self.status().door_changes,self.status().moves))
        command = self.next_move(terrain)
        self.assertEqual((direction,5,*fixture.DIRS[direction],1),self.choice(terrain))
        return terrain,command

    def project_top(self, terrain, projection):
        for x in range(-4,3):
            terrain.protected.discard((x,-5)); terrain.tiles.pop((x,-5),None)
        for x in range(-3,2): terrain.protected.add((x,-5))
        if projection=='full':
            for x in range(-3,2): terrain.tiles[(x,-5)]='item'
            terrain.protected.update({(-4,-5),(2,-5)})
        else:
            for x,kind in zip(range(-3,2), (None,'floor','dirt',None,'floor')):
                if kind: terrain.tiles[(x,-5)]=kind

    def changed(self, terrain, scope='top', projection='reduced', direction=3):
        changed=deepcopy(terrain)
        if scope=='top': self.project_top(changed,projection)
        else:
            dx,dy=fixture.DIRS[direction]; changed.tiles[(2*dx,2*dy)]='floor'
        remote=next(p for p,k in changed.tiles.items() if k in ('dirt','stone') and max(map(abs,p))>=6)
        changed.tiles[remote]='stone' if changed.tiles[remote]=='dirt' else 'dirt'
        return changed

    def revalidate(self, terrain, changed, old, at=None):
        self.assertEqual(self.choice(terrain),self.choice(changed))
        self.assertEqual((2,0,0),self.motion(terrain,changed,old.direction))
        state=self.status(); epoch=self.preparation_epoch(old); frozen=bytes(old)
        self.now=max(self.now+2,old.not_before_ns-44_000_000) if at is None else at
        self.assertEqual(1,self.observe_actual(self.scene(2,2,changed,beat=True)))
        self.assertEqual((0,0,0), (self.status().reason,self.status().moves-state.moves,
            self.status().inputs-state.inputs), 'independent zero evidence cannot end or credit the entry')
        retired=next(e for e in self.events() if e.command.id==old.id)
        self.assertEqual((3,17,0,frozen),(retired.outcome,retired.reason,retired.begin_ns,bytes(retired.command)))
        new=self.next_move(changed)
        self.assertGreater(new.id,old.id)
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal),
            (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal))
        self.assertEqual(epoch,self.preparation_epoch(new))
        self.assertEqual(12,self.scene_details()[-1].validation)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
        return new,state

    scene_details = mechanics.NativeRecoveryTests.scene_details

    def test_projected_top_goods_growth_and_shrink_use_latest_separate_ticket(self):
        for start,end in (('full','reduced'),('reduced','full')):
            with self.subTest(start=start,end=end):
                self.fresh_engine(); terrain,old=self.opened(projection=start)
                changed=self.changed(terrain,projection=end)
                new,state=self.revalidate(terrain,changed,old)
                self.ack(new)
                self.observed_result(new,fixture.translated(changed,new.direction))
                self.assertEqual((state.inputs+1,state.moves+1,1,0),
                    (self.status().inputs,self.status().moves,self.status().door_changes,self.status().goods))

    def test_observed_inner_floor_after_opening_revalidates_in_four_directions(self):
        for direction in (1,2,3,4):
            with self.subTest(direction=direction):
                self.fresh_engine(); terrain,old=self.opened(direction,goods='unknown')
                changed=self.changed(terrain,'inner',direction=direction)
                new,state=self.revalidate(terrain,changed,old)
                self.ack(new); self.observed_result(new,fixture.translated(changed,direction))
                self.assertEqual((state.inputs+1,state.moves+1,0),
                    (self.status().inputs,self.status().moves,self.status().goods))

    def test_projection_surface_gold_and_motion_counterexamples_reject_revalidation(self):
        for fault in ('outside_projection','near_protection','near_material','next_wall','bracket',
                      'lost_remote_gold','new_item','unknown_motion','nonzero_motion','goods_transition'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain,old=self.opened()
                changed=self.changed(terrain)
                if fault=='outside_projection':changed.protected.add((3,-5))
                elif fault=='near_protection':changed.protected.add((1,-1))
                elif fault=='near_material':changed.tiles[(1,0)]='dirt'
                elif fault=='next_wall':changed.tiles[(0,-1)]='dirt'
                elif fault=='bracket':changed.tiles[(-1,-1)]='floor'
                elif fault=='lost_remote_gold':changed.tiles[(1,-1)]='floor'
                elif fault=='new_item':changed.tiles[(8,1)]='item';changed.protected.add((8,1))
                elif fault=='unknown_motion':changed.signature=bytes([40])*23296
                elif fault=='nonzero_motion':changed.signature=fixture.translated(changed,3).signature
                elif fault=='goods_transition':changed.goods='unknown'
                before=self.credit();self.now+=2
                self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertNotEqual(12,self.scene_details()[-1].validation if self.scene_details() else 0)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
                self.assertEqual(before,self.credit())

    def test_original_ticket_windows_epochs_and_actual_begin_boundaries_are_frozen(self):
        for scope in ('top','inner'):
            for arrival in (44_000_000,719_539):
                for delta in (-1,0,1):
                    with self.subTest(scope=scope,arrival=arrival,deadline_delta=delta):
                        self.fresh_engine()
                        direction=3 if scope=='top' else 1
                        terrain,old=self.opened(direction,goods='partial' if scope=='top' else 'unknown')
                        changed=self.changed(terrain,scope,direction=direction)
                        new,state=self.revalidate(terrain,changed,old,at=old.not_before_ns-arrival)
                        self.now=new.deadline_ns+delta
                        accepted=self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1)
                        self.assertEqual(int(delta<=0),accepted)
                        self.assertEqual((state.inputs,state.moves),(self.status().inputs,self.status().moves))
                        if delta>0:
                            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                            self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,new.id,self.now,1))

    def test_expired_partial_entry_reacquires_independent_future_permission(self):
        for via in ('tick','begin','complete_zero'):
            with self.subTest(via=via):
                self.fresh_engine();terrain,old=self.opened();changed=self.changed(terrain)
                new,state=self.revalidate(terrain,changed,old)
                self.now=new.deadline_ns+1
                if via=='tick':self.tick()
                elif via=='begin':self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                else:self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,new.id,self.now,0))
                self.assertEqual((0,0,0),(self.status().reason,self.status().input_state,self.preparation_epoch(new)),
                    'an expired definitely-unsent partial entry must withdraw into bounded reacquisition')
                self.assertEqual((state.inputs,state.moves),(self.status().inputs,self.status().moves))
                self.assertEqual(1,self.recovery().post_move_reacquisitions)
                self.assertNotEqual(4,self.tick()[1].kind,'no new input before independent current proof')
                self.now+=1_000_000;self.observe_actual(self.scene(2,2,changed,beat=True))
                following=self.next_move(changed)
                self.assertGreater(following.target_ns,new.target_ns)
                self.assertGreaterEqual(following.not_before_ns-self.now,50_000_000)
                self.assertEqual(new.ordinal,following.ordinal)
                self.assertEqual((state.inputs,state.moves),(self.status().inputs,self.status().moves))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        for fault in ('changed_latest','crossing_capture','parent'):
            with self.subTest(recovery_fault=fault):
                self.fresh_engine();terrain,old=self.opened();parent=self.motion_wait().deadline_ns
                changed=self.changed(terrain);new,state=self.revalidate(terrain,changed,old)
                self.now=new.deadline_ns+1;retirement=self.now;self.tick()
                self.assertEqual(parent,self.recovery().records[0].sync_deadline_ns)
                self.now+=1_000_000
                if fault=='parent':self.now=parent;self.tick()
                else:
                    latest=deepcopy(changed)
                    if fault=='changed_latest':latest.tiles[(8,1)]='dirt'
                    self.observe_actual(self.scene(2,2,latest,beat=True),
                        start=retirement-1 if fault=='crossing_capture' else self.now-2)
                    self.assertNotEqual(4,self.tick()[1].kind)
                    if fault=='crossing_capture':
                        self.assertEqual(0,self.status().reason)
                        self.now+=2;self.observe_actual(self.scene(2,2,changed,beat=True))
                        self.assertEqual(4,self.next_move(changed).kind)
                self.assertEqual((state.inputs,state.moves),(self.status().inputs,self.status().moves))
                if fault=='parent':self.assertNotEqual(0,self.status().reason)

    def test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative(self):
        for fault in ('goods','cancel','locked','foreground','owner','unknown_ack','prefix','unstable',
                      'chain','walk','session'):
            with self.subTest(fault=fault):
                self.fresh_engine();terrain,old=self.opened();changed=self.changed(terrain)
                state=self.status()
                if fault in ('chain',):
                    new,_=self.revalidate(terrain,changed,old)
                    self.now+=2;self.observe_actual(self.scene(2,2,terrain,beat=True))
                    newer=self.next_move(terrain)
                    self.now+=2;self.observe_actual(self.scene(2,2,changed,beat=True))
                    self.assertEqual(5,self.scene_details()[-1].validation)
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,newer.id,self.now,1,0,1));continue
                if fault=='goods':changed.goods='visible'
                elif fault=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                elif fault in ('locked','foreground','owner'):
                    self.tick(front=int(fault!='foreground'),locked=int(fault=='locked'),owner=int(fault!='owner'))
                elif fault=='unknown_ack':
                    self.now=old.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                    self.now+=1;self.lib.ng2_controller_complete(self.engine,old.id,self.now,-1)
                elif fault in ('walk','session'):
                    self.now=(state.walk_started_ns+45*SECOND if fault=='walk' else state.started_ns+180*SECOND)
                    self.tick()
                self.now+=2
                self.observe_actual(self.scene(2,2,changed,beat=True),prefix=self.prefix+int(fault=='prefix'),stable=int(fault!='unstable'))
                self.assertFalse(any(d.validation==12 for d in self.scene_details()))
                if fault not in ('prefix','unstable'):
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                self.assertEqual(state.moves,self.status().moves)
                self.assertEqual(state.inputs+int(fault=='unknown_ack'),self.status().inputs)
                if fault=='goods':self.assertEqual(1,self.status().goods)
        # Old quiet PARTIAL authority cannot acquire the new recovery scope.
        self.fresh_engine();terrain,old=self.opened()
        quiet=deepcopy(terrain);self.project_top(quiet,'reduced')
        self.now+=2;self.observe_actual(self.scene(2,2,quiet,beat=True))
        self.assertEqual(old.id,self.status().current_command_id)
        self.now=old.deadline_ns+1
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
        self.assertEqual(0,self.recovery().post_move_reacquisitions)
        self.assertNotEqual(0,self.status().reason)
        # Same-source repeats and repeated recoveries do not renew the parent.
        self.fresh_engine();terrain,old=self.opened();parent=self.motion_wait().deadline_ns
        changed=self.changed(terrain);new,state=self.revalidate(terrain,changed,old)
        events=tuple(bytes(e) for e in self.events());self.now+=2
        self.observe_actual(self.scene(2,2,changed,beat=True))
        self.assertEqual((new.id,parent,events),(self.status().current_command_id,
            self.motion_wait().deadline_ns,tuple(bytes(e) for e in self.events())))
        for _ in range(2):
            self.now=new.deadline_ns+1;self.tick()
            self.assertEqual(0,self.status().reason)
            self.now+=1_000_000;self.observe_actual(self.scene(2,2,changed,beat=True))
            new=self.next_move(changed)
            self.assertEqual(parent,self.motion_wait().deadline_ns)
            self.assertTrue(all(row.sync_deadline_ns==parent for row in self.recovery().records
                if row.sequence))
        self.now=parent;self.tick()
        self.assertNotEqual(0,self.status().reason)
        self.assertEqual((state.inputs,state.moves),(self.status().inputs,self.status().moves))
        # A real entry ends this parent; later shop moves receive their own
        # normal horizons. Finish/terminal/new-level resets are also explicit
        # in C and reviewed; this test does not synthesize a real restart.
        self.fresh_engine();terrain,old=self.opened();parent=self.motion_wait().deadline_ns
        changed=self.changed(terrain);new,_=self.revalidate(terrain,changed,old)
        self.ack(new);after=fixture.translated(changed,3);self.observed_result(new,after)
        self.next_move(after)
        self.assertGreater(self.motion_wait().deadline_ns,parent)


if __name__=='__main__':unittest.main()
