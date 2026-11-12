"""TEST083: observed floor framing for already entered PARTIAL shops.

The maps are procedural API units, separate from the pixel-floor witnesses
and from the omitted future responses of the phone recordings.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_observation072 as observation

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativeShopFraming083Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = tempfile.TemporaryDirectory(prefix='test083-framing-source-')
        directory = Path(cls.snapshot.name)
        origin = Path(os.environ.get('NECRO_TEST083_FRAMING_BASELINE_CORE', CORE))
        for source in origin.glob('NG2*'):
            if source.suffix in ('.c', '.h'):
                shutil.copyfile(source, directory/source.name)
        identity = os.environ.get('NECRO_TEST083_FRAMING_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps({'source_sha256':{
                p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c','.h')},
                'python_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (Path(__file__),Path(fixture.__file__),Path(mechanics.__file__),
                          Path(observation.__file__))}},sort_keys=True,indent=2)+'\n')
        previous = mechanics.CORE
        try:
            mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_entered_gate.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.c_int32, C.c_int32, C.c_int32, C.POINTER(observation.Entrance)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        cls.snapshot.cleanup()

    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch
    credit = observation.NativeObservation072Tests.credit

    def room(self, items=((0,4),), direction=1):
        cells = {(x,y):'floor' for y in range(-5,5) for x in range(-11,12)}
        cells[(-5,-1)] = 'gold'
        terrain = fixture.textured(cells); terrain.goods = 'partial'
        for x,y in items:
            if -11<=x<=11 and -5<=y<=4:
                terrain.tiles[(x,y)] = 'item'
                for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
                    if -11<=x+dx<=11 and -5<=y+dy<=4:
                        terrain.protected.add((x+dx,y+dy))
        dx,dy = fixture.DIRS[direction]
        return terrain, observation.Entrance(valid=1,x=-dx,y=-dy,direction=direction)

    def choose(self, terrain, entrance, x=0, y=0, visit_points=(), native=None):
        source = self.scene(2,2,terrain) if native is None else native
        visits = (C.c_uint16*1089)(); visits[(y+16)*33+x+16] = 1
        for wx,wy,value in visit_points: visits[(wy+16)*33+wx+16] = value
        saved = bytes(source),bytes(visits),bytes(entrance)
        out = observation.Decision()
        ok = self.lib.ng2_choose(C.byref(source),x,y,visits,len(visits),C.byref(entrance),C.byref(out))
        self.assertEqual(saved,(bytes(source),bytes(visits),bytes(entrance)))
        return ok,tuple(getattr(out,name) for name,_ in out._fields_)

    def test_bottom_and_top_partial_items_choose_framing_floor_after_real_entry(self):
        for item_y,expected in ((4,(4,8,0,2,1)),(-5,(3,8,0,-3,1))):
            for direction in (1,2,3,4):
                if (item_y>0 and direction==3) or (item_y<0 and direction==4):
                    continue  # The existing entrance halfplane forbids this direction.
                with self.subTest(item_y=item_y,entrance=direction):
                    terrain,entrance = self.room(((-1,item_y),(0,item_y),(1,item_y)),direction)
                    self.assertEqual((1,expected),self.choose(terrain,entrance),
                        'entered PARTIAL goods must gain a readable floor vantage before nearer GOLD')

    def test_left_right_and_low_item_positions_follow_overflow_not_gold(self):
        cases = [(((-11,0),),1,(1,8,-5,0,1)),
                 (((11,0),),2,(2,8,5,0,1)),
                 (((3,3),),4,(4,8,0,1,1)),
                 (((-3,-3),),3,(3,8,0,-1,1)),
                 (((-6,4),(-5,4),(-4,4)),1,(4,8,0,2,1)),
                 (((-6,2),),1,(1,8,-5,0,1)),
                 (((7,2),),2,(2,8,1,0,1)),
                 (((-7,-2),),1,(1,8,-1,0,1))]
        for items,direction,expected in cases:
            with self.subTest(items=items,entrance=direction):
                terrain,entrance = self.room(items,direction)
                self.assertEqual((1,expected),self.choose(terrain,entrance))

    def test_framing_ties_keep_short_routes_visits_lexical_and_immutable_inputs(self):
        terrain,entrance = self.room(((0,4),),4)
        fixed = {p:k for p,k in terrain.tiles.items() if k in ('item','gold')}
        floors = ((0,0),(-1,0),(-1,1),(-1,2),(1,0),(1,1),(1,2))
        terrain.tiles = {**fixed,**{p:'floor' for p in floors}}
        self.assertEqual((1,(1,8,-1,2,1)),self.choose(terrain,entrance))
        self.assertEqual((1,(2,8,1,2,1)),self.choose(terrain,entrance,visit_points=((-1,2,8),)))
        short = deepcopy(terrain)
        short.tiles.pop((-1,1)); short.tiles.update({(-2,0):'floor',(-2,1):'floor',(-2,2):'floor'})
        self.assertEqual((1,(2,8,1,2,1)),self.choose(short,entrance,visit_points=((1,2,9),)))
        fork = deepcopy(terrain)
        fork.tiles = {**fixed,**{p:'floor' for p in ((0,0),(0,1),(-1,1),(-1,2),(1,1),(1,2))}}
        for _ in range(2):
            self.assertEqual((1,(4,8,-1,2,1)),self.choose(fork,entrance))
        self.assertEqual((1,(4,8,1,2,1)),self.choose(fork,entrance,visit_points=((-1,2,9),)))

    def test_unknown_blocked_item_or_protected_cells_never_form_a_framing_path(self):
        for material in ('unknown','dirt','stone','gold','door','item','protected'):
            with self.subTest(next=material):
                terrain,entrance = self.room(((0,4),),4)
                terrain.tiles = {(0,0):'floor',(0,1):'floor',(0,2):'floor',
                    (0,4):'item',(-5,-1):'gold'}
                if material=='protected': terrain.protected.add((0,1))
                elif material=='unknown': terrain.tiles.pop((0,1))
                else: terrain.tiles[(0,1)] = material
                ok,choice = self.choose(terrain,entrance)
                self.assertEqual((0,0),(ok,choice[0]))
        terrain,entrance = self.room(((0,4),),4)
        terrain.tiles = {(0,0):'floor',(0,1):'floor',(0,2):'dirt',
            (0,4):'item',(-5,-1):'gold'}
        self.assertEqual((1,(4,8,0,1,1)),self.choose(terrain,entrance),
            'the second blocked cell supplies no authority beyond the observed first step')
        terrain.tiles[(0,1)] = 'dirt'; terrain.tiles[(0,2)] = 'floor'
        terrain.tiles.update({(-1,0):'floor',(-1,1):'floor',(-1,2):'floor'})
        short_path = ((0,0),(-1,0),(-1,1),(-1,2))
        longer_path = (*short_path,(0,2))
        self.assertEqual((3,4),(len(short_path)-1,len(longer_path)-1))
        for path in (short_path,longer_path):
            self.assertTrue(all(terrain.tiles[p]=='floor' and p not in terrain.protected for p in path))
            self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:])))
            qx,qy = path[-1]
            # The one actual ITEM (0,4) lands inside the fixed frame for
            # both goals. Equal zero overflow leaves path length decisive.
            self.assertTrue(-6<=-qx<=6 and -2<=4-qy<=2)
        self.assertEqual((1,(1,8,-1,2,1)),self.choose(terrain,entrance),
            'a detour may use only its independently observed FLOOR cells')
        terrain,entrance = self.room(((0,4),),1)
        entrance.x=0; entrance.y=2
        self.assertEqual((1,(1,8,-1,2,1)),self.choose(terrain,entrance),
            'the projected passed entrance itself cannot become a framing goal')

    def test_unentered_invalid_unknown_visible_and_itemless_scenes_keep_old_contract(self):
        for fault in ('unentered','unknown_goods','visible','no_items','protected_only',
                      'outside_grid','in_band','backwards','backwards_top','invalid_flag','invalid_direction',
                      'invalid_entrance','behind_entrance','invalid_scene','no_gold','adjacent_goods','world_goal'):
            with self.subTest(fault=fault):
                terrain,entrance = self.room(((0,4),),1); x=y=0
                expected = (1,(1,8,-5,0,1))
                if fault=='unentered': entrance.valid=0
                elif fault=='unknown_goods': terrain.goods='unknown'
                elif fault=='visible': terrain.goods='visible'; expected=(0,(0,1,0,0,0))
                elif fault in ('no_items','protected_only','outside_grid'):
                    terrain,entrance=self.room(((0,5),) if fault=='outside_grid' else (),1)
                    if fault!='no_items': terrain.protected.add((0,4))
                elif fault=='in_band': terrain,entrance=self.room(((-6,2),),1)
                elif fault=='backwards': terrain,entrance=self.room(((0,4),),3)
                elif fault=='backwards_top': terrain,entrance=self.room(((0,-5),),4)
                elif fault=='invalid_flag': entrance.valid=2; expected=(0,(0,4,0,0,0))
                elif fault=='invalid_direction': entrance.direction=0; expected=(0,(0,4,0,0,0))
                elif fault=='invalid_entrance': entrance.x=17; expected=(0,(0,4,0,0,0))
                elif fault=='behind_entrance': entrance.x=-1; expected=(0,(0,4,0,0,0))
                elif fault=='invalid_scene':
                    native=self.scene(2,2,terrain);native.abi_version=2
                    self.assertEqual((0,(0,0,0,0,0)),self.choose(terrain,entrance,native=native));continue
                elif fault=='no_gold': terrain.tiles.pop((-5,-1)); expected=(0,(0,3,0,0,0))
                elif fault=='adjacent_goods': terrain,entrance=self.room(((0,1),),1); expected=(0,(0,2,0,0,0))
                elif fault=='world_goal':
                    terrain,entrance=self.room(((11,0),),2); x=16; entrance.x=15
                    expected=(1,(3,8,0,-1,1))
                self.assertEqual(expected,self.choose(terrain,entrance,x=x,y=y))

    def test_public_open_entry_partial_framing_then_visible_keeps_ticket_and_goods_priority(self):
        cells = {(0,0):'floor',(-1,0):'floor',(-2,0):'door',
                 (-2,-1):'gold',(-2,1):'gold'}
        cells.update({(x,y):'floor' for y in range(4) for x in range(-8,-2)})
        cells.update({(x,-1):'gold' for x in range(-8,-2)})
        terrain = fixture.textured(cells); self.fit(terrain)
        first = self.next_move(terrain); self.assertEqual(1,first.direction)
        self.ack(first); terrain = fixture.translated(terrain,1); self.observed_result(first,terrain)
        opening = self.next_move(terrain); self.assertEqual(1,opening.direction)
        self.ack(opening); terrain = deepcopy(terrain); terrain.tiles[(-1,0)]='floor'; terrain.goods='partial'
        for x in (-4,-3,-2):
            terrain.tiles[(x,4)]='item'
            for dx,dy in ((0,0),(-1,0),(1,0),(0,-1)):
                terrain.protected.add((x+dx,4+dy))
        self.observed_result(opening,terrain)
        self.assertEqual((2,1,1,0),(self.status().inputs,self.status().moves,
            self.status().door_changes,self.status().goods))
        entering = self.next_move(terrain); before = self.scene(2,2,terrain); state=self.status()
        self.ack(entering); terrain = fixture.translated(terrain,1); after=self.scene(2,2,terrain)
        entrance=observation.Entrance()
        self.assertEqual(1,self.lib.ng2_entered_gate(C.byref(before),C.byref(after),1,
            state.x,state.y,1,C.byref(entrance)))
        self.observed_result(entering,terrain)
        inside=self.next_move(terrain);self.assertEqual(1,inside.direction)
        self.ack(inside);terrain=fixture.translated(terrain,1);self.observed_result(inside,terrain)
        self.assertEqual((1,(4,8,0,2,1)),self.choose(terrain,entrance,
            x=self.status().x,y=self.status().y))
        framing=self.next_move(terrain);self.assertEqual(4,framing.direction)
        self.assertEqual((4,3,1,0),(self.status().inputs,self.status().moves,
            self.status().door_changes,self.status().goods))
        saved=(bytes(framing),self.preparation_epoch(framing),self.credit(),tuple(bytes(e) for e in self.events()))
        self.now+=2;self.observe_actual(self.scene(2,2,terrain,beat=True))
        self.assertEqual(saved,(bytes(self.events()[-1].command),self.preparation_epoch(framing),
            self.credit(),tuple(bytes(e) for e in self.events())))
        self.ack(framing);terrain=fixture.translated(terrain,4);self.observed_result(framing,terrain)
        pending=self.next_move(terrain);self.assertEqual(4,pending.direction)
        credit=self.credit();terrain.goods='visible';self.now+=2
        self.observe_actual(self.scene(2,2,terrain,beat=True))
        self.assertEqual((1,1,5,4,1),(self.status().reason,self.status().goods,
            self.status().inputs,self.status().moves,self.status().door_changes))
        self.assertEqual(credit,self.credit())
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,pending.id,pending.not_before_ns,1,0,1))


if __name__ == '__main__':
    unittest.main()
