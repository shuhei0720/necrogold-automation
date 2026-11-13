"""TEST094 cycle controller: synthetic clocks/Scenes, not iPhone acceptance.

The initial Red intentionally falls back to the legacy constructor so that
the assertion demonstrates its irreversible goods terminal, not a missing
symbol/compile failure. The cycle constructor replaces it in Green.
"""
import ctypes as C
import unittest

from tests import test_native_controller as native
SECOND = native.SECOND
from tests.test_native_ring094 import Result


class Cycle(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ("abi_version", "struct_size")] + [
        (name, C.c_int32) for name in ("state", "outcome", "status", "coverage", "partial", "pending",
            "completed_shops", "candidate_latched", "full_seen", "reserved")] + [
        (name, C.c_uint64) for name in ("level_id", "job_id", "capture_id", "capture_start_ns", "prefix",
            "deadline_ns", "hold_started_ns", "worker_started_ns", "assessment_ns", "durable_ns",
            "pause_source_capture_id", "pause_capture_id", "restart_command_id", "next_floor_capture_id",
            "intent_ns", "outcome_ns", "release_after_ns", "continuation_deadline_ns",
            "queued_capture_id", "queued_capture_start_ns", "queued_prefix")]


class NativeCycle094Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native.NativeControllerTests.setUpClass()
        cls.lib = native.NativeControllerTests.lib
        cls.lib.ng2_controller_cycle_status.argtypes = [C.c_void_p, C.POINTER(Cycle)]
        for name in ("worker_begin", "durable"):
            getattr(cls.lib, "ng2_controller_cycle_" + name).argtypes = [C.c_void_p] + [C.c_uint64] * 4
        cls.lib.ng2_controller_cycle_assess.argtypes = [C.c_void_p] + [C.c_uint64] * 4 + [C.POINTER(Result)]
        cls.lib.ng2_controller_cycle_intent_commit.argtypes = [C.c_void_p] + [C.c_uint64] * 5
        cls.lib.ng2_controller_cycle_outcome_commit.argtypes = [C.c_void_p] + [C.c_uint64] * 4
        cls.lib.ng2_controller_cycle_storage_failed.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64]

    @classmethod
    def tearDownClass(cls):
        native.NativeControllerTests.tearDownClass()

    def setUp(self):
        self.h = native.NativeControllerTests(methodName="runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        create = getattr(self.lib, "ng2_controller_create_cycle", self.lib.ng2_controller_create)
        create.argtypes = [C.c_uint64]
        create.restype = C.c_void_p
        self.h.engine = create(SECOND)
        self.h.addCleanup(self.lib.ng2_controller_destroy, self.h.engine)

    def cycle(self):
        value = Cycle()
        self.lib.ng2_controller_cycle_status(self.h.engine, C.byref(value))
        return value

    def goods(self, partial=False):
        h = self.h
        value = h.scene(state=2, gold=2)
        value.goods = 1 if partial else 2
        value.tiles[3 * 23 + 8] = 2
        self.assertEqual(1, h.observe(value))
        return value

    def assess(self, outcome=0, coverage=0, mutate=None):
        h = self.h
        source = self.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now))
        value = Result(abi=1, size=C.sizeof(Result), outcome=outcome, coverage=coverage,
                       selected_row=-1, selected_partial=-1,
                       started_ns=h.now, finished_ns=h.now + 1)
        if outcome == 3:
            # A procedural worker certificate exercises the controller trust
            # boundary; pixel/bank accuracy is tested by native_ring_bank094.
            value.row_count = 1
            value.selected_row = 0
            value.selected_partial = -1
            row = value.rows[0]
            row.left, row.sy, row.word_slot, row.outcome = 300, 90, -1, 3
            witness = value.certificate
            witness.layout_version = witness.policy_version = witness.accepted_rows = 1
            witness.board_mode = 1
            witness.scene_state, witness.scene_goods, witness.actual_gold_cells = 2, 2, 1
            witness.observed_items = witness.observed_prices = witness.non_target_items = 3
            witness.row[:] = (300, 90)
            witness.strip_box[:] = (246, 114, 180, 65)
            witness.merchant_box[:] = (326, 80, 20, 20)
            witness.merchant_score = witness.merchant_coverage = 1
            for side in range(2):
                witness.sign_boxes[side][:] = (289 + 72 * side, 84, 22, 7)
                witness.board_boxes[side][:] = (288 + 72 * side, 80, 24, 20)
                witness.board_counts[side] = 200
                witness.sign_iou[side] = witness.sign_coverage[side] = 1
                endcap = witness.endcaps[side]
                endcap.box[:] = (252 + 144 * side, 126, 25, 25)
                endcap.r, endcap.g, endcap.b, endcap.spread, endcap.count = 25, 15, 14, 1, 625
                endcap.floor_full = endcap.floor_upper = endcap.floor_lower = 1
            for index, slot in enumerate(row.slots):
                slot.cx, slot.sy, slot.slot = 300 + 36 * index, 90, index
                slot.icon_score = slot.icon_upper_bound = .1
                slot.icon_score_exact = 1
                slot.outcome, slot.kind, slot.non_target_id = 3, 1, index + 1
                slot.non_target_icon_score = slot.non_target_name_iou = slot.non_target_name_coverage = 1
                slot.non_target_icon_box[:] = (slot.cx - 6, 124, 13, 13)
                slot.non_target_name_box[:] = (slot.cx - 6, 145, 13, 7)
                witness.item_boxes[index][:] = slot.non_target_icon_box[:]
                witness.name_boxes[index][:] = slot.non_target_name_box[:]
                witness.price_boxes[index][:] = (slot.cx - 4, 159, 9, 7)
        if mutate:
            mutate(value)
        h.now += 1
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now, C.byref(value)))
        return value

    def pause_observed(self):
        h = self.h
        ready, pause = h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        h.ack(pause)
        h.now += 210_000_000
        self.assertEqual(1, h.observe(h.scene(state=1)))
        self.assertEqual(0, h.status().terminal)
        return pause

    def durable(self):
        h = self.h
        source = self.cycle()
        return self.lib.ng2_controller_cycle_durable(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now)

    def negative_restart(self):
        self.goods()
        self.assess(3, 2)
        self.pause_observed()
        self.assertEqual(1, self.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        return restart

    def intent(self, restart):
        return self.lib.ng2_controller_cycle_intent_commit(self.h.engine, self.cycle().job_id,
            restart.id, restart.source_capture_id, self.h.prefix, self.h.now)

    def next_floor(self, restart, changed=True):
        h = self.h
        h.ack(restart)
        h.now += 210_000_000
        floor = h.scene(state=2, gold=2, terrain=native.textured(), beat=True)
        floor.fingerprint[:] = bytes([80 if changed else 0] * 48)
        self.assertEqual(1, h.observe(floor))
        return floor

    def test_goods_hold_keeps_cycle_open_after_real_pause_observation(self):
        h = self.h
        goods = h.scene(state=2, gold=2)
        goods.goods = 2
        self.assertEqual(1, h.observe(goods))
        ready, pause = h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        h.ack(pause)
        h.now += 210_000_000
        self.assertEqual(1, h.observe(h.scene(state=1)))
        self.assertEqual(1, h.status().paused)
        self.assertEqual(0, h.status().terminal,
                         "cycle goods hold must await bound assessment; legacy goods finish seals the run")
        self.assertEqual(0, h.tick()[0], "pending classification cannot restart")

    def test_negative_authority_needs_durable_checkpoint_and_new_pause_source(self):
        self.goods()
        self.assess(outcome=3, coverage=2)
        self.assertEqual(0, self.durable(), "RGBA result cannot replace actual PAUSE confirmation")
        pause = self.pause_observed()
        self.assertEqual(0, self.h.tick()[0], "undurable negative cannot restart")
        self.assertEqual(1, self.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind),
                         "a certified durable negative continues inside the same controller")
        self.assertNotEqual(pause.source_capture_id, restart.source_capture_id)

    def test_restart_begin_requires_exact_durable_intent_and_fresh_pause(self):
        restart = self.negative_restart()
        h = self.h
        state, snapshot = bytes(h.status()), bytes(self.cycle())
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, restart.id, h.now, 1, 0, 1))
        self.assertEqual((state, snapshot), (bytes(h.status()), bytes(self.cycle())))
        for change in ("command", "source", "prefix", "job"):
            values = [self.cycle().job_id, restart.id, restart.source_capture_id, h.prefix, h.now]
            values[{"job": 0, "command": 1, "source": 2, "prefix": 3}[change]] += 1
            self.assertEqual(0, self.lib.ng2_controller_cycle_intent_commit(h.engine, *values))
            self.assertEqual((state, snapshot), (bytes(h.status()), bytes(self.cycle())))
        self.assertEqual(1, self.intent(restart))
        self.assertEqual(0, self.intent(restart), "committed intent is one-shot")
        self.next_floor(restart)
        self.assertEqual(1, h.status().restarts)

    def test_ack_and_real_changed_floor_wait_for_linked_outcome_durability(self):
        restart = self.negative_restart()
        h = self.h
        self.assertEqual(1, self.intent(restart))
        before = self.cycle()
        self.assertEqual(0, self.lib.ng2_controller_cycle_outcome_commit(h.engine, before.job_id, 1, h.prefix, h.now))
        floor = self.next_floor(restart, changed=False)
        self.assertEqual((0, 0, 1), (h.status().restarts, self.cycle().next_floor_capture_id, self.cycle().level_id))
        self.assertEqual(0, h.tick()[0])
        h.now += 30_000_000
        floor.fingerprint[:] = bytes([80] * 48)
        self.assertEqual(1, h.observe(floor))
        proof = self.cycle()
        self.assertEqual((1, 1), (h.status().restarts, proof.level_id))
        self.assertEqual(0, h.tick()[0], "new run waits for durable outcome, without images RPC")
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(h.engine,
            proof.job_id, proof.next_floor_capture_id, h.prefix, h.now))
        self.assertEqual((2, 0), (self.cycle().level_id, self.cycle().state))
        self.assertEqual(0, h.status().terminal)

    def test_target_candidate_and_unknown_keep_pause_without_restart(self):
        for outcome in (0, 1, 2):
            with self.subTest(outcome=outcome):
                self.setUp()
                self.goods(partial=outcome != 0)
                self.assess(outcome)
                self.pause_observed()
                self.assertEqual(1, self.durable())
                self.assertEqual(0, self.h.tick()[0])
                self.assertEqual((1, 1, 0), (self.h.status().terminal, self.h.status().paused, self.h.status().restarts))
                self.assertEqual(outcome, self.cycle().outcome)
                self.assertEqual(int(outcome != 0), self.cycle().candidate_latched)

    def test_deadline_and_cancelled_worker_results_are_inert(self):
        self.goods()
        h = self.h
        source = self.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now))
        h.now = self.cycle().deadline_ns + 1
        self.assertEqual((1, 2), (h.tick()[0], h.events()[-1].command.kind))
        late = Result(abi=1, size=C.sizeof(Result), outcome=3, coverage=2,
                      started_ns=source.capture_start_ns, finished_ns=h.now)
        before = bytes(self.cycle())
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now, C.byref(late)))
        self.assertEqual(before, bytes(self.cycle()))
        self.assertEqual((0, 2), (self.cycle().outcome, self.cycle().status))
        self.lib.ng2_controller_cancel(h.engine, h.now, 2)
        state, snapshot = bytes(h.status()), bytes(self.cycle())
        self.assertEqual(0, self.lib.ng2_controller_cycle_durable(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now + 1))
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now + 1, C.byref(late)))
        self.assertEqual((state, snapshot), (bytes(h.status()), bytes(self.cycle())))

    def test_storage_failure_pauses_then_stops_without_fabricating_durability(self):
        self.goods()
        source = self.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_storage_failed(self.h.engine, source.job_id, self.h.now))
        self.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual((1, 1, 0, 0), (self.h.status().terminal, self.h.status().paused,
            self.h.status().restarts, self.cycle().durable_ns))

    def test_storage_failure_revokes_an_already_reserved_restart_before_begin(self):
        restart = self.negative_restart()
        self.assertEqual(1, self.intent(restart))
        h = self.h
        self.assertEqual(1, self.lib.ng2_controller_cycle_storage_failed(h.engine, self.cycle().job_id, h.now))
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, restart.id, h.now, 1, 0, 1),
                         "failed durable authority must retire the exact unsent RESTART")

    def test_unknown_synth_freeze_survives_late_classifier_and_writer(self):
        self.goods()
        self.assess(3, 2)
        ready, pause = self.h.tick()
        self.assertEqual(1, ready)
        h = self.h
        self.assertEqual(1, self.lib.ng2_controller_begin(h.engine, pause.id, h.now, 1, 0, 1))
        h.now += 50_000_000
        self.assertEqual(1, self.lib.ng2_controller_complete(h.engine, pause.id, h.now, -1))
        state, snapshot = bytes(h.status()), bytes(self.cycle())
        self.assertEqual((1, 4), (h.status().terminal, h.status().input_state))
        self.assertEqual(0, self.durable())
        self.assertEqual(0, h.tick()[0])
        self.assertEqual((state, snapshot), (bytes(h.status()), bytes(self.cycle())))

    def test_two_shops_continue_and_fourth_shop_holds_with_cumulative_budget(self):
        h = self.h
        started = h.status().started_ns
        walk_started = 0
        for number in range(1, 5):
            self.goods()
            walk_started = walk_started or h.status().walk_started_ns
            self.assess(3, 2)
            self.pause_observed()
            self.assertEqual(1, self.durable())
            self.assertEqual(number, self.cycle().completed_shops)
            if number == 4:
                self.assertEqual(0, h.tick()[0])
                self.assertEqual((1, 1, 3), (h.status().terminal, h.status().paused, h.status().restarts))
                break
            ready, restart = h.tick()
            self.assertEqual((1, 3), (ready, restart.kind))
            self.assertEqual(1, self.intent(restart))
            floor = self.next_floor(restart)
            # Each procedural pair has distinct fingerprint bytes; these are
            # control fixtures, not recorded future game images.
            proof = self.cycle()
            self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(h.engine,
                proof.job_id, proof.next_floor_capture_id, h.prefix, h.now))
            self.assertEqual((started, walk_started, number),
                (h.status().started_ns, h.status().walk_started_ns, h.status().restarts))
            h.now += 20_000_000

    def partial_continuation(self):
        h = self.h
        terrain, retired = h.continuous_walk(moves=1, direction=1)
        terrain.goods = "partial"
        h.now += 2
        self.assertEqual(1, h.observe(h.scene(state=2, gold=2, terrain=terrain, beat=True)))
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, retired.id, retired.not_before_ns, 1, 0, 1))
        self.assertEqual(0, h.tick()[0], "partial pending classifier freezes MOVE without unnecessary PAUSE")
        def safe(value):
            value.partial_safe_no_positive = value.partial_count = 1
            value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
            value.partial[0].icon_score_exact = 1
        self.assess(0, 1, safe)
        self.assertEqual(3, self.cycle().state)
        h.now += 10_000_000
        self.assertEqual(1, h.observe(h.scene(state=2, gold=2, terrain=terrain, beat=True)))
        self.assertEqual(0, self.cycle().state)
        return terrain, retired

    def test_partial_observe_more_uses_one_new_safe_move_without_reviving_old_ticket(self):
        h = self.h
        terrain, retired = self.partial_continuation()
        proof = self.cycle()
        h.now += 10_000_000
        h.observe(h.scene(state=2, gold=2, terrain=terrain, beat=True))
        self.assertEqual((proof.job_id, proof.continuation_deadline_ns),
                         (self.cycle().job_id, self.cycle().continuation_deadline_ns))
        command = h.next_move(terrain)
        self.assertNotEqual(retired.id, command.id)
        self.assertGreater(command.not_before_ns - h.now, 49_999_999)
        h.ack(command)
        h.observed_result(command, native.translated(terrain, command.direction))
        self.assertEqual((2, 2), (h.status().inputs, h.status().moves))
        self.assertGreater(self.cycle().job_id, proof.job_id)
        self.assertEqual((1, command.id), (self.cycle().pending, self.cycle().prefix))
        self.assertEqual(0, h.tick()[0], "next prefix requires its own assessment")

    def test_partial_credit_unproven_change_retires_new_move_and_holds(self):
        h = self.h
        terrain, _ = self.partial_continuation()
        command = h.next_move(terrain)
        changed = native.Scene.from_buffer_copy(bytes(h._last_fixture_scene))
        changed.protected_cells[5 * 23 + 10] = 1
        h.now += 2
        h.observe(changed)
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, command.id, command.not_before_ns, 1, 0, 1))
        self.assertEqual((7, 0), (self.cycle().state, self.cycle().outcome))
        self.assertEqual((1, 1), (h.status().inputs, h.status().moves))

    def test_partial_candidate_survives_queued_full_goods_unknown_or_negative(self):
        self.goods(partial=True)
        h = self.h
        source = self.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(h.engine,
            source.job_id, source.capture_id, source.prefix, h.now))
        h.now += 10_000_000
        self.goods()
        queued = self.cycle()
        self.assertGreater(queued.queued_capture_id, source.capture_id)
        self.assertEqual((1, 2), (h.tick()[0], h.events()[-1].command.kind))
        result = Result(abi=1, size=C.sizeof(Result), outcome=1, selected_row=-1, selected_partial=-1,
                        started_ns=source.worker_started_ns, finished_ns=h.now)
        # worker_started is captured after admission, not the pre-admission getter.
        result.started_ns = self.cycle().worker_started_ns
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now, C.byref(result)))
        before = bytes(self.cycle())
        result.outcome, result.coverage = 3, 2
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(h.engine, source.job_id,
            source.capture_id, source.prefix, h.now, C.byref(result)))
        self.assertEqual(before, bytes(self.cycle()))
        self.assertEqual((1, 1), (self.cycle().outcome, self.cycle().candidate_latched))

    def test_negative_missing_or_conflicting_witness_is_held(self):
        def partial_candidate(value):
            value.partial_count = 1
            value.partial[0].outcome = 1
            value.partial[0].icon_score = value.partial[0].icon_upper_bound = .9
            value.partial[0].icon_score_exact = 1
        faults = {
            "incomplete": lambda v: setattr(v, "coverage", 1),
            "extra_item": lambda v: setattr(v.certificate, "observed_items", 4),
            "unmatched_item": lambda v: setattr(v.certificate, "unmatched_items", 1),
            "two_rows": lambda v: setattr(v.certificate, "accepted_rows", 2),
            "wrong_policy": lambda v: setattr(v.certificate, "policy_version", 0),
            "unknown_board_mode": lambda v: setattr(v.certificate, "board_mode", 0),
            "frame_without_edges": lambda v: setattr(v.certificate, "board_mode", 2),
            "name_missing": lambda v: setattr(v.rows[0].slots[1], "non_target_name_iou", 0),
            "unknown_id": lambda v: setattr(v.rows[0].slots[1], "non_target_id", 0),
            "conflict": lambda v: setattr(v.rows[0].slots[1], "non_target_conflict", 1),
            "black_endcap": lambda v: setattr(v.certificate.endcaps[0], "black_count", 63),
            "false_floor": lambda v: setattr(v.certificate.endcaps[0], "r", 0),
            "partial_candidate": partial_candidate,
            "no_scene_gold": lambda v: setattr(v.certificate, "actual_gold_cells", 0),
        }
        for fault, mutate in faults.items():
            with self.subTest(fault=fault):
                self.setUp()
                self.goods()
                self.assess(3, 2, mutate)
                self.assertEqual((0, 3), (self.cycle().outcome, self.cycle().status))
                self.pause_observed()
                self.assertEqual(1, self.durable())
                self.assertEqual(0, self.h.tick()[0])
                self.assertEqual((1, 0), (self.h.status().paused, self.h.status().restarts))

    def test_ignored_closed_container_is_explicit_policy_witness(self):
        def ignored(value):
            slot = value.rows[0].slots[2]
            slot.kind, slot.outcome, slot.non_target_id, slot.ignored_container_id = 2, 4, 0, 9
            slot.ignored_icon_box[:] = slot.non_target_icon_box[:]
            slot.ignored_icon_score = slot.ignored_gold_iou = slot.ignored_gold_coverage = 1
            slot.ignored_dark_iou = slot.ignored_dark_coverage = 1
            value.certificate.non_target_items, value.certificate.ignored_containers = 2, 1
            value.certificate.name_boxes[2][:] = (0, 0, 0, 0)
            value.certificate.strip_box[3] = 67
        self.goods()
        self.assess(3, 2, ignored)
        self.assertEqual((3, 0), (self.cycle().outcome, self.cycle().status))
        self.pause_observed()
        self.assertEqual(1, self.durable())
        self.assertEqual((1, 3), (self.h.tick()[0], self.h.events()[-1].command.kind))

    def test_actual_closed_container_footprints_fit_only_the_ignored_policy_strip(self):
        for ident in (9, 10):
            with self.subTest(ignored_id=ident):
                self.setUp()
                self.goods()
                def actual(value):
                    slot = value.rows[0].slots[2]
                    slot.kind, slot.outcome, slot.non_target_id, slot.ignored_container_id = 2, 4, 0, ident
                    slot.ignored_icon_score = slot.ignored_gold_iou = slot.ignored_gold_coverage = 1
                    slot.ignored_dark_iou = slot.ignored_dark_coverage = 1
                    slot.ignored_icon_box[:] = (slot.cx - 18, slot.sy + 49, 36, 33)
                    witness = value.certificate
                    witness.non_target_items, witness.ignored_containers = 2, 1
                    witness.strip_box[3] = 67
                    witness.item_boxes[2][:] = slot.ignored_icon_box[:]
                    witness.name_boxes[2][:] = (0, 0, 0, 0)
                    witness.price_boxes[2][:] = (slot.cx - 4, slot.sy + 83, 9, 7)
                    if ident == 10:
                        witness.board_mode = 2
                        for side in range(2):
                            witness.board_edge_counts[side][:] = (24, 24, 20, 20)
                            witness.board_corner_counts[side][:] = (1, 1, 1, 1)
                self.assess(3, 2, actual)
                self.assertEqual((3, 0), (self.cycle().outcome, self.cycle().status),
                                 "complete fixed 36x33 closed-container evidence must not be clipped as a named item")
                self.pause_observed()
                self.assertEqual(1, self.durable())
                self.assertEqual((1, 3), (self.h.tick()[0], self.h.events()[-1].command.kind))

    def changed_floor_goods(self, goods):
        restart = self.negative_restart()
        self.assertEqual(1, self.intent(restart))
        h = self.h
        h.ack(restart)
        h.now += 210_000_000
        floor = h.scene(state=2, gold=2, terrain=native.textured(), beat=True)
        floor.fingerprint[:] = bytes([80] * 48)
        floor.goods = goods
        h.observe(floor)
        old = self.cycle()
        self.assertEqual((h.number, 0, 1), (old.next_floor_capture_id, h.status().input_state, old.level_id),
                         "changed fresh FLOOR proves RESTART even when new-map goods are already visible")
        self.assertEqual(0, h.tick()[0], "next-level input waits for durable outcome")
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(h.engine,
            old.job_id, old.next_floor_capture_id, h.prefix, h.now))
        current = self.cycle()
        self.assertEqual((2, old.job_id + 1, h.number, restart.id, 1, goods == 1),
                         (current.level_id, current.job_id, current.capture_id, current.prefix,
                          current.pending, current.partial))
        snapshot = bytes(current)
        self.assertEqual(0, self.lib.ng2_controller_cycle_storage_failed(h.engine, old.job_id, h.now))
        self.assertEqual(snapshot, bytes(self.cycle()), "old-level writer cannot mutate new-level goods hold")

    def test_restart_changed_floor_with_partial_goods_starts_new_bound_hold_after_outcome(self):
        self.changed_floor_goods(1)

    def test_restart_changed_floor_with_visible_goods_starts_new_bound_hold_after_outcome(self):
        self.changed_floor_goods(2)

    def test_container_extension_rejects_one_pixel_overflow_cross_slot_and_unknown(self):
        for fault in ("icon_bottom", "price_bottom", "cross_slot", "strip_height", "unknown", "named_extension"):
            with self.subTest(fault=fault):
                self.setUp()
                self.goods()
                def malformed(value):
                    slot = value.rows[0].slots[2]
                    slot.kind, slot.outcome, slot.non_target_id, slot.ignored_container_id = 2, 4, 0, 9
                    slot.ignored_icon_score = slot.ignored_gold_iou = slot.ignored_gold_coverage = 1
                    slot.ignored_dark_iou = slot.ignored_dark_coverage = 1
                    slot.ignored_icon_box[:] = (slot.cx - 18, slot.sy + 49, 36, 33)
                    w = value.certificate
                    w.non_target_items, w.ignored_containers = 2, 1
                    w.strip_box[3] = 67
                    w.item_boxes[2][:] = slot.ignored_icon_box[:]
                    w.name_boxes[2][:] = (0, 0, 0, 0)
                    w.price_boxes[2][:] = (slot.cx - 4, slot.sy + 83, 9, 7)
                    if fault == "icon_bottom":
                        slot.ignored_icon_box[1] = slot.sy + 58
                        w.item_boxes[2][:] = slot.ignored_icon_box[:]
                    elif fault == "price_bottom":
                        w.price_boxes[2][3] += 1
                    elif fault == "cross_slot":
                        slot.ignored_icon_box[0] = slot.cx - 18 + 9
                        w.item_boxes[2][:] = slot.ignored_icon_box[:]
                    elif fault == "strip_height":
                        w.strip_box[3] += 1
                    elif fault == "unknown":
                        slot.kind = slot.outcome = slot.ignored_container_id = 0
                    else:
                        slot.kind, slot.outcome, slot.non_target_id, slot.ignored_container_id = 1, 3, 3, 0
                        slot.non_target_icon_box[:] = slot.ignored_icon_box[:]
                        w.name_boxes[2][:] = slot.non_target_name_box[:]
                        w.non_target_items, w.ignored_containers, w.strip_box[3] = 3, 0, 65
                self.assess(3, 2, malformed)
                self.assertEqual((0, 3, 7), (self.cycle().outcome, self.cycle().status, self.cycle().state))

    def test_recorded_named_full_sprite_poses_use_finite_bank_search_not_presence_window(self):
        # Only these full-template boxes come from recorded326. Remaining
        # certificate values are procedural controller-boundary fixtures;
        # this test does not promote recorded326 to a coverage negative.
        poses = ((466, 80, 34, 34), (502, 80, 36, 34), (538, 74, 36, 36))
        for fault in (None, "right_pose_plus_one", "top_pose_plus_one", "sprite_overlap", "named_price_extension"):
            with self.subTest(fault=fault):
                self.setUp()
                self.goods()
                def record_pose(value):
                    row, w = value.rows[0], value.certificate
                    row.left, row.sy = 482, 43
                    w.row[:] = (482, 43)
                    boxes = [w.strip_box, w.merchant_box, *w.sign_boxes, *w.board_boxes,
                             *w.price_boxes, *w.name_boxes, *(end.box for end in w.endcaps)]
                    for box in boxes:
                        box[0] += 182
                        box[1] -= 47
                    for index, slot in enumerate(row.slots):
                        slot.cx, slot.sy = 482 + 36 * index, 43
                        slot.non_target_icon_box[:] = poses[index]
                        slot.non_target_name_box[:] = w.name_boxes[index][:]
                        w.item_boxes[index][:] = poses[index]
                    w.merchant_box[:] = (500, 7, 36, 36)
                    for index, pose in enumerate(((458, 65, 48, 12), (500, 53, 36, 12), (513, 41, 84, 12))):
                        row.slots[index].non_target_name_box[:] = pose
                        w.name_boxes[index][:] = pose
                    for index, pose in enumerate(((480, 119, 9, 7), (513, 119, 15, 7), (550, 119, 11, 7))):
                        w.price_boxes[index][:] = pose
                    if fault == "right_pose_plus_one":
                        row.slots[0].non_target_icon_box[0] = row.slots[0].cx - 17 + 9
                        w.item_boxes[0][:] = row.slots[0].non_target_icon_box[:]
                    elif fault == "top_pose_plus_one":
                        row.slots[0].non_target_icon_box[1] = row.sy + 23
                        w.item_boxes[0][:] = row.slots[0].non_target_icon_box[:]
                    elif fault == "sprite_overlap":
                        row.slots[1].non_target_icon_box[0] = 499
                        w.item_boxes[1][:] = row.slots[1].non_target_icon_box[:]
                    elif fault == "named_price_extension":
                        w.price_boxes[1][1], w.price_boxes[1][3] = row.sy + 83, 7
                self.assess(3, 2, record_pose)
                self.assertEqual((3, 0) if fault is None else (0, 3),
                                 (self.cycle().outcome, self.cycle().status))

    def test_negative_restart_begin_rechecks_cumulative_walk_deadline_after_writer_wait(self):
        h = self.h
        self.goods()
        self.assess(3, 2)
        self.pause_observed()
        stop = h.status().walk_started_ns + 45 * SECOND
        # A blocked writer does not block control/main. Fresh real PAUSE
        # observations keep source validity, while the original walk budget
        # continues to expire. This models a callback boundary, not device IO.
        while h.now < stop - 10_000_000:
            h.now = min(h.now + SECOND, stop - 10_000_000)
            h.observe(h.scene(state=1))
            self.assertEqual(0, h.tick()[0])
        self.assertEqual(1, self.durable())
        ready, restart = h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(1, self.intent(restart))
        h.now = stop
        self.assertLessEqual(h.now, restart.deadline_ns)
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, restart.id, h.now, 1, 0, 1),
                         "durable intent does not renew the original 45-second walk horizon")

    def test_late_old_level_writer_failure_cannot_change_new_search(self):
        restart = self.negative_restart()
        self.assertEqual(1, self.intent(restart))
        self.next_floor(restart)
        h = self.h
        old = self.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(h.engine,
            old.job_id, old.next_floor_capture_id, h.prefix, h.now))
        state, snapshot = bytes(h.status()), bytes(self.cycle())
        self.assertEqual(0, self.lib.ng2_controller_cycle_storage_failed(h.engine, old.job_id, h.now + 1),
                         "old job identity cannot mutate a new level after outcome commit")
        self.assertEqual((state, snapshot), (bytes(h.status()), bytes(self.cycle())))

    def test_partial_safe_flag_without_observed_slot_is_not_continuation_authority(self):
        self.goods(partial=True)
        self.assess(0, 1, lambda value: setattr(value, "partial_safe_no_positive", 1))
        self.assertEqual(7, self.cycle().state,
                         "a scalar flag cannot replace an observed partial slot")

    def test_queued_full_frame_becomes_a_fresh_serial_job_after_safe_partial(self):
        self.goods(partial=True)
        h = self.h
        old = self.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(h.engine,
            old.job_id, old.capture_id, old.prefix, h.now))
        admitted = self.cycle()
        h.now += 10_000_000
        self.goods()
        queued = self.cycle()
        ready, pause = h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        result = Result(abi=1, size=C.sizeof(Result), outcome=0, coverage=1,
                        selected_row=-1, selected_partial=-1, partial_count=1,
                        partial_safe_no_positive=1, started_ns=admitted.worker_started_ns,
                        finished_ns=h.now)
        result.partial[0].icon_score = result.partial[0].icon_upper_bound = .1
        result.partial[0].icon_score_exact = 1
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(h.engine,
            old.job_id, old.capture_id, old.prefix, h.now, C.byref(result)))
        current = self.cycle()
        self.assertEqual((old.job_id + 1, queued.queued_capture_id, queued.queued_capture_start_ns + 150_000_000),
                         (current.job_id, current.capture_id, current.deadline_ns))
        self.assertEqual((0, 1, 1), (current.partial, current.pending, current.full_seen))
        self.assess(3, 2)
        h.ack(pause)
        h.now += 210_000_000
        h.observe(h.scene(state=1))
        self.assertEqual(1, self.durable())
        self.assertEqual((1, 3), (h.tick()[0], h.events()[-1].command.kind))

    def test_inflight_goods_credit_real_move_once_and_keep_unknown_motion_held(self):
        for known in (True, False):
            with self.subTest(known=known):
                self.setUp()
                h = self.h
                terrain = h.fit()
                move = h.next_move(terrain)
                h.ack(move)
                after = native.translated(terrain, move.direction)
                after.goods = "visible"
                if not known:
                    after.signature = bytes([40]) * 23296
                h.observed_result(move, after)
                self.assertEqual((1, int(known), 0, 1),
                    (h.status().inputs, h.status().moves, h.status().input_state, self.cycle().pending))
                self.assertEqual(h.number, self.cycle().capture_id)
                self.assertEqual((1, 2), (h.tick()[0], h.events()[-1].command.kind))
                self.assertEqual(1, len([event for event in h.events() if event.command.kind == 4]))

    def search_restart_first_goods(self, goods=2, changed=True, stable=1, prefix=None, delay_ns=200_000_000):
        h = self.h
        self.assertEqual(1, h.observe(h.scene(state=2, gold=1)))
        ready, pause = h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        h.ack(pause)
        h.now += 200_000_000
        h.observe(h.scene(state=1))
        ready, restart = h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        h.ack(restart)
        h.now += delay_ns
        first = h.scene(state=2, gold=2, terrain=native.textured() if goods == 1 else None)
        first.goods = goods
        if goods == 2:
            first.tiles[3 * 23 + 8] = 2
        if changed:
            for index in (0, 1, 2, 8, 9, 10):
                first.fingerprint[index] = 12
        h.observe(first, stable=stable, prefix=h.prefix if prefix is None else prefix)
        return first, restart

    def changed_search_goods(self, goods):
        first, restart = self.search_restart_first_goods(goods)
        h = self.h
        source = self.cycle()
        self.assertEqual((0, 1, 2, h.number, restart.id),
                         (h.status().input_state, h.status().restarts, source.level_id,
                          source.capture_id, source.prefix),
                         "first goods FLOOR must drain the search RESTART and bind the new-level job")
        observed = next(event for event in h.events() if event.command.id == restart.id)
        self.assertEqual(h.number, observed.observed_capture_id)
        self.assess(1)
        # The UI settle interval uses capture start, so obtain another frame
        # beyond ACK+200ms rather than rebasing the original goods evidence.
        h.now += 4
        h.observe(first)
        self.pause_observed()
        self.assertEqual(1, self.durable())
        self.assertEqual(0, h.tick()[0])
        self.assertEqual((1, 1, 1), (h.status().terminal, h.status().paused, h.status().restarts))

    def test_search_restart_first_visible_goods_drains_and_binds_new_level(self):
        self.changed_search_goods(2)

    def test_search_restart_first_partial_goods_drains_and_binds_new_level(self):
        self.changed_search_goods(1)

    def test_search_restart_unchanged_goods_holds_without_new_level_or_retry(self):
        for goods in (1, 2):
            with self.subTest(goods=goods):
                self.setUp()
                first, _ = self.search_restart_first_goods(goods, changed=False)
                h = self.h
                source = self.cycle()
                self.assertEqual((0, 0, 1, h.number),
                    (h.status().input_state, h.status().restarts, source.level_id, source.capture_id))
                if goods == 2:
                    self.assess(3, 2)
                else:
                    def safe(value):
                        value.partial_safe_no_positive = value.partial_count = 1
                        value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
                        value.partial[0].icon_score_exact = 1
                    self.assess(0, 1, safe)
                self.assertEqual(7, self.cycle().state, "unconfirmed search RESTART grants no continuation")
                h.now += 4
                h.observe(first)
                self.pause_observed()
                self.assertEqual(1, self.durable())
                self.assertEqual(0, h.tick()[0], "a negative cannot retry an unproved RESTART")
                self.assertEqual((1, 1, 0, 1),
                    (h.status().terminal, h.status().paused, h.status().restarts, self.cycle().level_id))

    def test_search_restart_crossed_first_goods_waits_for_current_stable_prefix(self):
        for fault in ("inflight_capture", "old_prefix"):
            with self.subTest(fault=fault):
                self.setUp()
                first, restart = self.search_restart_first_goods(2, stable=int(fault != "inflight_capture"),
                    prefix=0 if fault == "old_prefix" else None)
                h = self.h
                before = self.cycle()
                self.assertEqual((3, 0, 1, 0),
                    (h.status().input_state, h.status().restarts, before.level_id, before.capture_id))
                self.assertEqual(0, h.tick()[0])
                h.now += 10_000_000
                h.observe(first)
                current = self.cycle()
                self.assertEqual((0, 1, 2, h.number, restart.id),
                    (h.status().input_state, h.status().restarts, current.level_id,
                     current.capture_id, current.prefix))
        for delay, credit in ((4 * SECOND - 1, 1), (4 * SECOND, 0)):
            with self.subTest(transition_delay_ns=delay):
                self.setUp()
                self.search_restart_first_goods(2, delay_ns=delay)
                self.assertEqual((0, credit, 1 + credit, self.h.number),
                    (self.h.status().input_state, self.h.status().restarts,
                     self.cycle().level_id, self.cycle().capture_id),
                    "a late goods hold cannot extend the original RESTART transition window")


if __name__ == "__main__":
    unittest.main()
