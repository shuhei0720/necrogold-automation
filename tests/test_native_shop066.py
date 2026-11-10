"""TEST066 partial merchandise: retain an unchanged safe step inside the shop.

Procedural public-C sequences first verify a move, opening and gate entry.
They exercise guards, not the missing continuation of TEST065's second run.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_gate064 as gate
from tests import test_native_controller as fixture

CORE = gate.CORE

class Entrance(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('valid', 'x', 'y', 'direction')]
class Decision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]

class NativeShop066Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = gate.CORE
        try:
            gate.CORE = CORE
            gate.NativeGate064Tests.setUpClass.__func__(cls)
        finally:
            gate.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
    @classmethod
    def tearDownClass(cls):
        gate.NativeGate064Tests.tearDownClass.__func__(cls)

    setUp = gate.NativeGate064Tests.setUp
    scene = gate.NativeGate064Tests.scene
    observe = gate.NativeGate064Tests.observe
    observe_actual = gate.NativeGate064Tests.observe_actual
    tick = gate.NativeGate064Tests.tick
    status = gate.NativeGate064Tests.status
    events = gate.NativeGate064Tests.events
    motion_wait = gate.NativeGate064Tests.motion_wait
    recovery = gate.NativeGate064Tests.recovery
    ack = gate.NativeGate064Tests.ack
    fit = gate.NativeGate064Tests.fit
    next_move = gate.NativeGate064Tests.next_move
    fresh_engine = gate.NativeGate064Tests.fresh_engine
    observed_result = gate.NativeGate064Tests.observed_result
    publish_procedural_candidate = gate.NativeGate064Tests.publish_procedural_candidate
    continuous_walk = gate.NativeGate064Tests.continuous_walk
    scene_details = gate.NativeGate064Tests.scene_details
    armed_gate = gate.NativeGate064Tests.armed_gate

    def inside(self, direction=3, goods='partial'):
        opened, entry = self.armed_gate(direction, goods)
        self.ack(entry)
        interior = fixture.translated(opened, direction)
        interior.tiles[(8, 3)] = 'stone'
        self.observed_result(entry, interior)
        s = self.status()
        self.assertEqual((3, 2, 1, 1, 0), (s.inputs, s.moves, s.door_changes, s.lead_confirmed, s.reason))
        command = self.next_move(interior)
        self.assertEqual((4, direction, 1), (command.kind, command.direction, self.status().input_state))
        self.entrance_direction = direction
        choice = self.choice(interior)
        self.assertEqual((direction, 8, 1), (choice[0], choice[1], choice[4]))
        return interior, command

    def choice(self, terrain):
        s = self.status(); frame = self.scene(2, 2, terrain, beat=True)
        visits = (C.c_uint16 * 1089)()
        dx, dy = fixture.DIRS[self.entrance_direction]
        for x,y in ((0,0),(dx,dy),(2*dx,2*dy)):
            visits[(y+16)*33+x+16] = 1
        choice = Decision()
        self.assertEqual(1, self.lib.ng2_choose(C.byref(frame), s.x, s.y, visits,
            len(visits), C.byref(Entrance(1,2*dx,2*dy,self.entrance_direction)), C.byref(choice)))
        return tuple(getattr(choice,k) for k,_ in choice._fields_)

    def drift(self, terrain):
        changed = deepcopy(terrain)
        changed.tiles[(8,3)] = 'dirt' if changed.tiles[(8,3)] == 'stone' else 'stone'
        return changed

    def test_partial_interior_remote_drift_keeps_original_ticket_in_four_directions(self):
        for direction in (1,2,3,4):
            with self.subTest(direction=direction):
                self.fresh_engine(); terrain, command = self.inside(direction)
                decision = self.choice(terrain)
                events = tuple(bytes(e) for e in self.events())
                wait, recovery = bytes(self.motion_wait()), bytes(self.recovery())
                for _ in range(3):
                    terrain = self.drift(terrain)
                    self.assertEqual(decision, self.choice(terrain))
                    self.now += 2; self.observe_actual(self.scene(2,2,terrain,beat=True))
                    s = self.status()
                    self.assertEqual((0,0,1,command.id,3,2,1), (s.reason,s.terminal,s.input_state,
                        s.current_command_id,s.inputs,s.moves,s.door_changes),
                        'unchanged safe partial-goods interior step must retain the unstarted ticket')
                    self.assertEqual(events, tuple(bytes(e) for e in self.events()))
                    self.assertEqual(wait, bytes(self.motion_wait()))
                    self.assertEqual(recovery, bytes(self.recovery()))
                self.ack(command)
                self.observed_result(command, fixture.translated(terrain,command.direction))
                self.assertEqual((0,4,3,1), (self.status().reason,self.status().inputs,
                    self.status().moves,self.status().door_changes))

    def test_partial_interior_changed_authority_or_motion_is_not_coalesced(self):
        for fault in ('not_entered','near','target','gold','protected','item','goods_change','signature'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                if fault == 'not_entered':
                    # Goods may already be PARTIAL outside the shop. A real
                    # approach move alone does not prove a gate crossing.
                    terrain = fixture.textured({**{(x,0):'floor' for x in range(-7,1)},
                        (-7,0):'stone',(-8,0):'door',(-8,-1):'gold',(-8,1):'gold',
                        (-4,-2):'stone',(5,1):'stone'})
                    self.fit(terrain); first = self.next_move(); self.ack(first)
                    terrain = fixture.translated(terrain,first.direction)
                    terrain.goods = 'partial'; terrain.tiles[(8,3)] = 'stone'
                    self.observed_result(first,terrain); command = self.next_move(terrain)
                    self.assertEqual((1,1,0),(self.status().inputs,self.status().moves,self.status().door_changes))
                    visits = (C.c_uint16 * 1089)()
                    visits[16*33+16] = visits[16*33+15] = 1
                    choices = []
                    for world in (terrain,self.drift(terrain)):
                        frame = self.scene(2,2,world,beat=True); decision = Decision()
                        self.assertEqual(1,self.lib.ng2_choose(C.byref(frame),-1,0,visits,
                            len(visits),C.byref(Entrance()),C.byref(decision)))
                        choices.append(tuple(getattr(decision,k) for k,_ in decision._fields_))
                    self.assertEqual(choices[0],choices[1])
                    self.assertEqual((1,8,1),(choices[0][0],choices[0][1],choices[0][4]))
                else:
                    terrain,command = self.inside()
                changed = self.drift(terrain)
                if fault=='near': changed.tiles[(1,-1)]='stone'
                elif fault=='target': changed.tiles[(0,-1)]='dirt'
                elif fault=='gold': changed.tiles[(7,3)]='gold'
                elif fault=='protected': changed.protected.add((7,3))
                elif fault=='item': changed.tiles[(7,3)]='item'
                elif fault=='goods_change': changed.goods='unknown'
                elif fault=='signature': changed.signature=bytes([40])*23296
                self.now+=2; self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertEqual(17,self.status().reason)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
                self.assertEqual((1,1,0) if fault=='not_entered' else (3,2,1),
                    (self.status().inputs,self.status().moves,self.status().door_changes))

    def test_partial_interior_goods_cancel_and_live_control_guards_remain_priorities(self):
        for mode in ('goods','cancel','foreground','locked','owner'):
            with self.subTest(mode=mode):
                self.fresh_engine(); terrain,command = self.inside()
                changed=self.drift(terrain)
                if mode=='goods': changed.goods='visible'
                if mode=='cancel': self.lib.ng2_controller_cancel(self.engine,self.now,2)
                self.now+=2; self.observe_actual(self.scene(2,2,changed,beat=True))
                if mode in ('goods','cancel'):
                    self.assertEqual(1 if mode=='goods' else 2,self.status().reason)
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
                else:
                    self.assertEqual(0,self.status().reason)
                    front,locked,owner=(0,0,1) if mode=='foreground' else (1,1,1) if mode=='locked' else (1,0,0)
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,front,locked,owner))
                self.assertEqual((3,2,1),(self.status().inputs,self.status().moves,self.status().door_changes))

    def test_partial_interior_late_actual_commit_and_wrong_prefix_never_extend_ticket(self):
        for mode in ('late','unstable','prefix'):
            with self.subTest(mode=mode):
                self.fresh_engine(); terrain,command = self.inside()
                changed=self.drift(terrain); before=tuple(bytes(e) for e in self.events())
                last=self.status().last_capture_id
                if mode=='late':
                    self.now=command.deadline_ns-1
                    self.observe_actual(self.scene(2,2,changed,beat=True),commit=command.deadline_ns+1)
                    self.assertEqual(17,self.status().reason)
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.deadline_ns+1,1,0,1))
                else:
                    self.now+=2; self.observe_actual(self.scene(2,2,changed,beat=True),
                        stable=0 if mode=='unstable' else 1,prefix=self.prefix+1 if mode=='prefix' else self.prefix)
                    self.assertEqual(last,self.status().last_capture_id)
                    self.assertEqual(before,tuple(bytes(e) for e in self.events()))
                self.assertEqual(bytes(command),bytes(next(e for e in self.events() if e.command.id==command.id).command))
                self.assertEqual((3,2,1),(self.status().inputs,self.status().moves,self.status().door_changes))
