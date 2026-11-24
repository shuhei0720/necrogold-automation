"""TEST118: refresh an unsent logical MOVE using an independent pre-input view.

The procedural world keeps a fixed physical HUD epoch.  These public-C
boundaries are not a replay of the phone's unrecorded model or callbacks.
The original image/ticket remains provenance for the retired ID; no ACK is
interpreted as movement and no threshold in Motion is changed here.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_passage_palette077 as passage_palette
from tests.test_native_motion067 import Motion


CORE = Path(os.environ.get('NECRO118_PREINPUT_CORE', native.CORE))


class NativePreinputRefresh118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = CORE
            native.NativeControllerTests.setUpClass.__func__(cls)
        finally:
            native.CORE = previous
        cls.lib.ng2_controller_observe_at.argtypes = [C.c_void_p, C.POINTER(native.Scene),
            C.c_uint64, C.c_uint64, C.c_uint64, C.c_uint64, C.c_int32, C.c_uint64]
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.POINTER(Motion)]

    tearDownClass = classmethod(native.NativeControllerTests.tearDownClass.__func__)

    def observe_interval(self, terrain, *, start, end, commit, prefix=None, stable=1):
        self.now = commit
        frame = self.scene(2, 2 if terrain.gold else 1, terrain, beat=False)
        midpoint = start + (end - start) // 2
        frame.beat_valid = 1
        frame.beat_remaining = ((5*native.SECOND-midpoint) % native.PERIOD)/native.PERIOD
        frame.beat_spacing = 104.
        frame.beat_center = 446.
        self.number += 1
        result = self.lib.ng2_controller_observe_at(self.engine, C.byref(frame), self.number,
            start, end, self.prefix if prefix is None else prefix, stable, commit)
        if result == 1:
            self._last_fixture_scene = native.Scene.from_buffer_copy(bytes(frame))
        return result

    def normal_motion(self, before, after, direction):
        a = self.scene(2, 2 if before.gold else 1, before)
        b = self.scene(2, 2 if after.gold else 1, after)
        result = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(a), C.byref(b), direction,
            C.byref(result)))
        return result.kind, result.dx, result.dy

    def independent_source(self, terrain, old, *, gap=None):
        # P/10 only coalesces captures; normal Motion still proves strict zero.
        # Never select this source using a future successful post-input view.
        changed = deepcopy(terrain)
        changed.signature = bytes(min(255, value*11//10 + 3) for value in terrain.signature)
        self.assertEqual((2, 0, 0), self.normal_motion(terrain, changed, old.direction))
        start = old.source_start_ns + (native.PERIOD//10 if gap is None else gap)
        end = start + 12_000_000
        commit = end + 10_000_000
        self.assertLess(commit, old.not_before_ns)
        self.assertEqual(1, self.observe_interval(changed, start=start, end=end, commit=commit))
        return changed

    def test_same_tiles_independent_preinput_source_reissues_same_logical_MOVE_once(self):
        terrain, old = self.continuous_walk(moves=2, direction=1)
        epoch = self.preparation_epoch(old)
        before = self.status()
        self.assertNotEqual(0, epoch)
        changed = self.independent_source(terrain, old)
        accepted_id = self.number
        ready, new = self.tick()
        self.assertEqual((1, accepted_id), (ready, new.source_capture_id),
            'an independent same-position pre-input image must become the SAME reissue source')
        self.assertGreater(new.id, old.id)
        self.assertEqual((old.ordinal, old.direction, old.target_ns, old.not_before_ns, old.deadline_ns),
            (new.ordinal, new.direction, new.target_ns, new.not_before_ns, new.deadline_ns))
        self.assertEqual(epoch, self.preparation_epoch(new), 'one logical preparation lease survives')
        after = self.status()
        self.assertEqual((before.inputs, before.moves, before.x, before.y),
            (after.inputs, after.moves, after.x, after.y))
        retired = next(event for event in self.events() if event.command.id == old.id)
        self.assertEqual((3, 0), (retired.outcome, retired.begin_ns))
        self.now = old.not_before_ns
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))
        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, new.id, self.now, 1, 0, 1))
        self.now += 275_000_000
        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, new.id, self.now, 1),
            'public API ACK=1; Event outcome ACK=2 is an output enum')
        self.prefix = new.id
        self.assertEqual(3, self.status().input_state)
        moved = native.translated(changed, old.direction)
        start = self.now + 100_000_000
        self.assertEqual(1, self.observe_interval(moved, start=start,
            end=start+12_000_000, commit=start+22_000_000))
        self.assertEqual((3, 3, 0), (self.status().inputs, self.status().moves,
            self.status().input_state))

    def assert_same_pending(self, old, epoch, event_count):
        self.assertEqual((1, old.id, event_count), (self.status().input_state,
            self.status().current_command_id, len(self.events())))
        self.assertEqual(epoch, self.preparation_epoch(old))
        self.assertEqual(0, self.tick()[0])

    def test_capture_start_spacing_boundary_and_nonoverlap_are_required(self):
        terrain, old = self.continuous_walk()
        epoch = self.preparation_epoch(old); count = len(self.events())
        self.independent_source(terrain, old, gap=native.PERIOD//10-1)
        self.assert_same_pending(old, epoch, count)
        # The already accepted image now ends after the P/10 boundary. A
        # different ID whose acquisition overlaps it is not independent.
        start = old.source_start_ns + native.PERIOD//10
        self.assertEqual(1, self.observe_interval(terrain, start=start,
            end=start+20_000_000, commit=self.now+1))
        self.assert_same_pending(old, epoch, count)

    def test_once_is_keyed_by_logical_epoch_not_reissued_command_ID(self):
        terrain, old = self.continuous_walk()
        epoch = self.preparation_epoch(old)
        first = self.independent_source(terrain, old)
        ready, new = self.tick(); self.assertEqual(1, ready)
        count = len(self.events())
        second = deepcopy(first)
        second.signature = bytes(min(255, value+1) for value in first.signature)
        start = old.source_start_ns+80_000_000
        self.assertEqual(1, self.observe_interval(second, start=start,
            end=start+12_000_000, commit=start+14_000_000))
        self.assert_same_pending(new, epoch, count)

    def test_spacing_origin_stays_at_frozen_logical_source_after_ordinary_reissue(self):
        terrain, original = self.continuous_walk()
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        ready,current=self.tick();self.assertEqual(1,ready)
        epoch=self.preparation_epoch(current)
        self.assertGreater(current.source_start_ns,original.source_start_ns)
        self.independent_source(changed,original)
        ready,new=self.tick();self.assertEqual(1,ready)
        self.assertEqual((self.number,epoch),(new.source_capture_id,self.preparation_epoch(new)))
        self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns),
            (new.target_ns,new.not_before_ns,new.deadline_ns))

    def test_clear_passage_same_tiles_uses_new_primary_with_original_epoch(self):
        def observe_clear(terrain, **options):
            frame=terrain if isinstance(terrain,native.Scene) else self.scene(2,
                2 if terrain.gold else 1,terrain,beat=True)
            return native.NativeControllerTests.observe(self,frame,**options)
        self.observe=observe_clear
        terrain,old=passage_palette.NativePassagePalette077Tests.armed_palette(self)
        self.assertEqual(1,self.scene(2,1,terrain).gold_state)
        epoch=self.preparation_epoch(old)
        changed=self.independent_source(terrain,old)
        ready,new=self.tick()
        self.assertEqual((1,self.number,epoch),(ready,new.source_capture_id,self.preparation_epoch(new)))
        self.assertEqual((old.direction,old.ordinal,old.target_ns,old.not_before_ns,old.deadline_ns),
            (new.direction,new.ordinal,new.target_ns,new.not_before_ns,new.deadline_ns))
        self.now=old.not_before_ns
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.now+=275_000_000
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,new.id,self.now,1))
        self.prefix=new.id;start=self.now+100_000_000
        self.assertEqual(1,self.observe_interval(native.translated(changed,new.direction),
            start=start,end=start+12_000_000,commit=start+22_000_000))
        self.assertEqual((2,2,0),(self.status().inputs,self.status().moves,self.status().input_state))

    def test_at_not_before_optional_refresh_keeps_old_authority(self):
        terrain, old = self.continuous_walk()
        epoch = self.preparation_epoch(old); count = len(self.events())
        start = old.source_start_ns+native.PERIOD//10
        self.assertEqual(1, self.observe_interval(terrain, start=start,
            end=start+12_000_000, commit=old.not_before_ns))
        self.assert_same_pending(old, epoch, count)
        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id,
            old.not_before_ns, 1, 0, 1))

    def test_first_step_and_started_ACK_UNKNOWN_do_not_refresh(self):
        for state in ('first', 'started', 'ACK', 'UNKNOWN'):
            with self.subTest(state=state):
                self.fresh_engine()
                if state=='first':
                    terrain=self.fit();old=self.next_move(terrain)
                    self.assertEqual(0, self.preparation_epoch(old))
                    start=old.source_start_ns+native.PERIOD//10
                else:
                    terrain,old=self.continuous_walk()
                    self.now=old.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                    if state in ('ACK','UNKNOWN'):
                        self.now+=275_000_000
                        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,old.id,self.now,
                            1 if state=='ACK' else -1))
                        if state=='ACK':self.prefix=old.id
                    start=self.now+native.PERIOD//10
                count=len(self.events());inputs=self.status().inputs;moves=self.status().moves
                self.observe_interval(terrain,start=start,end=start+12_000_000,commit=start+22_000_000)
                self.assertEqual(count,len(self.events()))
                self.assertEqual(old.id,self.events()[-1].command.id)
                self.assertEqual((inputs,moves),(self.status().inputs,self.status().moves))

    def test_bad_prefix_stability_same_capture_and_reverse_time_do_not_refresh(self):
        for fault in ('prefix','unstable','same_ID','reverse_time'):
            with self.subTest(fault=fault):
                self.fresh_engine();terrain,old=self.continuous_walk()
                epoch=self.preparation_epoch(old);count=len(self.events())
                start=old.source_start_ns+native.PERIOD//10
                if fault=='same_ID':self.number=old.source_capture_id-1
                if fault=='reverse_time':
                    self.assertEqual(-1,self.lib.ng2_controller_observe_at(self.engine,
                        C.byref(self.scene(2,2,terrain)),self.number+1,start,start+12_000_000,
                        self.prefix,1,self.now-1))
                else:
                    self.assertEqual(0,self.observe_interval(terrain,start=start,end=start+12_000_000,
                        commit=start+22_000_000,prefix=self.prefix+1 if fault=='prefix' else None,
                        stable=0 if fault=='unstable' else 1))
                self.assert_same_pending(old,epoch,count)

    def test_nonzero_and_unknown_Motion_never_supply_a_new_source(self):
        for kind in ('unit','partial','unknown'):
            with self.subTest(kind=kind):
                self.fresh_engine();terrain,old=self.continuous_walk()
                epoch=self.preparation_epoch(old);count=len(self.events())
                changed=deepcopy(terrain)
                if kind=='unknown':changed.signature=bytes([40])*23296
                else:changed.signature=native.translated(terrain,old.direction,
                    amount=1 if kind=='unit' else 8).signature
                self.assertNotEqual((2,0,0),self.normal_motion(terrain,changed,old.direction))
                start=old.source_start_ns+native.PERIOD//10
                self.assertEqual(1,self.observe_interval(changed,start=start,end=start+12_000_000,
                    commit=start+22_000_000))
                self.assert_same_pending(old,epoch,count)

    def test_changed_protection_item_and_local_terrain_do_not_use_optional_refresh(self):
        for fault in ('protected','item','local','choice'):
            with self.subTest(fault=fault):
                self.fresh_engine();terrain,old=self.continuous_walk()
                changed=deepcopy(terrain)
                if fault=='protected':changed.protected.add((-10,4))
                elif fault=='item':changed.tiles[(-10,4)]='item'
                elif fault=='local':changed.tiles[(-1,1)]='stone'
                else:changed.tiles[(-5,0)]='stone'
                start=old.source_start_ns+native.PERIOD//10
                self.observe_interval(changed,start=start,end=start+12_000_000,commit=start+22_000_000)
                # Existing ordinary scene-change policies remain responsible
                # for these cases (including a separately qualified FRESH).
                # The new optional zero-mask branch must not authorize them.
                self.tick()
                self.assertFalse(any(row.observed_capture_id==self.number and row.change_mask==0
                    for row in self.scene_changes()))

    def exhaust_refresh_budget(self, chains):
        terrain,current=self.continuous_walk();toggle=False
        for chain in range(chains):
            for _ in range(2):
                terrain=deepcopy(terrain);toggle=not toggle
                if toggle:terrain.tiles[(-10,4)]='stone'
                else:terrain.tiles.pop((-10,4),None)
                self.now+=2;self.observe(self.scene(2,2,terrain,beat=True))
                current=self.next_move()
            if chain+1<chains:
                self.ack(current);terrain=native.translated(terrain,1)
                self.observed_result(current,terrain);current=self.next_move(terrain)
        return terrain,current

    def test_chain_and_run_budget_exhaustion_are_optional_noops(self):
        for chains in (1,4):
            with self.subTest(chains=chains):
                self.fresh_engine();terrain,old=self.exhaust_refresh_budget(chains)
                if chains==4:
                    self.ack(old);terrain=native.translated(terrain,1)
                    self.observed_result(old,terrain);old=self.next_move(terrain)
                epoch=self.preparation_epoch(old);count=len(self.events())
                self.independent_source(terrain,old)
                self.assert_same_pending(old,epoch,count)


for _name in ('setUp', 'scene', 'observe', 'tick', 'status', 'events', 'ack', 'fit',
    'next_move', 'publish_procedural_candidate', 'fresh_engine', 'recovery',
    'motion_wait', 'preparation_epoch', 'observed_result', 'continuous_walk', 'scene_changes'):
    setattr(NativePreinputRefresh118Tests, _name, getattr(native.NativeControllerTests, _name))


if __name__ == '__main__':
    unittest.main()
