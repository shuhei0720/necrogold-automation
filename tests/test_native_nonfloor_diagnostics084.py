"""TEST084: retain a true non-FLOOR rejection without inventing motion.

Public procedural C scenes exercise the old stop and its additive diagnostic.
They do not reconstruct the unretained TEST083 capture 285.
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

from necroprobe import native_walk
from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics

CORE = mechanics.CORE


class NativeNonfloorDiagnostics084Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_directory = tempfile.TemporaryDirectory(prefix='test084-nonfloor-source-')
        directory = Path(cls.source_directory.name)
        origin = Path(os.environ.get('NECRO_TEST084_NONFLOOR_BASELINE_CORE', CORE))
        for path in origin.glob('NG2*'):
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, directory / path.name)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c', '.h')}
        expected = os.environ.get('NECRO_TEST084_NONFLOOR_EXPECTED_IDENTITY')
        if expected and hashes != json.loads(Path(expected).read_text()):
            raise AssertionError('the immutable eight-file baseline identity changed')
        identity = os.environ.get('NECRO_TEST084_NONFLOOR_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps({
                'source_directory': str(origin), 'source_sha256': hashes,
                'python_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (Path(__file__), Path(fixture.__file__),
                              Path(mechanics.__file__), Path(native_walk.__file__))}},
                sort_keys=True, indent=2)+'\n')
        previous = mechanics.CORE
        try:
            mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        cls.source_directory.cleanup()

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
    publish_procedural_candidate = mechanics.NativeRecoveryTests.publish_procedural_candidate
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    scene_changes = fixture.NativeControllerTests.scene_changes
    scene_details = fixture.NativeControllerTests.scene_details
    motion_references = fixture.NativeControllerTests.motion_references

    def credit(self):
        s = self.status()
        return tuple(getattr(s, key) for key in ('inputs', 'moves', 'door_changes',
            'terrain_changes', 'x', 'y', 'last_ordinal', 'first_move_ns', 'lead_ns'))

    def acknowledged_move(self, assessed=False):
        terrain = self.fit()
        command = self.next_move()
        self.ack(command)
        if assessed:
            uncertain = deepcopy(terrain)
            uncertain.signature = bytes([40])*23296
            self.observed_result(command, uncertain)
            self.assertEqual((3, 1, 0), (self.status().input_state,
                self.motion_wait().attempts, self.status().moves))
        self.assertEqual(3, self.status().input_state)
        return terrain, command

    def authority(self):
        return (self.credit(), tuple(bytes(e) for e in self.events()),
            bytes(self.recovery()), tuple(bytes(r) for r in self.motion_references()))

    @staticmethod
    def scalars(value):
        return {name: getattr(value, name) for name, _ in value._fields_}

    def validated_trace(self):
        rows = [self.scalars(row) for row in self.scene_changes()]
        for row in rows:
            row['replan_allowed'] = bool(row['replan_allowed'])
        details = []
        for detail in self.scene_details():
            encoded = {name: getattr(detail, name) for name, _ in detail._fields_
                if name != 'cells'}
            encoded['cells'] = [self.scalars(cell) for cell in detail.cells[:detail.cell_count]]
            details.append(encoded)
        self.assertEqual(rows, native_walk._scene_changes(rows))
        self.assertEqual(details, native_walk._scene_change_details(details))
        events = []
        for event in self.events():
            encoded = self.scalars(event.command)
            encoded.update({name: getattr(event, name) for name, _ in event._fields_
                if name != 'command'})
            events.append(encoded)
        references = [self.scalars(row) for row in self.motion_references()]
        for row in references:
            for flag in ('reference_eligible', 'fallback_attempted'):
                row[flag] = bool(row[flag])
        wait = self.scalars(self.motion_wait())
        wait['active'] = bool(wait['active'])
        report = dict(schema='ngg2-native-v1', clock_id='0'*32,
            input_state=self.status().input_state, device_now_ns=self.now,
            goods=self.status().goods, events=events, motion_references=references,
            motion_wait=wait, scene_changes=rows, scene_change_details=details)
        clean = native_walk._report(report, require_motion_references=True,
            api_version='1.98.16-ngg2')
        self.assertEqual(report, clean)
        return rows, details

    def test_ack_nonfloor_rejection_records_state_diff_without_motion_assessment(self):
        for assessed in (False, True):
            with self.subTest(previous_motion_assessment=assessed):
                if assessed:
                    self.fresh_engine()
                terrain, command = self.acknowledged_move(assessed)
                saved, wait = self.authority(), self.scalars(self.motion_wait())
                changed = deepcopy(terrain)
                for x in range(-11, -5):
                    changed.tiles[(x, 4)] = 'stone'
                changed.protected.add((10, 4))
                rejected = self.scene(0, 2, changed)
                frame_bytes = bytes(rejected)
                self.now = max(self.now+2, command.target_ns+80_000_002)
                self.assertEqual(1, self.observe_actual(rejected))
                s = self.status()
                # Establish the original stop and all existing proof values
                # before requiring the new diagnostic (the semantic Red).
                self.assertEqual((17, 0, 0, 0, 0),
                    (s.reason, s.terminal, s.input_state, s.paused, s.current_command_id))
                self.assertEqual(saved, self.authority())
                wait['active'] = 0
                self.assertEqual(wait, self.scalars(self.motion_wait()))
                self.assertEqual(frame_bytes, bytes(rejected))
                self.assertEqual(bytes(command), bytes(self.events()[-1].command))
                self.assertEqual(1, len(self.scene_changes()),
                    'the first genuine non-FLOOR rejection needs a comparison image pair')
                rows, details = self.validated_trace()
                row, detail = rows[0], details[0]
                self.assertEqual((command.id, command.source_capture_id, self.number,
                    command.target_ns, command.deadline_ns, 13, 6, 1, 2, 0, 0, 0, False),
                    tuple(row[key] for key in ('command_id', 'source_capture_id',
                        'observed_capture_id', 'target_ns', 'deadline_ns', 'change_mask',
                        'changed_tiles', 'changed_protected', 'state_before', 'state_after',
                        'goods_before', 'goods_after', 'replan_allowed')))
                self.assertEqual((4, 0, 0, 4, 3), tuple(detail[key] for key in
                    ('validation', 'continuous_count', 'chain_count', 'cell_count', 'omitted_cells')))
                self.assertEqual([(-11, 4), (-10, 4), (-9, 4), (-8, 4)],
                    [(cell['x'], cell['y']) for cell in detail['cells']])
                self.assertTrue(all((cell['tile_before'], cell['tile_after'],
                    cell['protected_before'], cell['protected_after']) == (0, 3, 0, 0)
                    for cell in detail['cells']))

    def test_nonfloor_trace_requires_current_acked_move_and_original_capture_bounds(self):
        for fault in ('unsent', 'inflight', 'unknown_send', 'nonmove', 'prefix', 'unstable',
                      'before_ack', 'before_source', 'invalid_commit'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain = self.fit()
                command = self.next_move()
                if fault in ('inflight', 'unknown_send'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, self.now, 1, 0, 1))
                    if fault == 'unknown_send':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(
                            self.engine, command.id, self.now, -1))
                elif fault == 'nonmove':
                    self.fresh_engine()
                    self.now += 100_000_000
                    self.observe(self.scene())  # PAUSE -> public RESUME.
                    ready, command = self.tick()
                    self.assertEqual((1, 1), (ready, command.kind))
                    self.ack(command)
                elif fault != 'unsent':
                    self.ack(command)
                saved = self.authority()
                before_rows = tuple(bytes(row) for row in self.scene_changes())
                before_details = tuple(bytes(row) for row in self.scene_details())
                ack_ns = self.now
                self.now += 100_000_000
                options = {'prefix': self.prefix-1} if fault == 'prefix' else \
                    {'stable': 0} if fault == 'unstable' else \
                    {'start': ack_ns-1} if fault == 'before_ack' else \
                    {'start': command.source_start_ns-1} if fault == 'before_source' else \
                    {'commit': self.now-1} if fault == 'invalid_commit' else {}
                self.observe_actual(self.scene(0, 2, terrain), **options)
                if fault == 'unsent':
                    # An unbegun MOVE keeps the existing generic rejection;
                    # the ACK-only diagnostic must not replace or duplicate it.
                    self.assertEqual((17, 0, 0), (self.status().reason,
                        self.status().input_state, self.status().inputs))
                    self.assertEqual(saved[0], self.credit())
                    event = self.events()[-1]
                    self.assertEqual((0, 3, 17, bytes(command)),
                        (event.begin_ns, event.outcome, event.reason, bytes(event.command)))
                    self.assertEqual([], self.motion_references())
                    rows, details = self.validated_trace()
                    self.assertEqual((1, 1, 3), (len(rows), rows[0]['change_mask'],
                        details[0]['validation']))
                    self.assertEqual((command.id, command.source_capture_id, self.number),
                        (rows[0]['command_id'], rows[0]['source_capture_id'],
                         rows[0]['observed_capture_id']))
                    continue
                self.assertEqual(before_rows, tuple(bytes(row) for row in self.scene_changes()))
                self.assertEqual(before_details, tuple(bytes(row) for row in self.scene_details()))
                self.assertEqual(saved, self.authority())
                if fault == 'unknown_send':
                    self.assertEqual((1, 11, 4), (self.status().terminal,
                        self.status().reason, self.status().input_state))

    def test_state_trace_preserves_deadlines_goods_priority_and_existing_cleanup(self):
        for mode in ('deadline_equal', 'deadline_late', 'visible', 'mask_zero'):
            with self.subTest(mode=mode):
                self.fresh_engine()
                terrain, command = self.acknowledged_move()
                deadline = self.motion_wait().deadline_ns
                saved = self.authority()
                frame = self.scene(0, 2, terrain)
                if mode == 'visible':
                    frame.goods = 2
                if mode == 'mask_zero':
                    frame = self.scene(2, 2, terrain)
                    frame.signature[:] = bytes([40])*23296
                self.now = deadline + int(mode == 'deadline_late')
                self.assertEqual(1, self.observe_actual(frame))
                if mode == 'deadline_equal':
                    self.assertEqual((17, 0, 0), (self.status().reason,
                        self.status().input_state, self.status().goods))
                    self.assertEqual(saved, self.authority())
                    self.assertEqual(1, len(self.scene_changes()))
                    rows, details = self.validated_trace()
                    self.assertEqual((1, 0, 0, 4), (rows[0]['change_mask'],
                        rows[0]['changed_tiles'], rows[0]['changed_protected'], details[0]['validation']))
                    frozen = (tuple(bytes(row) for row in self.scene_changes()),
                        tuple(bytes(row) for row in self.scene_details()))
                    self.now += 2
                    self.observe_actual(self.scene(0, 2, terrain))
                    self.assertEqual(frozen, (tuple(bytes(row) for row in self.scene_changes()),
                        tuple(bytes(row) for row in self.scene_details())))
                    self.assertEqual((0, 0), self.tick()[:1]+(self.status().paused,))
                    self.assertEqual(saved, self.authority())
                else:
                    self.assertEqual([], self.scene_changes())
                    self.assertEqual([], self.scene_details())
                    self.assertEqual(saved[0], self.credit())
                    self.assertEqual(bytes(command), bytes(self.events()[-1].command))
                    if mode == 'visible':
                        self.assertEqual((1, 1, 0), (self.status().reason,
                            self.status().goods, self.status().paused))
                        self.assertEqual(0, self.tick()[0])
                        self.assertEqual(1, len(self.events()))
                        # Only the existing fresh FLOOR path may reserve PAUSE.
                        self.now += 2
                        self.observe_actual(self.scene(2, 2, terrain))
                        ready, pause = self.tick()
                        self.assertEqual((1, 2), (ready, pause.kind))


if __name__ == '__main__':
    unittest.main()
