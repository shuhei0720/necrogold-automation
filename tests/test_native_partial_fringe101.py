"""Clipped duplicate top-row collapse through the complete public-C path.

All Scenes/results/clocks are procedural. The source546/549 case supplies
the paired-row premise; these tests do not invent subsequent phone arrival.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_entry097 as entry
from tests import test_native_partial_framing097 as framing


class NativePartialFringe101Tests(unittest.TestCase):
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

    def pending(self, direction=3, opened=True, extra_margin=False):
        items = {(x, y) for x in range(-3, 4) for y in (-5, -4)}
        if extra_margin: items.add((-4, -4))
        cells, protected = framing.NativePartialFraming097Tests.envelope(
            items)
        terrain, opening = self.p.pending(direction=direction, opened=opened,
            extra=cells, protected=protected)
        self.assertEqual((3, 0), (self.q.cycle().state, self.q.cycle().completed_shops))
        self.p.observe(terrain)
        self.assertEqual(0, self.q.cycle().state, 'a separate original static image first grants ordinary partial credit')
        return terrain, opening, self.q.cycle()

    @staticmethod
    def collapse(terrain):
        changed = deepcopy(terrain)
        for x, kind in zip(range(-3, 4), (None, 'floor', 'dirt', None, 'dirt', 'floor', None)):
            if kind is None: changed.tiles.pop((x, -5), None)
            else: changed.tiles[(x, -5)] = kind
        changed.protected.difference_update({(-4, -5), (4, -5)})
        return changed

    def test_adopted_partial_credit_survives_later_duplicate_top_collapse_to_future_input(self):
        terrain, opening, source = self.pending()
        changed = self.collapse(terrain)
        before = self.h.status()
        self.p.observe(changed)
        self.assertEqual((0, 0, 0), (self.q.cycle().state, self.h.status().reason, self.h.status().terminal),
            'paired protected lower merchandise keeps the later clipped top alias from terminating existing credit')
        current = self.q.cycle()
        self.assertEqual((source.job_id, source.capture_id, source.prefix, source.continuation_deadline_ns),
            (current.job_id, current.capture_id, current.prefix, current.continuation_deadline_ns))
        self.assertEqual((before.inputs, before.moves), (self.h.status().inputs, self.h.status().moves))
        command = self.h.next_move(changed)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.id, opening.id)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opening.id, self.h.now, 1, 0, 1))
        self.h.ack(command)
        self.assertEqual((before.inputs + 1, before.moves), (self.h.status().inputs, self.h.status().moves))

    def test_real_lower_item_and_protection_loss_are_not_duplicate_top_aliases(self):
        for fault in ('lower_item', 'lower_protection', 'old_top_protection', 'unpaired_top',
                      'gold', 'outside', 'near', 'lower_extra_margin'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _, old = self.pending(extra_margin=fault == 'lower_extra_margin')
                changed = self.collapse(terrain)
                if fault == 'lower_item': changed.tiles[(0, -4)] = 'floor'
                elif fault == 'lower_protection': changed.protected.discard((0, -4))
                elif fault == 'old_top_protection': changed.protected.discard((0, -5))
                elif fault == 'unpaired_top': changed.tiles[(4, -5)] = 'item'; changed.protected.add((4, -5))
                elif fault == 'gold': changed.tiles[(1, -1)] = 'floor'
                elif fault == 'outside': changed.tiles[(8, 3)] = 'dirt'
                elif fault == 'near': changed.tiles[(1, 0)] = 'dirt'
                self.p.observe(changed)
                if fault == 'outside':
                    # TEST107 composes the supported top alias with the
                    # already admitted remote STONE->DIRT relation. Neither
                    # the frozen job nor its original horizon is renewed.
                    self.assertEqual((old.job_id, 0, old.continuation_deadline_ns),
                        (self.q.cycle().job_id, self.q.cycle().state,
                         self.q.cycle().continuation_deadline_ns))
                    self.assertEqual((4, 3),
                        (self.h.next_move(changed).kind, self.h.events()[-1].command.direction))
                else:
                    self.assertEqual((old.job_id, 7), (self.q.cycle().job_id, self.q.cycle().state))
                    self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_only_top_floor_dirt_unknown_or_item_with_explained_outer_margin_is_allowed(self):
        for fault in ('stone', 'gold', 'door', 'new_protection', 'outer_material', 'outer_other_row'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _, _ = self.pending()
                changed = self.collapse(terrain)
                if fault in ('stone', 'gold', 'door'): changed.tiles[(0, -5)] = fault
                elif fault == 'new_protection': changed.protected.add((5, -5))
                elif fault == 'outer_material': changed.tiles[(4, -5)] = 'floor'
                elif fault == 'outer_other_row': changed.protected.discard((4, -4))
                self.p.observe(changed)
                self.assertEqual(7, self.q.cycle().state)

    def test_non_up_unopened_or_ineligible_motion_and_original_guards_do_not_continue(self):
        for fault in ('non_up', 'no_ack', 'motion', 'unknown', 'prefix', 'unstable', 'deadline', 'cancel'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _, old = self.pending(direction=1 if fault == 'non_up' else 3,
                                               opened=fault != 'no_ack')
                changed = self.collapse(terrain)
                if fault == 'motion': changed.signature = native.translated(terrain, 3).signature
                elif fault == 'unknown': changed.signature = bytes([80]) * 23296
                elif fault == 'deadline': self.h.now = old.continuation_deadline_ns + 1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                self.p.observe(changed, **({'prefix': self.h.prefix + 1} if fault == 'prefix' else
                                          {'stable': 0} if fault == 'unstable' else {}))
                if fault in ('prefix', 'unstable'):
                    self.assertEqual(0, self.q.cycle().state)
                else:
                    self.assertNotEqual(0, self.q.cycle().state)
                    self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_empty_unknown_framing_does_not_inherit_the_nonempty_partial_alias_relation(self):
        f = framing.NativePartialFraming097Tests(methodName='runTest')
        f.p, f.h, f.q, f.lib = self.p, self.h, self.q, self.lib
        terrain, _ = f.pending()
        f.admitted()
        f.p.observe(terrain)
        self.assertEqual(0, self.q.cycle().state)
        changed = deepcopy(terrain); changed.tiles[(0, -5)] = 'floor'
        f.p.observe(changed)
        self.assertEqual(7, self.q.cycle().state)


if __name__ == '__main__':
    unittest.main()
