"""TEST072 public-C local passage control and level boundaries.

All maps, signatures, later frames and device clocks in this module are
procedural. The user's twelve visual examples motivate the passage families;
these tests do not reconstruct absent raw screenshots or prove iPhone arrival.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics

SECOND = fixture.SECOND
PERIOD = fixture.PERIOD
CORE = mechanics.CORE


def passage_room(mouth=(0, -3), outside=True, second=None):
    tiles = {(x, y): 'floor' for x in range(-2, 3) for y in range(-2, 3)}
    for n in range(-3, 4):
        tiles[(n, -3)] = tiles[(n, 3)] = 'dirt'
        tiles[(-3, n)] = tiles[(3, n)] = 'dirt'
    for point in (mouth, second):
        if point is None:
            continue
        tiles[point] = 'floor'
        dx, dy = (-1, 0) if point[0] == -3 else (0, -1)
        if outside:
            tiles[(point[0]+dx, point[1]+dy)] = 'floor'
    return fixture.textured(tiles)


class NativePassage072Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
    tearDownClass = classmethod(mechanics.NativeRecoveryTests.tearDownClass.__func__)
    setUp = fixture.NativeControllerTests.setUp
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    tick = fixture.NativeControllerTests.tick
    ack = fixture.NativeControllerTests.ack
    motion_wait = fixture.NativeControllerTests.motion_wait
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation

    def scene(self, terrain, gold=None, state=2, fingerprint=None, beat=True):
        if gold is None:
            gold = 2 if terrain.gold else 1
        out = fixture.NativeControllerTests.scene(self, state, gold, terrain, beat=beat)
        if fingerprint is not None:
            out.fingerprint[:] = fingerprint
        return out

    def observe(self, terrain, **kwargs):
        frame = terrain if isinstance(terrain, fixture.Scene) else self.scene(terrain)
        return fixture.NativeControllerTests.observe(self, frame, **kwargs)

    def fit_clear(self, terrain):
        for _ in range(27):
            self.now += 100_000_000
            self.assertEqual(1, self.observe(terrain))
        return terrain

    def next_operation(self, terrain):
        for _ in range(100):
            ready, command = self.tick()
            if ready:
                return command
            status = self.status()
            if status.terminal or status.reason:
                return command
            if status.next_target_ns and status.next_target_ns >= status.lead_ns+100_000_000:
                self.now = max(self.now, status.next_target_ns-status.lead_ns-100_000_000)
            else:
                self.now += 10_000_000
            self.observe(terrain)
        self.fail('bounded procedural observations must yield an operation or a stated stop')

    def next_move(self, terrain):
        command = self.next_operation(terrain)
        self.assertEqual(4, command.kind,
            'an observed side passage must be approached before a no-gold restart')
        dx, dy = fixture.DIRS[command.direction]
        self.assertEqual('floor', terrain.tiles.get((dx, dy)))
        self.assertNotIn((dx, dy), terrain.protected)
        return command

    def moved(self, terrain, command, reveal=None):
        count = self.status().moves
        self.ack(command)
        shifted = fixture.translated(terrain, command.direction)
        if reveal:
            shifted.tiles.update(reveal)
            shifted.gold = {p for p, kind in shifted.tiles.items() if kind == 'gold'}
        self.now = max(self.now, command.target_ns+80_000_002)
        self.assertEqual(1, self.observe(shifted))
        self.assertEqual(count+1, self.status().moves)
        self.assertEqual(0, self.status().reason)
        return shifted

    def test_gold_clear_passage_moves_on_observed_floor_instead_of_restarting(self):
        for mouth, direction in (((0, -3), 3), ((-3, 0), 1), ((2, -3), 2)):
            with self.subTest(mouth=mouth):
                self.fresh_engine()
                terrain = self.fit_clear(passage_room(mouth))
                command = self.next_move(terrain)
                self.assertEqual(direction, command.direction)
                self.assertEqual((0, 0, 0),
                    (self.status().inputs, self.status().moves, self.status().restarts))
                self.moved(terrain, command)
                self.assertEqual((1, 1, 1),
                    (self.status().inputs, self.status().moves, self.status().lead_confirmed))

    def walk_to_goal(self):
        terrain = self.fit_clear(passage_room())
        commands = []
        for _ in range(4):
            command = self.next_move(terrain)
            self.assertEqual(3, command.direction)
            commands.append(command)
            terrain = self.moved(terrain, command)
        self.assertEqual((0, -4), (self.status().x, self.status().y))
        return terrain, commands

    def test_moved_gold_reveal_uses_normal_shop_without_restart(self):
        terrain = self.fit_clear(passage_room())
        first = self.next_move(terrain)
        terrain = self.moved(terrain, first,
            {(0, -2): 'door', (-1, -2): 'gold', (1, -2): 'gold'})
        following = self.next_move(terrain)
        self.assertEqual(3, following.direction)
        self.assertEqual((0, 1, 1),
            (self.status().restarts, self.status().inputs, self.status().moves))
        self.assertGreater(following.id, first.id)
        self.assertGreater(following.ordinal, first.ordinal)

    def test_final_vantage_requires_independent_clear_before_restart(self):
        terrain, commands = self.walk_to_goal()
        self.assertEqual(0, self.tick()[0],
            'the same MOVED frame cannot also prove the independent no-gold inspection')
        self.now += 100_000_000
        self.observe(terrain)
        pause = self.next_operation(terrain)
        self.assertEqual(2, pause.kind)
        self.assertEqual((4, 4, 0),
            (self.status().inputs, self.status().moves, self.status().restarts))
        self.assertEqual(4, len([e for e in self.events() if e.command.kind == 4 and e.begin_ns]))

    def test_gold_reveal_retires_unsent_exploration_before_new_shop_ticket(self):
        terrain = self.fit_clear(passage_room())
        old = self.next_move(terrain)
        revealed = deepcopy(terrain)
        revealed.tiles.update({(0, -3): 'door', (-1, -3): 'gold', (1, -3): 'gold'})
        revealed.gold = {p for p, kind in revealed.tiles.items() if kind == 'gold'}
        self.now += 2
        self.observe(revealed)
        self.assertEqual((0, 0, 0),
            (self.status().reason, self.status().input_state, self.status().inputs))
        self.assertEqual((3, 0, 0),
            (self.events()[-1].outcome, self.events()[-1].begin_ns, self.events()[-1].motion))
        self.assertEqual(0, self.tick()[0])
        self.reject_old_callbacks_without_mutation(old)
        self.now += 100_000_000
        self.observe(revealed)
        following = self.next_move(revealed)
        self.assertGreater(following.id, old.id)
        self.assertGreater(following.target_ns, old.target_ns)
        self.assertEqual(0, self.status().restarts)
        self.reject_old_callbacks_without_mutation(old)

    def paused_after_inspection(self):
        terrain, commands = self.walk_to_goal()
        self.now += 100_000_000
        self.observe(self.scene(terrain, fingerprint=bytes([80])*48))
        pause = self.next_operation(terrain)
        self.assertEqual(2, pause.kind)
        self.ack(pause)
        self.now += 2
        self.observe(self.scene(terrain, state=1, fingerprint=bytes([80])*48))
        self.now += 200_000_000
        restart = self.next_operation(terrain)
        self.assertEqual(3, restart.kind)
        return terrain, commands, pause, restart

    def restarted_level(self):
        old_terrain, commands, pause, restart = self.paused_after_inspection()
        previous = self.status()
        self.ack(restart)
        self.now += 2
        self.observe(self.scene(old_terrain, fingerprint=bytes([80])*48))
        self.assertEqual((3, 0, 0, -4, 1),
            (self.status().input_state, self.status().restarts, self.status().x,
             self.status().y, self.status().lead_confirmed),
            'an ACK followed by the old endpoint world is not a new level')
        terrain = passage_room((-3, 0))
        self.now += 100_000_000
        self.observe(self.scene(terrain, fingerprint=bytes([160])*48))
        status = self.status()
        self.assertEqual((0, 1, 0, 0, 0),
            (status.input_state, status.restarts, status.x, status.y, status.lead_confirmed))
        self.assertEqual((previous.inputs, previous.moves, previous.started_ns,
                          previous.walk_started_ns, previous.first_move_ns, previous.last_ordinal),
            (status.inputs, status.moves, status.started_ns, status.walk_started_ns,
             status.first_move_ns, status.last_ordinal),
            'level geometry resets without restoring session budget or old beat credit')
        for old in [*commands, pause, restart]:
            self.reject_old_callbacks_without_mutation(old)
        return terrain, previous, commands

    def test_walked_restart_uses_endpoint_fingerprint_and_level_local_calibration(self):
        terrain, previous, commands = self.restarted_level()
        self.fit_clear(terrain)
        command = self.next_move(terrain)
        self.assertEqual(1, command.direction)
        self.assertGreater(command.id, commands[-1].id)
        self.assertEqual(previous.last_ordinal+1, command.ordinal)
        self.assertEqual(0, self.status().lead_confirmed)
        terrain = self.moved(terrain, command)
        self.assertEqual((previous.inputs+1, previous.moves+1, -1, 0, 1),
            (self.status().inputs, self.status().moves, self.status().x,
             self.status().y, self.status().lead_confirmed))
        self.assertEqual(previous.walk_started_ns, self.status().walk_started_ns)

    def test_restart_never_extends_original_walk_equality_deadline(self):
        terrain, previous, _ = self.restarted_level()
        self.fit_clear(terrain)
        old = self.next_move(terrain)
        self.now = previous.walk_started_ns+45*SECOND
        self.tick()
        self.assertEqual(14, self.status().reason)
        self.assertEqual(previous.inputs, self.status().inputs)
        self.assertEqual((3, 0), (self.events()[-1].outcome, self.events()[-1].begin_ns))
        self.reject_old_callbacks_without_mutation(old)

    def stage(self, stage):
        terrain = passage_room()
        command = None
        if stage == 'start':
            return terrain, command
        if stage == 'calibration':
            for _ in range(3):
                self.now += 100_000_000
                self.observe(terrain)
            return terrain, command
        if stage == 'final':
            terrain, commands = self.walk_to_goal()
            return terrain, commands[-1]
        self.fit_clear(terrain)
        command = self.next_move(terrain)
        if stage == 'ack':
            self.ack(command)
        return terrain, command

    def test_goods_item_and_protection_hold_at_every_exploration_stage(self):
        for stage in ('start', 'calibration', 'reserved', 'ack', 'final'):
            for fault in ('partial', 'visible', 'protected', 'item'):
                with self.subTest(stage=stage, fault=fault):
                    self.fresh_engine()
                    terrain, command = self.stage(stage)
                    before = self.status()
                    changed = deepcopy(terrain)
                    if fault in ('partial', 'visible'):
                        changed.goods = fault
                    elif fault == 'protected':
                        changed.protected.add((0, 1))
                    else:
                        changed.tiles[(0, 1)] = 'item'
                    self.now += 2
                    self.observe(changed)
                    self.assertEqual(1 if fault == 'visible' else 13, self.status().reason)
                    self.assertEqual(before.inputs, self.status().inputs)
                    self.assertLessEqual(self.status().moves, before.moves+1)
                    for _ in range(3):
                        ready, operation = self.tick()
                        self.assertNotIn(operation.kind, (3, 4))
                        self.now += 100_000_000
                    self.assertEqual(0, self.status().restarts)
                    if command is not None:
                        self.reject_old_callbacks_without_mutation(command)

    def test_cancel_foreground_and_owner_stop_every_exploration_stage(self):
        for stage in ('start', 'calibration', 'reserved', 'ack', 'final'):
            for fault, reason in (('cancel', 2), ('foreground', 3), ('owner', 5)):
                with self.subTest(stage=stage, fault=fault):
                    self.fresh_engine()
                    terrain, command = self.stage(stage)
                    before = self.status()
                    if fault == 'cancel':
                        self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                    else:
                        self.tick(front=0 if fault == 'foreground' else 1,
                                  owner=0 if fault == 'owner' else 1)
                    self.assertEqual(reason, self.status().reason)
                    self.assertEqual(before.inputs, self.status().inputs)
                    self.assertEqual(before.restarts, self.status().restarts)
                    self.now += 2
                    self.observe(terrain)
                    self.assertNotIn(self.tick()[1].kind, (3, 4))
                    if command is not None:
                        self.reject_old_callbacks_without_mutation(command)

    def test_unknown_sent_exploration_and_restart_cannot_issue_or_reset(self):
        for operation in ('exploration', 'restart'):
            with self.subTest(operation=operation):
                self.fresh_engine()
                if operation == 'exploration':
                    terrain = self.fit_clear(passage_room())
                    command = self.next_move(terrain)
                else:
                    terrain, _, _, command = self.paused_after_inspection()
                self.now = max(self.now, command.not_before_ns)
                self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                self.now += 2
                self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1))
                before = self.all_public_bytes()
                self.now += 2
                new = self.scene(passage_room((-3, 0)), fingerprint=bytes([200])*48)
                self.observe(new)
                self.assertEqual((11, 4, 0),
                    (self.status().reason, self.status().input_state, self.status().restarts))
                self.assertEqual(before, self.all_public_bytes())
                self.assertNotIn(self.tick()[1].kind, (3, 4))

    def test_shadowed_outer_goal_waits_for_observed_floor_and_never_steps_unknown(self):
        for reveal in (False, True):
            with self.subTest(reveal=reveal):
                self.fresh_engine()
                terrain = self.fit_clear(passage_room(outside=False))
                for _ in range(3):
                    command = self.next_move(terrain)
                    terrain = self.moved(terrain, command)
                self.assertEqual((0, -3), (self.status().x, self.status().y))
                waiting = self.now
                self.assertEqual(0, self.tick()[0])
                self.now += 100_000_000
                if reveal:
                    terrain.tiles[(0, -1)] = 'floor'
                self.observe(terrain)
                self.assertNotEqual(3, self.tick()[1].kind)
                if reveal:
                    self.now += 100_000_000
                    self.observe(terrain)
                    following = self.next_move(terrain)
                    self.assertEqual(3, following.direction)
                    terrain = self.moved(terrain, following)
                    self.assertEqual((0, -4), (self.status().x, self.status().y))
                else:
                    self.now = waiting+2*PERIOD
                    self.tick()
                    self.assertEqual((12, 3, 3, 0),
                        (self.status().reason, self.status().inputs,
                         self.status().moves, self.status().restarts),
                        'an unreachable unknown goal is unresolved, never no-gold completion')

    def test_multiple_fixed_mouths_are_retained_until_both_independent_inspections(self):
        terrain = self.fit_clear(passage_room(second=(-3, 0)))
        for _ in range(4):
            command = self.next_move(terrain)
            self.assertEqual(3, command.direction)
            terrain = self.moved(terrain, command)
        self.now += 100_000_000
        self.observe(terrain)
        for _ in range(8):
            command = self.next_move(terrain)
            self.assertIn(command.direction, (1, 4))
            terrain = self.moved(terrain, command)
        self.assertEqual((-4, 0), (self.status().x, self.status().y))
        self.assertEqual(0, self.tick()[0])
        self.now += 100_000_000
        self.observe(terrain)
        self.assertEqual(2, self.next_operation(terrain).kind)
        self.assertEqual((12, 12, 0),
            (self.status().inputs, self.status().moves, self.status().restarts))

    def test_restarted_level_retune_and_initial_recovery_use_local_zero(self):
        for mode in ('blocked', 'unsent'):
            with self.subTest(mode=mode):
                self.fresh_engine()
                terrain, previous, _ = self.restarted_level()
                self.fit_clear(terrain)
                old = self.next_move(terrain)
                if mode == 'blocked':
                    self.ack(old)
                    self.now = max(self.now, old.target_ns+80_000_002)
                    self.observe(terrain)
                    self.assertEqual((0, previous.inputs+1, previous.moves, 75_000_000),
                        (self.status().reason, self.status().inputs,
                         self.status().moves, self.status().lead_ns))
                    following = self.next_move(terrain)
                    self.assertEqual(old.direction, following.direction)
                else:
                    self.now = old.deadline_ns+1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, old.id, self.now, 0))
                    self.assertEqual((0, 0, previous.inputs),
                        (self.status().reason, self.status().input_state, self.status().inputs))
                    self.fit_clear(terrain)
                    following = self.next_move(terrain)
                self.assertGreater(following.id, old.id)
                self.reject_old_callbacks_without_mutation(old)
                self.moved(terrain, following)
                self.assertEqual(1, self.status().lead_confirmed)

    def test_partial_or_protected_after_inspection_revokes_pause_and_restart_authority(self):
        for phase in ('pause_reserved', 'pause_ack', 'restart_reserved', 'restart_ack'):
            for fault in ('partial', 'item', 'protected'):
                with self.subTest(phase=phase, fault=fault):
                    self.fresh_engine()
                    terrain, _ = self.walk_to_goal()
                    self.now += 100_000_000
                    self.observe(terrain)
                    operation = self.next_operation(terrain)
                    self.assertEqual(2, operation.kind)
                    if phase != 'pause_reserved':
                        self.ack(operation)
                    if phase.startswith('restart'):
                        self.now += 2
                        self.observe(self.scene(terrain, state=1))
                        self.now += 200_000_000
                        operation = self.next_operation(terrain)
                        self.assertEqual(3, operation.kind)
                        if phase == 'restart_ack':
                            self.ack(operation)
                    before = self.status()
                    changed = deepcopy(terrain)
                    if fault == 'partial':
                        changed.goods = 'partial'
                    elif fault == 'item':
                        changed.tiles[(0, 1)] = 'item'
                    else:
                        changed.protected.add((0, 1))
                    self.now += 2
                    self.observe(changed)
                    self.assertEqual((13, 0, before.inputs),
                        (self.status().reason, self.status().restarts, self.status().inputs))
                    self.assertNotIn(self.tick()[1].kind, (3, 4))
                    self.reject_old_callbacks_without_mutation(operation)

    def test_new_gold_revokes_skip_and_started_pause_holds_candidate(self):
        for phase in ('reserved', 'ack'):
            with self.subTest(phase=phase):
                self.fresh_engine()
                terrain, _ = self.walk_to_goal()
                self.now += 100_000_000
                self.observe(terrain)
                old_pause = self.next_operation(terrain)
                self.assertEqual(2, old_pause.kind)
                if phase == 'ack':
                    self.ack(old_pause)
                revealed = deepcopy(terrain)
                revealed.tiles.update({(0, -1): 'floor', (-1, -1): 'gold', (1, -1): 'gold'})
                revealed.gold = {p for p, kind in revealed.tiles.items() if kind == 'gold'}
                self.now += 2
                self.observe(revealed)
                if phase == 'ack':
                    self.assertEqual((12, 0), (self.status().reason, self.status().restarts))
                    self.assertNotIn(self.tick()[1].kind, (3, 4))
                    self.now += 100_000_000
                    self.observe(self.scene(revealed, state=1))
                    self.assertEqual((1, 1, 0),
                        (self.status().terminal, self.status().paused, self.status().restarts))
                    continue
                self.assertEqual((0, 0, 3, 0),
                    (self.status().reason, self.status().input_state,
                     self.events()[-1].outcome, self.status().restarts))
                self.reject_old_callbacks_without_mutation(old_pause)
                self.now += 100_000_000
                self.observe(revealed)
                following = self.next_move(revealed)
                self.assertGreater(following.id, old_pause.id)
                self.assertEqual(3, following.direction)

    def test_one_native_session_restarts_searches_enters_and_completes_only_on_goods(self):
        # This is a procedural public-C integration unit, not an iPhone replay.
        empty = self.fit_clear(passage_room(mouth=None))
        pause = self.next_operation(empty)
        self.assertEqual(2, pause.kind)
        self.ack(pause)
        self.now += 2
        self.observe(self.scene(empty, state=1))
        self.now += 200_000_000
        restart = self.next_operation(empty)
        self.assertEqual(3, restart.kind)
        self.ack(restart)
        terrain = passage_room(outside=False)
        self.now += 2
        self.observe(self.scene(terrain, fingerprint=bytes([160])*48))
        self.assertEqual((1, 0, 0),
            (self.status().restarts, self.status().terminal, self.status().goods))
        self.fit_clear(terrain)
        for step in range(2):
            command = self.next_move(terrain)
            reveal = {(0, -2): 'door', (-1, -2): 'gold', (1, -2): 'gold',
                      (0, -3): 'floor', (0, -4): 'floor'} if step == 1 else None
            terrain = self.moved(terrain, command, reveal)
        approach = self.next_move(terrain)
        terrain = self.moved(terrain, approach)
        door = self.next_operation(terrain)
        self.assertEqual((4, 3), (door.kind, door.direction))
        self.assertEqual('door', terrain.tiles[(0, -1)])
        self.ack(door)
        opened = deepcopy(terrain)
        opened.tiles[(0, -1)] = 'floor'
        self.now = max(self.now, door.target_ns+80_000_002)
        self.observe(opened)
        self.assertEqual((3, 1, 0, 0),
            (self.status().moves, self.status().door_changes,
             self.status().terminal, self.status().goods))
        entry = self.next_move(opened)
        terrain = self.moved(opened, entry)
        terrain.goods = 'partial'
        self.now += 2
        self.observe(terrain)
        vantage = self.next_move(terrain)
        self.ack(vantage)
        visible = fixture.translated(terrain, vantage.direction)
        visible.goods = 'visible'
        self.now = max(self.now, vantage.target_ns+80_000_002)
        self.observe(visible)
        self.assertEqual((1, 1, 5, 6, 1),
            (self.status().reason, self.status().goods, self.status().moves,
             self.status().inputs, self.status().restarts))
        holding = self.next_operation(visible)
        self.assertEqual(2, holding.kind)
        self.ack(holding)
        self.now += 2
        self.observe(self.scene(visible, state=1))
        self.assertEqual((1, 1, 1),
            (self.status().terminal, self.status().paused, self.status().goods))
        self.assertNotIn(self.tick()[1].kind, (3, 4))

    def test_final_inspection_discards_old_prefix_unstable_and_overlapping_frames(self):
        terrain, _ = self.walk_to_goal()
        arrival = self.now
        self.now += 100_000_000
        self.assertEqual(0, self.observe(terrain, prefix=self.prefix-1))
        self.assertEqual(0, self.tick()[0])
        self.now += 100_000_000
        self.assertEqual(0, self.observe(terrain, stable=0))
        self.assertEqual(0, self.tick()[0])
        self.now += 100_000_000
        # A disjoint frame must follow the actual arrival frame, even if its
        # capture ID and end are newer. Use a fresh engine to keep global
        # capture-start monotonicity distinct from this pair boundary.
        self.fresh_engine()
        terrain, _ = self.walk_to_goal()
        arrival = self.now
        self.now += 100_000_000
        self.assertEqual(1, self.observe(terrain, start=arrival-1, end=self.now))
        self.assertEqual(0, self.tick()[0])
        self.now += 100_000_000
        self.observe(terrain)
        self.assertEqual(2, self.next_operation(terrain).kind)
        self.assertEqual(0, self.status().restarts)

    def test_acknowledged_unknown_visual_motion_never_becomes_another_exploration_step(self):
        terrain = self.fit_clear(passage_room())
        command = self.next_move(terrain)
        self.ack(command)
        unknown = deepcopy(terrain)
        unknown.signature = bytes([40])*23296
        first = command.target_ns+80_000_002
        for index in range(8):
            self.now = first+index*(PERIOD//10+4)
            if index == 7:
                self.now = max(self.now, first+PERIOD+4)
            self.observe(unknown)
            self.assertEqual(index+1, self.motion_wait().attempts)
            self.assertEqual(1, self.status().inputs)
            self.assertNotEqual(3, self.tick()[1].kind)
        self.assertEqual((10, 0, 0),
            (self.status().reason, self.status().moves, self.status().restarts))
        self.assertEqual(1, len([e for e in self.events() if e.command.kind == 4]))
        self.reject_old_callbacks_without_mutation(command)

    def test_acknowledged_restart_proves_new_gold_level_before_normal_shop(self):
        old_terrain, _, _, restart = self.paused_after_inspection()
        previous = self.status()
        self.ack(restart)
        new_terrain = fixture.textured()
        self.now += 2
        self.observe(self.scene(new_terrain, fingerprint=bytes([80])*48))
        self.assertEqual((0, 3), (self.status().restarts, self.status().input_state))
        self.now += 100_000_000
        self.observe(self.scene(new_terrain, fingerprint=bytes([160])*48))
        self.assertEqual((1, 0, 0),
            (self.status().restarts, self.status().x, self.status().y))
        self.fit_clear(new_terrain)
        following = self.next_move(new_terrain)
        self.assertEqual(3, following.direction)
        self.moved(new_terrain, following)
        self.assertEqual((previous.inputs+1, previous.moves+1),
            (self.status().inputs, self.status().moves))
        self.assertEqual(previous.walk_started_ns, self.status().walk_started_ns)

    def test_new_shop_ticket_requires_hud_at_or_after_independent_geometry_proof(self):
        terrain = self.fit_clear(passage_room())
        old = self.next_move(terrain)
        revealed = deepcopy(terrain)
        revealed.tiles.update({(0, -3): 'door', (-1, -3): 'gold', (1, -3): 'gold'})
        revealed.gold = {p for p, kind in revealed.tiles.items() if kind == 'gold'}
        self.now += 2
        self.observe(revealed)
        self.now += 100_000_000
        self.observe(self.scene(revealed, beat=False))
        self.assertEqual((0, 0, 0),
            (self.tick()[0], self.status().inputs, self.status().reason))
        self.assertEqual(1, len(self.events()))
        self.now += 100_000_000
        self.observe(revealed)
        following = self.next_move(revealed)
        self.assertGreater(following.id, old.id)
        self.assertGreaterEqual(following.not_before_ns-self.now, 50_000_000)

    def test_first_skip_pause_new_gold_starts_walk_once_at_real_device_uptime(self):
        for uptime in (1000*SECOND, 32746*SECOND):
            with self.subTest(uptime=uptime):
                self.engine = self.lib.ng2_controller_create(uptime)
                self.assertTrue(self.engine)
                self.addCleanup(self.lib.ng2_controller_destroy, self.engine)
                self.now = uptime+100_000_000
                self.number = self.prefix = 0
                empty = self.fit_clear(passage_room(mouth=None))
                self.assertEqual((0, 0, 0),
                    (self.status().inputs, self.status().moves, self.status().walk_started_ns))
                old_pause = self.next_operation(empty)
                self.assertEqual(2, old_pause.kind)
                revealed = fixture.textured()
                self.now += 2
                first_gold = self.now
                self.observe(revealed)
                self.assertEqual((0, 0, first_gold),
                    (self.status().reason, self.status().input_state, self.status().walk_started_ns),
                    'first gold during an unstarted skip must establish the first walk/sync epoch')
                self.assertEqual((3, 0),
                    (self.events()[-1].outcome, self.events()[-1].begin_ns))
                self.assertEqual(0, self.tick()[0])
                self.reject_old_callbacks_without_mutation(old_pause)
                self.now += 100_000_000
                self.observe(revealed)
                self.fit_clear(revealed)
                following = self.next_move(revealed)
                self.assertGreater(following.id, old_pause.id)
                self.assertEqual(first_gold, self.status().walk_started_ns)
                self.assertEqual((0, 0, 0),
                    (self.status().inputs, self.status().moves, self.status().restarts))
                self.moved(revealed, following)
                self.assertEqual(first_gold, self.status().walk_started_ns)

    def test_uncertain_floor_gold_evidence_revokes_local_completion_and_skip(self):
        for stage, gold, tile in (('initial', 1, True), ('initial', 2, False),
                                  ('inspection', 1, True),
                                  ('pause_reserved', 0, False),
                                  ('pause_reserved', 2, False),
                                  ('pause_reserved', 1, True),
                                  ('restart_reserved', 0, False),
                                  ('restart_reserved', 2, False),
                                  ('restart_reserved', 1, True)):
            with self.subTest(stage=stage, gold=gold, tile=tile):
                self.fresh_engine()
                old_pause = None
                if stage == 'initial':
                    terrain = passage_room(mouth=None)
                elif stage == 'restart_reserved':
                    terrain, _, _, old_pause = self.paused_after_inspection()
                    self.assertEqual(3, old_pause.kind)
                else:
                    terrain, _ = self.walk_to_goal()
                    if stage == 'pause_reserved':
                        self.now += 100_000_000
                        self.observe(terrain)
                        old_pause = self.next_operation(terrain)
                        self.assertEqual(2, old_pause.kind)
                changed = deepcopy(terrain)
                if tile:
                    changed.tiles[(4, 0)] = 'gold'
                    changed.gold.add((4, 0))
                self.now += 100_000_000 if stage == 'inspection' else 2
                self.observe(self.scene(changed, gold=gold))
                self.assertNotEqual(0, self.status().reason,
                    'uncertain floor gold evidence cannot retain a no-gold completion or restart authority')
                self.assertEqual(0, self.status().restarts)
                self.assertNotIn(self.tick()[1].kind, (3, 4))
                if old_pause is not None:
                    event = next(row for row in self.events() if row.command.id == old_pause.id)
                    self.assertEqual((3, 0), (event.outcome, event.begin_ns))
                    self.reject_old_callbacks_without_mutation(old_pause)

    def test_pause_ui_gold_unknown_is_not_uncertain_floor_and_can_restart(self):
        terrain, _ = self.walk_to_goal()
        self.now += 100_000_000
        self.observe(terrain)
        pause = self.next_operation(terrain)
        self.assertEqual(2, pause.kind)
        self.ack(pause)
        self.now += 2
        self.observe(self.scene(terrain, state=1, gold=0))
        self.now += 200_000_000
        restart = self.next_operation(terrain)
        self.assertEqual(3, restart.kind)
        self.assertEqual((0, 0), (self.status().reason, self.status().restarts))


if __name__ == '__main__':
    unittest.main()
