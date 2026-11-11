"""TEST081: keep an opened UP entry while clipped goods stay quarantined.

The 152/154 retained pair changes only its originally protected top grid row.
These public-C maps, signatures and clocks are procedural units, not future
phone frames or evidence that all three real products have been observed.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_observation072 as observation

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativeClippedEntry081Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            baseline = os.environ.get('NECRO_TEST081_BASELINE_CONTROLLER')
            cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test081-clipped-source-')
            directory = Path(cls.baseline_directory.name)
            for path in CORE.glob('NG2*'):
                if path.suffix in ('.c', '.h'):
                    shutil.copyfile(path, directory / path.name)
            if baseline:
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
            mechanics.CORE = directory
            evidence = os.environ.get('NECRO_TEST081_CLIPPED_SOURCE_IDENTITY')
            if evidence:
                Path(evidence).write_text(json.dumps({'controller_override':baseline,
                    'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c','.h')},
                    'python_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (Path(__file__),Path(fixture.__file__),Path(mechanics.__file__),
                                  Path(observation.__file__))}},sort_keys=True,indent=2)+'\n')
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.POINTER(observation.Motion)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    scene_details = mechanics.NativeRecoveryTests.scene_details
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
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
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation

    def armed(self, direction=3, opened=True, goods='partial'):
        rotate = {1: lambda x,y: (y,-x), 2: lambda x,y: (-y,x),
                  3: lambda x,y: (x,y), 4: lambda x,y: (-x,-y)}[direction]
        terrain = fixture.textured({rotate(x,y): kind for (x,y),kind in {
            (0,0): 'floor', (0,-1): 'floor', (0,-2): 'door' if opened else 'floor',
            (-1,-2): 'gold', (1,-2): 'gold', (0,-3): 'floor',
            (0,-4): 'floor', (-4,2): 'stone', (5,2): 'stone'}.items()})
        self.fit(terrain)
        first = self.next_move(terrain); self.assertEqual(direction, first.direction)
        self.ack(first); terrain = fixture.translated(terrain, direction)
        self.observed_result(first, terrain)
        if opened:
            opening = self.next_move(terrain); self.assertEqual(direction, opening.direction)
            self.ack(opening)
            terrain = deepcopy(terrain); terrain.tiles[fixture.DIRS[direction]] = 'floor'
        terrain.goods = goods
        for y in (-5, -4):
            for x in range(-4, 3):
                terrain.protected.add((x, y))
                if -3 <= x <= 1: terrain.tiles[(x, y)] = 'item'
        for x in range(-3, 2): terrain.protected.add((x, -3))
        if opened:
            self.observed_result(opening, terrain)
        else:
            self.now += 2; self.observe_actual(self.scene(2, 2, terrain, beat=True))
        command = self.next_move(terrain)
        dx, dy = fixture.DIRS[direction]
        self.assertEqual((direction, 5, dx, dy, 1), self.choice(terrain))
        self.assertEqual((int(opened)+1, 1, int(opened), 0),
            (self.status().inputs, self.status().moves, self.status().door_changes, self.status().goods))
        return terrain, command

    def clipped(self, terrain, kind='mixed', shrink=True):
        changed = deepcopy(terrain)
        if kind == 'mixed':
            values = ('unknown', 'floor', 'dirt', 'unknown', 'gold')
        else:
            values = (kind,) * 5
        for x, latest in zip(range(-3, 2), values):
            if latest == 'unknown': changed.tiles.pop((x, -5), None)
            else: changed.tiles[(x, -5)] = latest
        if shrink:
            changed.protected.remove((-4, -5)); changed.protected.remove((2, -5))
        return changed

    def saved_ticket(self, command):
        return (self.credit(), bytes(command), self.preparation_epoch(command),
            tuple(bytes(e) for e in self.events()), bytes(self.motion_wait()),
            bytes(self.recovery()), tuple(bytes(d) for d in self.scene_details()))

    def preserve(self, terrain, changed, command):
        self.assertEqual(self.choice(terrain), self.choice(changed))
        self.assertEqual((2, 0, 0), self.motion(terrain, changed, command.direction))
        saved = self.saved_ticket(command)
        self.assertNotEqual(0, saved[2], 'the original entry already has a preparation epoch')
        self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
        self.assertEqual((0, 0, 1, command.id), (self.status().reason,
            self.status().terminal, self.status().input_state, self.status().current_command_id),
            'the same opened-floor ticket must retain the original protected top envelope')
        self.assertEqual(saved, self.saved_ticket(self.events()[-1].command))
        return saved

    def test_clipped_partial_goods_preserve_original_up_entry_then_real_move_and_goods_hold(self):
        for kind in ('unknown', 'floor', 'dirt', 'gold', 'mixed'):
            with self.subTest(kind=kind):
                self.fresh_engine(); terrain, command = self.armed()
                changed = self.clipped(terrain, kind)
                self.preserve(terrain, changed, command)
                self.ack(command)
                self.assertEqual(command.not_before_ns, self.events()[-1].begin_ns)
                self.observed_result(command, fixture.translated(changed, command.direction))
                self.assertEqual((0, 3, 2, 1, 0), (self.status().reason,
                    self.status().inputs, self.status().moves, self.status().door_changes, self.status().goods))
                after = fixture.translated(changed, command.direction); after.goods = 'visible'
                self.now += 2; self.observe_actual(self.scene(2, 2, after, beat=True))
                self.assertEqual((1, 1, 3, 2, 1), (self.status().reason, self.status().goods,
                    self.status().inputs, self.status().moves, self.status().door_changes))

    def test_source_mask_and_top_gold_quarantine_survive_mask_zero_return(self):
        terrain, command = self.armed(); saved = self.saved_ticket(command)
        expanded = self.clipped(terrain, 'gold')
        self.preserve(terrain, expanded, command)
        self.preserve(terrain, terrain, command)
        mixed = self.clipped(terrain, 'mixed', shrink=False)
        self.preserve(terrain, mixed, command)
        self.assertEqual(saved, self.saved_ticket(command))
        self.assertEqual(0, self.status().restarts)

    def test_new_protection_nonedge_items_gold_or_near_changes_cannot_use_quarantine(self):
        for fault in ('new_top_protection', 'new_remote_protection', 'nonedge_protected_material',
                      'outside_item', 'outside_gold_loss', 'near_origin', 'near_next',
                      'target', 'top_stone', 'remote_material', 'lost_accepted_gold',
                      'unknown_signature', 'mask_zero_unknown_signature',
                      'mask_zero_without_gold_unknown', 'mask_zero_without_gold_late'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed()
                if fault == 'lost_accepted_gold':
                    reveal = deepcopy(terrain); reveal.tiles[(-5, -3)] = 'gold'
                    self.now += 2; self.observe_actual(self.scene(2, 2, reveal, beat=True))
                    self.assertEqual((0, 1, command.id), (self.status().reason,
                        self.status().input_state, self.status().current_command_id))
                changed = self.clipped(terrain)
                if fault == 'new_top_protection': changed.protected.add((3, -5))
                elif fault == 'new_remote_protection': changed.protected.add((8, 2))
                elif fault == 'nonedge_protected_material': changed.tiles[(-3, -4)] = 'floor'
                elif fault == 'outside_item': changed.tiles[(8, 2)] = 'item'
                elif fault == 'outside_gold_loss': changed.tiles[(-1, -1)] = 'floor'
                elif fault == 'near_origin': changed.tiles[(1, 0)] = 'dirt'
                elif fault == 'near_next': changed.protected.add((1, -2))
                elif fault == 'target': changed.tiles[(0, -1)] = 'dirt'
                elif fault == 'top_stone': changed.tiles[(-3, -5)] = 'stone'
                elif fault == 'remote_material': changed.tiles[(8, 2)] = 'stone'
                elif fault in ('mask_zero_without_gold_unknown', 'mask_zero_without_gold_late'):
                    self.preserve(terrain, self.clipped(terrain, 'unknown'), command)
                    changed = deepcopy(terrain)
                    self.assertEqual(terrain.tiles, changed.tiles)
                    self.assertEqual(terrain.protected, changed.protected)
                    if fault == 'mask_zero_without_gold_late':
                        self.now = command.deadline_ns
                    else:
                        rng = random.Random(81081)
                        changed.signature = bytes(rng.randrange(20, 100) for _ in terrain.signature)
                        self.assertEqual((0, 0, 0), self.motion(terrain, changed, command.direction))
                elif fault in ('unknown_signature', 'mask_zero_unknown_signature'):
                    if fault == 'mask_zero_unknown_signature':
                        self.preserve(terrain, self.clipped(terrain, 'gold'), command)
                        changed = deepcopy(terrain)
                    rng = random.Random(81081)
                    changed.signature = bytes(rng.randrange(20, 100) for _ in terrain.signature)
                    self.assertEqual((0, 0, 0), self.motion(terrain, changed, command.direction))
                credit = self.credit(); self.now += 2
                self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertNotEqual((0, 1, command.id), (self.status().reason,
                    self.status().input_state, self.status().current_command_id))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual(credit, self.credit())

    def test_original_deadline_actual_commit_prefix_and_total_budgets_remain_fixed(self):
        for fault in ('deadline_equal', 'deadline_late', 'prefix', 'unstable', 'walk', 'session'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed(); changed = self.clipped(terrain)
                saved = self.saved_ticket(command); last_capture = self.status().last_capture_id
                kwargs = {}
                if fault.startswith('deadline'):
                    self.now = command.deadline_ns-1
                    kwargs['commit'] = command.deadline_ns+int(fault=='deadline_late')
                elif fault in ('prefix', 'unstable'):
                    self.now += 2; kwargs['prefix'] = self.prefix+int(fault=='prefix')
                    kwargs['stable'] = int(fault!='unstable')
                else:
                    self.now = (self.status().walk_started_ns+45*SECOND if fault=='walk'
                                else self.status().started_ns+180*SECOND)
                    self.tick()
                self.observe_actual(self.scene(2, 2, changed, beat=True), **kwargs)
                if fault.startswith('deadline'):
                    self.now = kwargs['commit']
                if fault == 'deadline_equal':
                    self.assertEqual((0, 1, command.id), (self.status().reason,
                        self.status().input_state, self.status().current_command_id))
                    self.assertEqual(saved, self.saved_ticket(command))
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.deadline_ns, 1, 0, 1))
                elif fault in ('prefix', 'unstable'):
                    self.assertEqual(last_capture, self.status().last_capture_id)
                    self.assertEqual(saved, self.saved_ticket(command))
                else:
                    self.assertEqual({'deadline_late': 17, 'walk': 14, 'session': 15}[fault], self.status().reason)
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, max(self.now, command.deadline_ns+1), 1, 0, 1))
                self.assertEqual((1, 1, 0), (self.status().moves, self.status().door_changes, self.status().goods))

    def test_unopened_other_direction_or_entered_state_does_not_gain_clipped_permission(self):
        for fault in ('not_opened', 'left', 'right', 'down', 'unknown_goods', 'entered'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                direction = {'left': 1, 'right': 2, 'down': 4}.get(fault, 3)
                terrain, command = self.armed(direction=direction, opened=fault!='not_opened',
                    goods='unknown' if fault=='unknown_goods' else 'partial')
                if fault == 'entered':
                    self.ack(command); terrain = fixture.translated(terrain, direction)
                    self.observed_result(command, terrain); command = self.next_move(terrain)
                changed = self.clipped(terrain, shrink=fault!='entered')
                credit = self.credit(); self.now += 2
                self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertNotEqual((0, 1, command.id), (self.status().reason,
                    self.status().input_state, self.status().current_command_id))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual(credit, self.credit())

    def test_goods_cancel_owner_and_started_unknown_send_override_clipped_retention(self):
        for fault in ('goods', 'cancel', 'owner', 'foreground', 'locked', 'begun', 'unknown'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed(); changed = self.clipped(terrain)
                if fault in ('begun', 'unknown'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    if fault == 'unknown':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1))
                    count = len(self.events()); self.now += 2
                    self.observe_actual(self.scene(2, 2, changed, beat=True))
                    self.assertEqual((2 if fault=='begun' else 4, count,
                        2 if fault=='begun' else 3, 1),
                        (self.status().input_state, len(self.events()), self.status().inputs, self.status().moves))
                    self.assertEqual(0, self.tick()[0])
                    continue
                self.preserve(terrain, changed, command)
                if fault == 'goods':
                    changed.goods = 'visible'; self.now += 2
                    self.observe_actual(self.scene(2, 2, changed, beat=True))
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                else:
                    flags = {'front': 1, 'locked': 0, 'owner': 1}
                    flags[{'owner': 'owner', 'locked': 'locked', 'foreground': 'front'}[fault]] = int(fault=='locked')
                    self.tick(**flags)
                self.assertEqual({'goods': 1, 'cancel': 2, 'owner': 5, 'foreground': 3, 'locked': 4}[fault], self.status().reason)
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual((2, 1, 1), (self.status().inputs, self.status().moves, self.status().door_changes))


if __name__ == '__main__':
    unittest.main()
