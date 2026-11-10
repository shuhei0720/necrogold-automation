"""TEST071: enter a verified opened gate while two goods remain PARTIAL.

The recorded c94 pair changes only FLOOR/DIRT diagonally behind one unchanged
GOLD bracket. Procedural public-C sequences verify this bounded permission;
no missing third product or future device frame is invented.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics

CORE = mechanics.CORE


class NativeShop071Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous

    tearDownClass = classmethod(mechanics.NativeRecoveryTests.tearDownClass.__func__)
    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate

    def opened_entry(self, direction=3, side=1, initial='dirt', opened_ack=True,
                     wrong_opening_direction=False, protected_shield=False):
        opening_direction = 2 if wrong_opening_direction else direction
        rotate = {1: lambda x,y:(y,-x), 2: lambda x,y:(-y,x),
                  3: lambda x,y:(x,y), 4: lambda x,y:(-x,-y)}[opening_direction]
        tiles = {(0,0):'floor',(0,-1):'floor',(0,-2):'door' if opened_ack else 'floor',
            (-1,-2):'gold',(1,-2):'gold',(0,-3):'floor',(-1,-3):'floor',(1,-3):'floor'}
        terrain = fixture.textured({rotate(x,y):kind for (x,y),kind in tiles.items()})
        self.fit(terrain); first = self.next_move(terrain)
        self.assertEqual(opening_direction,first.direction)
        self.ack(first); terrain = fixture.translated(terrain,opening_direction)
        if not opened_ack: terrain.goods = 'partial'
        self.observed_result(first,terrain)
        if opened_ack:
            opening = self.next_move(terrain); self.ack(opening)
            terrain = deepcopy(terrain); terrain.tiles[fixture.DIRS[opening_direction]] = 'floor'
            terrain.goods = 'partial'
        if wrong_opening_direction:
            # A second observed, already open UP gate does not inherit the
            # RIGHT gate's acknowledged opening permission.
            terrain.tiles.update({(0,-1):'floor',(-1,-1):'gold',(1,-1):'gold'})
        self.shield = (side,-2) if wrong_opening_direction else rotate(side,-2)
        terrain.tiles[self.shield] = initial
        if protected_shield: terrain.protected.add(self.shield)
        terrain.tiles[(8,3)] = 'stone'
        if opened_ack:
            self.observed_result(opening,terrain)
        else:
            self.now += 2; self.observe_actual(self.scene(2,2,terrain,beat=True))
        command = self.next_move(terrain)
        self.assertEqual((4,direction,0), (command.kind,command.direction,self.status().goods))
        return terrain,command

    def flicker(self, terrain):
        changed = deepcopy(terrain)
        changed.tiles[self.shield] = 'floor' if terrain.tiles[self.shield] == 'dirt' else 'dirt'
        return changed

    def test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker(self):
        for direction in (1,2,3,4):
            for side in (-1,1):
                for initial in ('floor','dirt'):
                    with self.subTest(direction=direction,side=side,initial=initial):
                        self.fresh_engine(); terrain,command = self.opened_entry(direction,side,initial)
                        saved = (bytes(command),tuple(bytes(e) for e in self.events()),
                            bytes(self.motion_wait()),bytes(self.recovery()))
                        changed = self.flicker(terrain); self.now += 2
                        self.observe_actual(self.scene(2,2,changed,beat=True))
                        self.assertEqual((0,0,1,command.id,2,1,1,0), (self.status().reason,
                            self.status().terminal,self.status().input_state,self.status().current_command_id,
                            self.status().inputs,self.status().moves,self.status().door_changes,self.status().goods),
                            'two PARTIAL goods must keep the same observed opened-floor entry available')
                        self.assertEqual(saved,(bytes(self.events()[-1].command),
                            tuple(bytes(e) for e in self.events()),bytes(self.motion_wait()),bytes(self.recovery())))
                        self.ack(command)
                        self.observed_result(command,fixture.translated(changed,direction))
                        self.assertEqual((0,3,2,1,0),(self.status().reason,self.status().inputs,
                            self.status().moves,self.status().door_changes,self.status().goods),
                            'real entry is one movement; PARTIAL merchandise is not completion')

    def test_exception_does_not_allow_other_local_cells_materials_or_missing_open_ack(self):
        for fault in ('not_opened','wrong_direction','unknown_goods','goods_change','protected',
                      'protected_existing','stone','unknown',
                      'bracket','forward_path','other_near','target','signature'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain,command = self.opened_entry(opened_ack=fault!='not_opened',
                    wrong_opening_direction=fault=='wrong_direction',protected_shield=fault=='protected_existing')
                changed = self.flicker(terrain)
                if fault == 'unknown_goods':
                    # A goods-state change cannot qualify as the PARTIAL pair.
                    changed.goods = 'unknown'
                elif fault == 'goods_change': changed.goods = 'visible'
                elif fault == 'protected': changed.protected.add(self.shield)
                elif fault == 'stone': changed.tiles[self.shield] = 'stone'
                elif fault == 'unknown': del changed.tiles[self.shield]
                elif fault == 'bracket': changed.tiles[(self.shield[0],-1)] = 'floor'
                elif fault == 'forward_path': changed.tiles[(0,-2)] = 'dirt'
                elif fault == 'other_near': changed.tiles[(1,0)] = 'dirt'
                elif fault == 'target': changed.tiles[(0,-1)] = 'dirt'
                elif fault == 'signature': changed.signature = bytes([40])*23296
                self.now += 2; self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertEqual(1 if fault == 'goods_change' else 17,self.status().reason)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
                self.assertEqual(1,self.status().moves)

    def test_original_actual_deadline_and_matching_stable_prefix_remain_required(self):
        for fault in ('deadline_equal','deadline_late','unstable','prefix'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain,command = self.opened_entry()
                changed = self.flicker(terrain); kwargs = {}
                if fault.startswith('deadline'):
                    self.now = command.deadline_ns-1
                    kwargs['commit'] = command.deadline_ns+int(fault=='deadline_late')
                else:
                    self.now += 2
                    kwargs['stable'] = int(fault!='unstable')
                    kwargs['prefix'] = self.prefix+1 if fault=='prefix' else self.prefix
                self.observe_actual(self.scene(2,2,changed,beat=True),**kwargs)
                self.assertEqual(17 if fault=='deadline_late' else 0,self.status().reason)
                self.assertEqual(2,self.status().inputs)
                self.assertEqual(1,self.status().moves)
                if fault=='deadline_equal':
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,command.deadline_ns,1,0,1))
                elif fault=='deadline_late':
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.deadline_ns+1,1,0,1))

    def test_goods_cancel_and_control_guards_preempt_preserved_entry(self):
        for fault in ('goods','cancel','owner','locked','foreground'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain,command = self.opened_entry()
                changed = self.flicker(terrain); self.now += 2
                self.observe_actual(self.scene(2,2,changed,beat=True))
                if fault=='goods':
                    changed.goods='visible';self.now+=2
                    self.observe_actual(self.scene(2,2,changed,beat=True))
                elif fault=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                else:
                    flags={'front':1,'locked':0,'owner':1}
                    flags[{'owner':'owner','locked':'locked','foreground':'front'}[fault]]=int(fault=='locked')
                    self.tick(**flags)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
                self.assertEqual({'goods':1,'cancel':2,'owner':5,'locked':4,'foreground':3}[fault],self.status().reason)
                self.assertEqual((2,1,1),(self.status().inputs,self.status().moves,self.status().door_changes))

    def test_unknown_entry_synth_never_reuses_the_quiet_permission(self):
        terrain,command = self.opened_entry(); self.now=command.not_before_ns
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
        self.now+=1;self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,command.id,self.now,-1))
        for _ in range(3):
            terrain=self.flicker(terrain);self.now+=100_000_000
            self.observe_actual(self.scene(2,2,terrain,beat=True))
            self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual((4,11,3,1,1),(self.status().input_state,self.status().reason,
            self.status().inputs,self.status().moves,self.status().door_changes))


if __name__=='__main__':
    unittest.main()
