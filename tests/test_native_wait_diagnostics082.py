"""TEST082: truthful diagnostics for rejected independent stationary proofs.

Procedural public-C scenes exercise existing failures; no omitted phone frame
or private Controller state is reconstructed or injected.
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
from tests import test_native_stationary_wait076 as stationary

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativeWaitDiagnostics082Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_directory = tempfile.TemporaryDirectory(prefix='test082-wait-source-')
        directory = Path(cls.source_directory.name)
        origin = Path(os.environ.get('NECRO_TEST082_BASELINE_CORE', CORE))
        for path in origin.glob('NG2*'):
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, directory / path.name)
        identity = os.environ.get('NECRO_TEST082_DIAGNOSTIC_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps({
                'source_directory': str(origin),
                'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c', '.h')},
                'python_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (Path(__file__), Path(fixture.__file__), Path(mechanics.__file__),
                              Path(stationary.__file__), Path(native_walk.__file__))}},
                sort_keys=True, indent=2)+'\n')
        previous = stationary.CORE
        try:
            stationary.CORE = directory
            stationary.NativeStationaryWait076Tests.setUpClass.__func__(cls)
        finally:
            stationary.CORE = previous

    @classmethod
    def tearDownClass(cls):
        stationary.NativeStationaryWait076Tests.tearDownClass.__func__(cls)
        cls.source_directory.cleanup()

    setUp = stationary.NativeStationaryWait076Tests.setUp
    scene = stationary.NativeStationaryWait076Tests.scene
    frame = stationary.NativeStationaryWait076Tests.frame
    observe = stationary.NativeStationaryWait076Tests.observe
    observe_actual = stationary.NativeStationaryWait076Tests.observe_actual
    tick = stationary.NativeStationaryWait076Tests.tick
    status = stationary.NativeStationaryWait076Tests.status
    events = stationary.NativeStationaryWait076Tests.events
    ack = stationary.NativeStationaryWait076Tests.ack
    fit = stationary.NativeStationaryWait076Tests.fit
    next_move = stationary.NativeStationaryWait076Tests.next_move
    publish_procedural_candidate = stationary.NativeStationaryWait076Tests.publish_procedural_candidate
    fresh_engine = stationary.NativeStationaryWait076Tests.fresh_engine
    recovery = stationary.NativeStationaryWait076Tests.recovery
    recovery_samples = stationary.NativeStationaryWait076Tests.recovery_samples
    all_public_bytes = stationary.NativeStationaryWait076Tests.all_public_bytes
    reject_old_callbacks_without_mutation = stationary.NativeStationaryWait076Tests.reject_old_callbacks_without_mutation
    motion_wait = stationary.NativeStationaryWait076Tests.motion_wait
    credit = stationary.NativeStationaryWait076Tests.credit
    choice = stationary.NativeStationaryWait076Tests.choice
    observed_vantage = stationary.NativeStationaryWait076Tests.observed_vantage
    observed_result = stationary.NativeStationaryWait076Tests.observed_result
    preparation_epoch = stationary.NativeStationaryWait076Tests.preparation_epoch
    armed = stationary.NativeStationaryWait076Tests.armed
    uncertain = stationary.NativeStationaryWait076Tests.uncertain
    motion = stationary.NativeStationaryWait076Tests.motion
    start_wait = stationary.NativeStationaryWait076Tests.start_wait
    assert_waiting = stationary.NativeStationaryWait076Tests.assert_waiting
    future_ticket = stationary.NativeStationaryWait076Tests.future_ticket
    scene_changes = fixture.NativeControllerTests.scene_changes
    scene_details = fixture.NativeControllerTests.scene_details
    motion_references = fixture.NativeControllerTests.motion_references

    def frozen_authority(self):
        return (self.credit(), tuple(bytes(e) for e in self.events()),
            bytes(self.recovery()), bytes(self.motion_wait()),
            tuple(bytes(r) for r in self.motion_references()))

    def trace(self, old, observed, validation, changed_tiles, entry=None):
        rows, details = self.scene_changes(), self.scene_details()
        expected = 1 if entry is None else 2
        self.assertEqual(expected, len(rows), 'each true entry/rejection retains its own diagnostic row')
        self.assertEqual(expected, len(details))
        if entry is not None:
            self.assertEqual(entry, (bytes(rows[0]), bytes(details[0])),
                             'the later rejection cannot overwrite the original entry evidence')
        row, detail = rows[-1], details[-1]
        self.assertEqual((old.id, old.source_capture_id, observed, old.target_ns, old.deadline_ns,
            4, changed_tiles, 0, 0), (row.command_id, row.source_capture_id,
            row.observed_capture_id, row.target_ns, row.deadline_ns, row.change_mask,
            row.changed_tiles, row.changed_protected, row.replan_allowed))
        self.assertEqual((old.id, old.source_capture_id, observed, validation, 0),
            (detail.command_id, detail.source_capture_id, detail.observed_capture_id,
             detail.validation, detail.chain_count))
        encoded = {name: getattr(row, name) for name, _ in row._fields_}
        encoded['replan_allowed'] = bool(encoded['replan_allowed'])
        cells = [{name: getattr(cell, name) for name, _ in cell._fields_}
            for cell in detail.cells[:detail.cell_count]]
        encoded_detail = {name: getattr(detail, name) for name, _ in detail._fields_ if name != 'cells'}
        encoded_detail['cells'] = cells
        self.assertEqual([encoded], native_walk._scene_changes([encoded]))
        self.assertEqual([encoded_detail], native_walk._scene_change_details([encoded_detail]))
        return detail, cells

    def test_rejected_independent_route_retains_true_source_diff_without_authority_change(self):
        terrain, _, old = self.start_wait('passage')
        saved = self.frozen_authority()
        changed = deepcopy(terrain)
        changed.tiles[fixture.DIRS[old.direction]] = 'dirt'
        for x in range(-11, -5):
            changed.tiles[(x, 4)] = 'stone' if terrain.tiles.get((x, 4)) != 'stone' else 'dirt'
        self.now += 100_000_000; self.observe(changed)
        self.assertEqual((17, 0, 0, 1, 1), (self.status().reason, self.status().terminal,
            self.status().input_state, self.status().inputs, self.status().moves))
        self.assertEqual(saved, self.frozen_authority())
        detail, cells = self.trace(old, self.number, 10, 7)
        self.assertEqual((4, 3), (detail.cell_count, detail.omitted_cells))
        self.assertEqual([fixture.DIRS[old.direction], (-11, 4), (-10, 4), (-9, 4)],
            [(cell['x'], cell['y']) for cell in cells])
        self.reject_old_callbacks_without_mutation(old)

    def test_ready_unknown_motion_records_only_real_nonzero_scene_diff(self):
        terrain, changed, old = self.start_wait('passage', remote=True)
        self.trace(old, self.trigger_id, 11, 1)
        entry = (bytes(self.scene_changes()[0]), bytes(self.scene_details()[0]))
        self.now += 100_000_000; self.observe(changed)
        self.assert_waiting(old)
        self.assertEqual(entry, (bytes(self.scene_changes()[0]), bytes(self.scene_details()[0])))
        self.assertEqual((1, 1), (len(self.scene_changes()), len(self.scene_details())),
                         'a repeated OBSERVE UNKNOWN does not append another entry or rejection')
        self.now += 100_000_000; self.observe(terrain)  # Independent strict zero; do not issue a ticket.
        self.assertEqual((0, 0), (self.status().reason, self.status().input_state))
        saved = self.frozen_authority()
        self.now += 2; self.observe(changed)
        self.assertEqual((17, 0, 1, 1), (self.status().reason, self.status().input_state,
            self.status().inputs, self.status().moves))
        self.assertEqual(saved, self.frozen_authority())
        detail, cells = self.trace(old, self.number, 11, 1, entry=entry)
        self.assertEqual((1, 0), (detail.cell_count, detail.omitted_cells))
        self.assertEqual([(-10, 4)], [(cell['x'], cell['y']) for cell in cells])

    def test_mask_zero_metadata_issued_clock_and_goods_do_not_create_false_trace(self):
        for fault in ('mask_zero', 'prefix', 'unstable', 'overlap', 'issued',
                      'deadline_equal', 'deadline_late', 'visible', 'partial', 'unknown_send'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                if fault == 'unknown_send':
                    terrain, old = self.armed('shop')
                    self.now = old.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))
                    self.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, old.id, self.now, -1))
                    changed = self.uncertain(terrain, True)
                    saved = self.frozen_authority(); self.now += 2; self.observe(changed)
                    self.assertEqual((11, 4), (self.status().reason, self.status().input_state))
                    self.assertEqual(saved, self.frozen_authority())
                    self.assertEqual([], self.scene_changes()); continue
                terrain, changed, old = self.start_wait('passage', remote=fault!='mask_zero')
                if fault == 'mask_zero':
                    self.assertEqual([], self.scene_changes())
                    self.assertEqual([], self.scene_details())
                else:
                    self.trace(old, self.trigger_id, 11, 1)
                original_journal = (tuple(bytes(row) for row in self.scene_changes()),
                                    tuple(bytes(row) for row in self.scene_details()))
                if fault in ('mask_zero', 'issued'):
                    if fault == 'issued': self.future_ticket(terrain)
                    else:
                        self.now += 100_000_000; self.observe(terrain)
                elif fault.startswith('deadline'):
                    self.now = self.wait_deadline + int(fault == 'deadline_late') - 2
                saved = self.frozen_authority(); self.now += 2
                options = {'prefix': self.prefix-1} if fault=='prefix' else \
                    {'stable': 0} if fault=='unstable' else \
                    {'start': self.trigger_end-1} if fault=='overlap' else {}
                if fault in ('visible', 'partial'):
                    changed = deepcopy(changed); changed.goods = fault
                self.observe(changed, **options)
                self.assertEqual(original_journal,
                    (tuple(bytes(row) for row in self.scene_changes()),
                     tuple(bytes(row) for row in self.scene_details())),
                    'the existing entry is retained without a false later failure/entry row')
                if fault == 'mask_zero':
                    self.assertEqual([], self.scene_changes())
                    self.assertEqual([], self.scene_details())
                if fault in ('prefix', 'unstable'):
                    self.assertEqual(0, self.status().reason)
                else:
                    expected = 8 if fault.startswith('deadline') else \
                        1 if fault=='visible' else 13 if fault=='partial' else 17
                    self.assertEqual(expected, self.status().reason)
                # Goods latching changes no input credit; withdrawing a new
                # ISSUED ticket may update its own event but never the old one.
                self.assertEqual(saved[0], self.credit())
                self.assertEqual(bytes(old), bytes(next(e.command for e in self.events() if e.command.id==old.id)))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                    max(self.now, old.deadline_ns+1), 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
