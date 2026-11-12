"""TEST087: retain true material changes at an uncertain unsent wait entry.

Public procedural scenes establish diagnostic ownership and unchanged input
authority. They do not recreate missing TEST086 capture355 or fix its stop.
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
from tests import test_native_stationary_wait076 as stationary
from tests import test_native_wait_diagnostics082 as previous

CORE = stationary.CORE
SECOND = fixture.SECOND


class NativeWaitEntry087Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_directory = tempfile.TemporaryDirectory(prefix='test087-wait-entry-')
        directory = Path(cls.source_directory.name)
        origin = Path(os.environ.get('NECRO_TEST087_WAIT_BASELINE_CORE', CORE))
        for path in origin.glob('NG2*'):
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, directory / path.name)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c', '.h')}
        if len(hashes) != 8:
            raise AssertionError('exactly eight C/H identities are required')
        identity = os.environ.get('NECRO_TEST087_WAIT_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps({'source_sha256': hashes,
                'source_directory': str(origin), 'python_sha256': {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (Path(__file__), Path(fixture.__file__),
                              Path(stationary.__file__), Path(previous.__file__),
                              Path(native_walk.__file__))}}, sort_keys=True, indent=2)+'\n')
        prior = stationary.CORE
        try:
            stationary.CORE = directory
            stationary.NativeStationaryWait076Tests.setUpClass.__func__(cls)
        finally:
            stationary.CORE = prior

    @classmethod
    def tearDownClass(cls):
        stationary.NativeStationaryWait076Tests.tearDownClass.__func__(cls)
        cls.source_directory.cleanup()

    setUp = previous.NativeWaitDiagnostics082Tests.setUp
    scene = previous.NativeWaitDiagnostics082Tests.scene
    frame = previous.NativeWaitDiagnostics082Tests.frame
    observe = previous.NativeWaitDiagnostics082Tests.observe
    observe_actual = previous.NativeWaitDiagnostics082Tests.observe_actual
    tick = previous.NativeWaitDiagnostics082Tests.tick
    status = previous.NativeWaitDiagnostics082Tests.status
    events = previous.NativeWaitDiagnostics082Tests.events
    ack = previous.NativeWaitDiagnostics082Tests.ack
    fit = previous.NativeWaitDiagnostics082Tests.fit
    next_move = previous.NativeWaitDiagnostics082Tests.next_move
    publish_procedural_candidate = previous.NativeWaitDiagnostics082Tests.publish_procedural_candidate
    fresh_engine = previous.NativeWaitDiagnostics082Tests.fresh_engine
    recovery = previous.NativeWaitDiagnostics082Tests.recovery
    recovery_samples = previous.NativeWaitDiagnostics082Tests.recovery_samples
    all_public_bytes = previous.NativeWaitDiagnostics082Tests.all_public_bytes
    reject_old_callbacks_without_mutation = previous.NativeWaitDiagnostics082Tests.reject_old_callbacks_without_mutation
    motion_wait = previous.NativeWaitDiagnostics082Tests.motion_wait
    credit = previous.NativeWaitDiagnostics082Tests.credit
    choice = previous.NativeWaitDiagnostics082Tests.choice
    observed_vantage = previous.NativeWaitDiagnostics082Tests.observed_vantage
    observed_result = previous.NativeWaitDiagnostics082Tests.observed_result
    preparation_epoch = previous.NativeWaitDiagnostics082Tests.preparation_epoch
    armed = previous.NativeWaitDiagnostics082Tests.armed
    uncertain = previous.NativeWaitDiagnostics082Tests.uncertain
    motion = previous.NativeWaitDiagnostics082Tests.motion
    assert_waiting = previous.NativeWaitDiagnostics082Tests.assert_waiting
    future_ticket = previous.NativeWaitDiagnostics082Tests.future_ticket
    scene_changes = previous.NativeWaitDiagnostics082Tests.scene_changes
    scene_details = previous.NativeWaitDiagnostics082Tests.scene_details
    motion_references = previous.NativeWaitDiagnostics082Tests.motion_references
    frozen_authority = previous.NativeWaitDiagnostics082Tests.frozen_authority

    def prepare_entry(self, mode='passage', count=1):
        terrain, command = self.armed(mode)
        changed = self.uncertain(terrain)
        for x in range(-10, -10 + count):
            self.assertNotIn((x, 4), terrain.tiles)
            changed.tiles[(x, 4)] = 'floor'
        self.assertEqual((0, 0, 0), self.motion(terrain, changed, command.direction))
        self.assertEqual((2, 0, 0), self.motion(changed, changed, command.direction))
        self.saved_credit = self.credit()
        self.now = command.deadline_ns - 30_000_000
        self.trigger_commit = self.trigger_end = self.now
        self.wait_deadline = min(self.parent_deadline, self.now + 2 * self.original_period)
        return terrain, changed, command

    def entry_row(self, command, observed, points):
        rows, details = self.scene_changes(), self.scene_details()
        self.assertEqual(1, len(rows), 'a true nonzero entry needs its original/trigger raster pair')
        self.assertEqual(1, len(details))
        row, detail = rows[0], details[0]
        self.assertEqual((command.id, command.source_capture_id, observed,
            command.target_ns, command.deadline_ns, 4, len(points), 0, 0),
            (row.command_id, row.source_capture_id, row.observed_capture_id,
             row.target_ns, row.deadline_ns, row.change_mask, row.changed_tiles,
             row.changed_protected, row.replan_allowed))
        self.assertEqual((command.id, command.source_capture_id, observed, 11, 0, 0),
            (detail.command_id, detail.source_capture_id, detail.observed_capture_id,
             detail.validation, detail.continuous_count, detail.chain_count))
        self.assertEqual((min(4, len(points)), max(0, len(points) - 4)),
                         (detail.cell_count, detail.omitted_cells))
        self.assertEqual([(x, y, 0, 1, 0, 0) for x, y in points[:4]],
            [(c.x, c.y, c.tile_before, c.tile_after, c.protected_before, c.protected_after)
             for c in detail.cells[:detail.cell_count]])
        return row, detail

    def test_nonzero_floor_reveal_wait_entry_keeps_original_ticket_credit_and_horizons(self):
        _, changed, command = self.prepare_entry()
        before_wait = bytes(self.motion_wait())
        self.assertEqual(1, self.observe(changed))
        self.trigger_id = self.number
        self.assert_waiting(command)
        self.assertEqual(before_wait, bytes(self.motion_wait()))
        self.assertEqual(self.parent_deadline, self.recovery().records[0].sync_deadline_ns)
        self.assertEqual(self.wait_deadline,
                         min(self.parent_deadline, self.trigger_commit + 2 * self.original_period))
        event = self.events()[-1]
        self.assertEqual((3, 17, 0, 0, 0, 0, 0), (event.outcome, event.reason,
            event.begin_ns, event.observed_capture_id, event.motion, event.dx, event.dy))
        self.assertEqual(bytes(command), bytes(event.command))
        self.entry_row(command, self.trigger_id, [(-10, 4)])
        saved = self.frozen_authority()
        self.now += 100_000_000
        self.assertEqual(1, self.observe(changed))
        self.assert_waiting(command)
        self.assertEqual(saved, self.frozen_authority())
        self.entry_row(command, self.trigger_id, [(-10, 4)])
        self.reject_old_callbacks_without_mutation(command)

    def test_ineligible_or_mask_zero_observations_do_not_create_wait_entry_diagnostics(self):
        for fault in ('mask_zero', 'prefix', 'unstable', 'old_id', 'old_start',
                      'late', 'visible', 'partial', 'route', 'started', 'unknown_send'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, changed, command = self.prepare_entry(count=0 if fault == 'mask_zero' else 1)
                options = {}
                if fault == 'prefix': options['prefix'] = self.prefix - 1
                if fault == 'unstable': options['stable'] = 0
                if fault == 'old_id': options['number'] = self.number
                if fault == 'old_start': options['start'] = command.source_start_ns
                if fault == 'late': self.now = command.deadline_ns + 1
                if fault in ('visible', 'partial'): changed.goods = fault
                if fault == 'route': changed.tiles[fixture.DIRS[command.direction]] = 'dirt'
                if fault in ('started', 'unknown_send'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    if fault == 'unknown_send':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1))
                    self.now += 2
                counts = self.credit()
                self.observe(changed, **options)
                # Other pre-existing failures may have their own diagnostic
                # validation. This entry-only MOTION11 row must remain absent.
                self.assertFalse(any(d.validation == 11 for d in self.scene_details()))
                self.assertEqual(counts, self.credit())
                if fault == 'mask_zero':
                    self.assertEqual([], self.scene_changes())
                    self.assertEqual([], self.scene_details())
                if fault in ('visible', 'partial'):
                    self.assertEqual(1 if fault == 'visible' else 13, self.status().reason)

    def test_entry_payload_records_true_row_major_deltas_and_roundtrips_existing_schema(self):
        for mode in ('passage', 'shop'):
            with self.subTest(mode=mode):
                self.fresh_engine()
                _, changed, command = self.prepare_entry(mode, count=7)
                wait = bytes(self.motion_wait())
                self.assertEqual(1, self.observe(changed)); self.trigger_id = self.number
                self.assert_waiting(command)
                row, detail = self.entry_row(command, self.trigger_id,
                                            [(x, 4) for x in range(-10, -3)])
                self.assertEqual(wait, bytes(self.motion_wait()))
                encoded = {name: getattr(row, name) for name, _ in row._fields_}
                encoded['replan_allowed'] = bool(encoded['replan_allowed'])
                cells = [{name: getattr(c, name) for name, _ in c._fields_}
                         for c in detail.cells[:detail.cell_count]]
                encoded_detail = {name: getattr(detail, name) for name, _ in detail._fields_ if name != 'cells'}
                encoded_detail['cells'] = cells
                self.assertEqual([encoded], native_walk._scene_changes([encoded]))
                self.assertEqual([encoded_detail], native_walk._scene_change_details([encoded_detail]))
                invalid = dict(encoded, change_mask=0)
                with self.assertRaises(native_walk.ProbeError):
                    native_walk._scene_changes([invalid])
                saved = self.frozen_authority()
                self.reject_old_callbacks_without_mutation(command)
                self.assertEqual(saved, self.frozen_authority())


if __name__ == '__main__':
    unittest.main()
