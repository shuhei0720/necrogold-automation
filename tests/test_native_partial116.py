"""TEST116: normal pixel top projection, before/after unused observation credit.

Clocks/world responses are procedural; TEST115 received PNGs are calibrated
separately. These cases do not claim unrecorded future iPhone acceptance.
"""
import ctypes as C
import unittest

from tests import test_native_shop115 as shop115


class NativePartial116Tests(unittest.TestCase):
    PERIOD, SYNTH, RESPONSE = shop115.NativeShop115Tests.PERIOD, shop115.NativeShop115Tests.SYNTH, shop115.NativeShop115Tests.RESPONSE

    @classmethod
    def setUpClass(cls):
        shop115.NativeShop115Tests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        shop115.NativeShop115Tests.tearDownClass.__func__(cls)

    for _name in ('normal_commit', 'partial_source', 'partial_frame',
                  'partial_pending', 'queue_partial', 'no_move_or_restart',
                  'exact_mask'):
        locals()[_name] = getattr(shop115.NativeShop115Tests, _name)
    tile_index = staticmethod(shop115.NativeShop115Tests.tile_index)

    def current_after_credit(self):
        self.partial_pending()
        self.partial_frame(2)
        self.assertEqual(0, self.q.cycle().state, 'old unused observation is already qualified')
        self.latest_pixels, self.latest = self.partial_frame(3)
        state = self.q.cycle()
        self.assertEqual(self.root.job_id+1, state.job_id,
            'the same top projection transition after qualification needs its own DATA epoch')
        self.assertEqual((1, self.h.number, self.root.prefix),
            (state.pending, state.capture_id, state.prefix))
        self.assertLessEqual(state.continuation_deadline_ns, self.root.continuation_deadline_ns)
        self.assertEqual(self.before_counts, (self.h.status().inputs, self.h.status().moves))

    def test_top_transition_after_unused_credit_starts_independent_data(self):
        self.current_after_credit()
        result = self.normal_commit(self.latest_pixels, self.latest)
        self.assertEqual((0, 1), (result.outcome, result.coverage))
        self.no_move_or_restart()

    def test_issued_but_unbegun_credit_is_retired_without_refunding_an_input(self):
        self.partial_pending()
        self.partial_frame(2)
        for _ in range(100):
            ready, old = self.h.tick()
            if ready:
                self.assertEqual((4, 3), (old.kind, old.direction))
                break
            self.partial_frame(2)
        else:
            self.fail('no old framing ticket was issued for the boundary test')
        self.assertEqual(1, self.h.status().input_state)
        self.latest_pixels, self.latest = self.partial_frame(3)
        state = self.q.cycle()
        self.assertEqual((self.root.job_id+1, 1), (state.job_id, state.pending))
        self.assertEqual((self.before_counts, 0),
            ((self.h.status().inputs, self.h.status().moves), self.h.status().input_state))
        self.assertEqual((3, 0), (self.h.events()[-1].outcome, self.h.events()[-1].begin_ns))
        self.assertEqual(0, self.lib.ng2_controller_begin(
            self.h.engine, old.id, max(self.h.now, old.not_before_ns), 1, 0, 1))
        self.assertLessEqual(state.continuation_deadline_ns, self.root.continuation_deadline_ns)
        self.normal_commit(self.latest_pixels, self.latest)
        self.no_move_or_restart()

    def test_reverse_top_relation_rejects_unexplained_goods_floor_gold_and_motion(self):
        for fault in ('lower_item', 'outside_item', 'outside_protection', 'top_gold',
                      'lower_gold', 'unknown_up', 'motion', 'prefix', 'parent'):
            with self.subTest(fault=fault):
                self.queue_partial()
                self.normal_commit(self.latest_pixels, self.latest)
                original = self.q.cycle()
                _pixels, scene = self.partial_source(2)
                if fault == 'lower_item':
                    scene.tiles[self.tile_index(-1, -4)] = 1
                    self.exact_mask(scene)
                elif fault == 'outside_item':
                    scene.tiles[self.tile_index(5, -4)] = 6
                    self.exact_mask(scene)
                elif fault == 'outside_protection': scene.protected_cells[self.tile_index(7, 2)] = 1
                elif fault == 'top_gold': scene.tiles[self.tile_index(-1, -5)] = 2
                elif fault == 'lower_gold': scene.tiles[self.tile_index(1, -2)] = 4
                elif fault == 'unknown_up': scene.tiles[self.tile_index(0, -1)] = 0
                elif fault == 'motion':
                    scene.signature[:] = bytes((37*i+71) % 251 for i in range(len(scene.signature)))
                if fault == 'parent': self.h.now = original.continuation_deadline_ns+1
                else: self.h.now += 20_000_000
                self.h.observe_actual(scene,
                    prefix=self.h.prefix+1 if fault == 'prefix' else self.h.prefix)
                self.no_move_or_restart()
                self.assertEqual((original.job_id, original.capture_id),
                    (self.q.cycle().job_id, self.q.cycle().capture_id))
                self.assertEqual(self.before_counts, (self.h.status().inputs, self.h.status().moves))

    def test_reverse_top_projection_keeps_fixed_epoch_and_original_one_up(self):
        self.queue_partial()
        self.normal_commit(self.latest_pixels, self.latest)
        source = self.q.cycle()
        self.partial_frame(2)
        self.assertEqual(0, self.q.cycle().status,
            'lower-supported top duplicate flicker inside the original potential is not hard drift')
        self.assertEqual((source.job_id, source.capture_id, source.continuation_deadline_ns),
            (self.q.cycle().job_id, self.q.cycle().capture_id,
             self.q.cycle().continuation_deadline_ns), 'no new source, job or time')
        for _ in range(100):
            ready, command = self.h.tick()
            if ready:
                self.assertEqual((4, 3), (command.kind, command.direction))
                break
            self.partial_frame(2)
        else:
            self.fail('the one unused current observation did not continue through top flicker')
        self.h.ack(command)
        self.h.now = max(self.h.now, command.target_ns+100_000_000)
        pixels, scene = self.partial_frame(5, advance=0)
        self.assertEqual((1, 0, -1), (self.h.events()[-1].motion,
            self.h.events()[-1].dx, self.h.events()[-1].dy))
        result = self.normal_commit(pixels, scene)
        self.assertEqual((3, 2), (result.outcome, result.coverage))
        self.assertEqual((self.before_counts[0]+1, self.before_counts[1]+1),
            (self.h.status().inputs, self.h.status().moves))
        self.q.pause_observed()
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(1, self.q.intent(restart))


if __name__ == '__main__':
    unittest.main()
