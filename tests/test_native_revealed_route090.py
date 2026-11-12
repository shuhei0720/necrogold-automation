"""TEST090: one stationary view reveals the bracket on a known floor route.

The procedural geometry comes from TEST089 source243/244. Its live beat model
was not exported; the existing explicit synthetic TEST055 context supplies the
clock only. Public C planner, motion and Controller calls remain real.
"""
import ctypes as C
import unittest

from tests import test_native_controller as fixture

CORE = fixture.CORE


class NativeRevealedRoute090Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = fixture.CORE
        try:
            fixture.CORE = CORE
            fixture.NativeControllerTests.setUpClass.__func__(cls)
        finally:
            fixture.CORE = previous

    tearDownClass = classmethod(fixture.NativeControllerTests.tearDownClass.__func__)
    setUp = fixture.NativeControllerTests.setUp
    scene = fixture.NativeControllerTests.scene
    observe = fixture.NativeControllerTests.observe
    tick = fixture.NativeControllerTests.tick
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    motion_wait = fixture.NativeControllerTests.motion_wait
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    next_move = fixture.NativeControllerTests.next_move
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    scene_details = fixture.NativeControllerTests.scene_details
    fresh_private_case = fixture.NativeControllerTests.fresh_private_case
    private_choice = fixture.NativeControllerTests.private_choice

    def fresh_private_wrapper(self):
        previous = fixture.CORE
        try:
            fixture.CORE = CORE
            fixture.NativeControllerTests.fresh_private_wrapper(self)
        finally:
            fixture.CORE = previous

    def geometry(self, turns=0, palette=(9, 0)):
        def rotate(x, y):
            for _ in range(turns): x, y = -y, x
            return x, y
        tiles = {rotate(0, y): 'floor' for y in range(-3, 2)}
        tiles.update({rotate(-1, 0): 'floor', rotate(-2, 0): 'floor',
            rotate(-3, -1): 'gold', rotate(-3, 0): 'dirt', rotate(-3, 1): 'dirt',
            palette: 'dirt'})
        after = dict(tiles)
        after.update({rotate(-3, 0): 'door', rotate(-3, 1): 'gold', palette: 'floor'})
        before = self.scene(2, 2, fixture.textured(tiles))
        latest = self.scene(2, 2, fixture.textured(after))
        return before, latest, rotate(-1, 0)

    def test_stationary_new_bracket_reissues_same_floor_step_without_extending_frozen_ticket(self):
        for turns in range(4):
            with self.subTest(turns=turns):
                before, latest, unit = self.geometry(turns)
                _, _, old, wait = self.fresh_private_case(before, latest)
                self.assertEqual(12, self.scene_details()[-1].validation,
                    'a newly proven bracket and remote palette change must preserve the known floor step')
                self.assertEqual((0, 0, 1, 1), (self.status().reason,
                    self.status().terminal, self.status().inputs, self.status().moves))
                choice = self.private_choice(True)
                self.assertEqual((old.direction, 7, 2*unit[0], 2*unit[1], 1), choice)
                ready, new = self.tick()
                self.assertEqual((1, 4, old.direction), (ready, new.kind, new.direction))
                self.assertNotEqual(old.id, new.id)
                self.assertEqual((old.target_ns, old.not_before_ns, old.deadline_ns, old.ordinal, wait.deadline_ns),
                    (new.target_ns, new.not_before_ns, new.deadline_ns, new.ordinal, self.motion_wait().deadline_ns))
                self.assertEqual((1, 1), (self.scene_details()[-1].continuous_count,
                                        self.scene_details()[-1].chain_count))
                retired = next(row for row in self.events() if row.command.id == old.id)
                self.assertEqual((3, 0, bytes(old)), (retired.outcome, retired.begin_ns, bytes(retired.command)))
                saved = (bytes(self.status()), tuple(bytes(row) for row in self.events()), bytes(self.motion_wait()))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id, new.not_before_ns, 1, 0, 1))
                self.assertEqual(0, self.lib.ng2_controller_complete(self.engine, old.id, new.not_before_ns, 1))
                self.assertEqual(saved, (bytes(self.status()), tuple(bytes(row) for row in self.events()), bytes(self.motion_wait())))

    def test_new_bracket_exception_rejects_near_palette_lost_anchors_blockers_and_nonstationary_pixels(self):
        def at(x, y): return (y+5)*23+x+11
        for fault in ('near_origin', 'near_next', 'distance_five', 'no_bracket', 'lost_old_gold',
                      'other_gold', 'old_stone', 'protected_palette', 'new_protection',
                      'unknown_motion', 'tween_motion', 'changed_target'):
            with self.subTest(fault=fault):
                palette = (1, 1) if fault == 'near_origin' else (-2, 1) if fault == 'near_next' else (5, 0) if fault == 'distance_five' else (9, 0)
                before, latest, _ = self.geometry(palette=palette)
                if fault == 'no_bracket':
                    # Keep the new GOLD observation but break the bracket.
                    # Removing all new GOLD would leave the old SAME policy
                    # legitimately applicable and would not isolate this scope.
                    latest.tiles[at(-3, 1)] = 4; latest.tiles[at(-4, 1)] = 2
                elif fault == 'lost_old_gold': latest.tiles[at(-3, -1)] = 4
                elif fault == 'other_gold': latest.tiles[at(7, 2)] = 2
                elif fault == 'old_stone':
                    before.tiles[at(7, 2)] = 3; latest.tiles[at(7, 2)] = 1
                elif fault == 'protected_palette':
                    before.protected_cells[at(*palette)] = latest.protected_cells[at(*palette)] = 1
                elif fault == 'new_protection': latest.protected_cells[at(7, 2)] = 1
                elif fault in ('unknown_motion', 'tween_motion'):
                    if fault == 'unknown_motion': latest.signature[:] = bytes([29])*len(latest.signature)
                    else:
                        source = fixture.textured(); source.signature = bytes(before.signature)
                        latest.signature[:] = fixture.translated(source, 1, amount=1).signature
                elif fault == 'changed_target': latest.tiles[at(-2, 0)] = 3
                _, _, old, _ = self.fresh_private_case(before, latest)
                self.assertNotEqual(12, self.scene_details()[-1].validation)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id, old.not_before_ns, 1, 0, 1))

    def test_new_bracket_reveal_cannot_bypass_existing_run_or_chain_limits(self):
        for field, limit in ((8, 8), (9, 2)):
            with self.subTest(field=field, limit=limit):
                before, latest, _ = self.geometry()
                _, _, old, wait = self.fresh_private_case(before, latest, admit=False)
                self.lib.test055_mutate(self.engine, field, limit)
                self.observe(latest, number=70, start=30617198203458, end=30617216601291)
                self.assertEqual(5, self.scene_details()[-1].validation)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                retired = next(row for row in self.events() if row.command.id == old.id)
                self.assertEqual((bytes(old), 3, 0), (bytes(retired.command), retired.outcome, retired.begin_ns))
                self.assertEqual(wait.deadline_ns, self.motion_wait().deadline_ns)


if __name__ == '__main__': unittest.main()
