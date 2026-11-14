"""TEST098 public partial-cycle transitions on procedural Scenes and clocks.

Received 297->299 supplies the remote FLOOR->UNKNOWN difference. Received
234->242 is a later stationary pair; its first rejected frame was not saved.
UNKNOWN fixtures below verify bounded waiting, not that missing device cause.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_entry097 as entry


class NativePartialReacquire098Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry.NativePartialEntry097Tests.setUpClass()
        cls.lib = entry.NativePartialEntry097Tests.lib

    @classmethod
    def tearDownClass(cls):
        entry.NativePartialEntry097Tests.tearDownClass()

    def setUp(self):
        self.p = entry.NativePartialEntry097Tests(methodName='runTest')
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.h, self.q = self.p.h, self.p.q

    def pending(self, **kwargs):
        return self.p.pending(extra={(5, 4): 'floor'}, **kwargs)

    def observe(self, terrain, **kwargs):
        return self.p.observe(terrain, **kwargs)

    @staticmethod
    def unknown(terrain):
        value = deepcopy(terrain)
        value.signature = bytes(255 - n for n in value.signature)
        return value

    def unchanged_source(self, original):
        current = self.q.cycle()
        fields = ('job_id', 'capture_id', 'capture_start_ns', 'prefix', 'release_after_ns',
                  'continuation_deadline_ns', 'deadline_ns', 'assessment_ns')
        self.assertEqual(tuple(getattr(original, k) for k in fields),
                         tuple(getattr(current, k) for k in fields))

    def no_move(self):
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind == 4)
        self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves,
                                   self.h.status().restarts))

    def test_actual_opened_entry_remote_floor_loss_keeps_fixed_continuation(self):
        for direction in (1, 2, 3, 4):
            with self.subTest(direction=direction):
                self.setUp()
                terrain, opening = self.pending(direction=direction)
                original = self.q.cycle()
                changed = deepcopy(terrain); changed.tiles[(5, 4)] = 'unknown'
                self.assertEqual(1, self.observe(changed))
                self.assertEqual((0, 0, 0), (self.q.cycle().state,
                    self.q.cycle().status, self.h.status().reason),
                    'an opened entry may ignore remote FLOOR disappearance with complete route and strict zero')
                self.unchanged_source(original)
                changed.tiles.pop((5, 4))  # Native procedural builder encodes UNKNOWN by absence.
                command = self.h.next_move(changed)
                self.assertNotEqual(opening.id, command.id)
                self.assertGreaterEqual(command.not_before_ns - self.h.now, 50_000_000)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    opening.id, command.not_before_ns, 1, 0, 1))

    def test_floor_loss_does_not_expand_unopened_wrong_direction_near_or_protected_authority(self):
        for fault in ('no_ack', 'wrong_ack', 'near', 'protected', 'gold', 'item', 'stone', 'new_floor'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending(opened=fault != 'no_ack',
                    opening_direction=2 if fault == 'wrong_ack' else 3)
                changed = deepcopy(terrain)
                changed.tiles[(5, 4)] = 'unknown'
                if fault == 'near': changed.tiles[(0, -1)] = 'unknown'
                elif fault == 'protected': changed.protected.add((5, 4))
                elif fault in ('gold', 'item', 'stone'): changed.tiles[(5, 4)] = fault
                elif fault == 'new_floor': changed.tiles[(7, 4)] = 'floor'
                self.observe(changed)
                self.assertEqual(7, self.q.cycle().state)
                if fault == 'no_ack':
                    self.assertEqual((1, 1, 0), (self.h.status().inputs,
                        self.h.status().moves, self.h.status().restarts))
                else: self.no_move()

    def test_only_unknown_motion_waits_then_later_independent_zero_releases_once(self):
        terrain, opening = self.pending()
        original = self.q.cycle()
        uncertain = self.unknown(terrain)
        self.assertEqual(1, self.observe(uncertain))
        self.assertEqual((3, 0), (self.q.cycle().state, self.q.cycle().status),
                         'unknown motion with all fixed static guards must remain read-only OBSERVE_MORE')
        self.unchanged_source(original)
        self.no_move()
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
            opening.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.observe(terrain))
        self.assertEqual(0, self.q.cycle().state)
        self.unchanged_source(original)
        command = self.h.next_move(terrain)
        self.h.ack(command)
        self.assertEqual((3, 1), (self.h.status().inputs, self.h.status().moves))
        self.h.observed_result(command, native.translated(terrain, command.direction))
        self.assertEqual((original.job_id + 1, 1),
                         (self.q.cycle().job_id, self.q.cycle().pending))
        self.assertEqual(0, self.h.tick()[0], 'one new input never authorizes a second unassessed input')

    def test_unknown_wait_does_not_clear_known_motion_static_changes_or_missing_open_ack(self):
        for fault in ('known_move', 'route', 'protected', 'gold', 'item', 'material', 'goods', 'no_ack'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending(opened=fault != 'no_ack')
                changed = self.unknown(terrain)
                if fault == 'known_move': changed.signature = native.translated(terrain, 3).signature
                elif fault == 'route': changed.tiles[(0, -1)] = 'dirt'
                elif fault == 'protected': changed.protected.add((5, 4))
                elif fault == 'gold': changed.tiles[(-1, -1)] = 'floor'
                elif fault == 'item': changed.tiles[(5, 4)] = 'item'
                elif fault == 'material': changed.tiles[(5, 4)] = 'stone'
                elif fault == 'goods': changed.goods = 'unknown'
                self.observe(changed)
                self.assertEqual(7, self.q.cycle().state)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_unknown_wait_keeps_original_deadline_and_cancel_owner_lock_stop(self):
        for fault in ('deadline', 'cancel', 'foreground', 'owner', 'locked'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending()
                original = self.q.cycle()
                self.observe(self.unknown(terrain))
                self.assertEqual(3, self.q.cycle().state)
                if fault == 'deadline':
                    self.h.now = original.continuation_deadline_ns + 1
                    self.h.tick()
                    self.assertEqual((7, 2), (self.q.cycle().state, self.q.cycle().status))
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                else: self.h.tick(front=int(fault != 'foreground'),
                    owner=int(fault != 'owner'), locked=int(fault == 'locked'))
                self.observe(terrain)
                self.assertNotEqual(0, self.q.cycle().state)
                self.no_move()

    def test_wrong_prefix_unstable_pre_release_and_old_id_never_supply_wait_proof(self):
        for fault in ('prefix', 'unstable', 'pre_release', 'same_id'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending()
                original = self.q.cycle()
                self.observe(self.unknown(terrain))
                self.assertEqual(3, self.q.cycle().state)
                kwargs = {'prefix': self.h.prefix + 1} if fault == 'prefix' else (
                    {'stable': 0} if fault == 'unstable' else (
                    {'start': original.release_after_ns - 1} if fault == 'pre_release' else
                    {'number': original.capture_id}))
                self.observe(terrain, **kwargs)
                self.assertEqual(3, self.q.cycle().state)
                self.unchanged_source(original)
                self.no_move()

    def test_new_full_floor_handoff_is_not_limited_to_empty_framing_and_retires_old_job(self):
        for state in (2, 0, 1):
            with self.subTest(state=state):
                self.setUp()
                terrain, _ = self.pending()
                original = self.q.cycle()
                full = deepcopy(terrain); full.goods = 'visible'
                self.h.now += 10_000_000
                self.h.observe(self.h.scene(state, 2, full, beat=True))
                current = self.q.cycle()
                if state == 2:
                    self.assertEqual((original.job_id + 1, 1, 1, 0, 1),
                        (current.job_id, current.state, current.pending, current.partial, current.full_seen),
                        'a fresh FULL observation starts its own classification instead of failing the old partial job')
                    self.assertGreater(current.capture_id, original.capture_id)
                    self.assertEqual(self.h.prefix, current.prefix)
                    self.assertEqual(0, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        original.job_id, original.capture_id, original.prefix, self.h.now + 1))
                else:
                    self.assertEqual((original.job_id, original.capture_id, 0),
                                     (current.job_id, current.capture_id, current.pending))
                self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves,
                                           self.h.status().restarts))

    def test_first_rejected_cycle_observation_logs_immutable_source_and_no_permission(self):
        terrain, opening = self.pending()
        original = self.q.cycle()
        self.observe(self.unknown(terrain))
        first_id = self.h.number
        rows = self.h.scene_changes()
        self.assertTrue(rows, 'even a motion-only rejection needs its first source/proof IDs retained')
        row, detail = rows[-1], self.h.scene_details()[-1]
        self.assertEqual((opening.id, original.capture_id, first_id, 0, 0),
            (row.command_id, row.source_capture_id, row.observed_capture_id,
             row.change_mask, row.replan_allowed))
        self.assertEqual((11, 0, 0, 0, 0), (detail.validation, detail.continuous_count,
            detail.chain_count, detail.cell_count, detail.omitted_cells))
        frozen = bytes(row), bytes(detail)
        self.observe(self.unknown(terrain))
        self.assertEqual(frozen, (bytes(self.h.scene_changes()[-1]), bytes(self.h.scene_details()[-1])))
        self.no_move()

    def test_material_rejection_diagnostic_uses_cycle_anchor_not_pre_door_ticket(self):
        terrain, opening = self.pending()
        original = self.q.cycle()
        changed = deepcopy(terrain); changed.tiles[(5, 4)] = 'stone'
        self.observe(changed)
        self.assertTrue(self.h.scene_changes(), 'the first rejected comparison must retain both source IDs')
        row, detail = self.h.scene_changes()[-1], self.h.scene_details()[-1]
        self.assertEqual((opening.id, original.capture_id, self.h.number, 1, 0),
            (row.command_id, row.source_capture_id, row.observed_capture_id,
             row.changed_tiles, row.changed_protected))
        self.assertEqual((5, 4, 1, 3, 0, 0), tuple(getattr(detail.cells[0], name) for name in
            ('x', 'y', 'tile_before', 'tile_after', 'protected_before', 'protected_after')))
        self.assertEqual((0, 0, 0, 1), (row.replan_allowed, detail.continuous_count,
                                      detail.chain_count, detail.cell_count))
        self.assertEqual(7, self.q.cycle().state)
        self.no_move()
        # An initial PARTIAL may have no qualified route at all. Identical
        # static Scenes then fail ROUTE, not MOTION; the old mask schema must
        # not receive a zero-mask ROUTE row or consume the first-record flag.
        self.setUp()
        source = self.q.goods(partial=True)
        def safe(value):
            value.partial_safe_no_positive = value.partial_count = 1
            value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
            value.partial[0].icon_score_exact = 1
        self.q.assess(0, 1, safe)
        self.h.now += 10_000_000
        self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(source))))
        self.assertEqual(7, self.q.cycle().state)
        self.assertEqual([], self.h.scene_changes(),
                         'a static-identical ROUTE rejection is not a mask-zero MOTION diagnostic')


if __name__ == '__main__':
    unittest.main()
