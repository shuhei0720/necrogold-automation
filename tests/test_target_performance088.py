"""Equivalent scoring with bounded Python-call overhead, not device timing."""
import cProfile
import inspect
import unittest

from necroprobe import target_assessment as target
from tests.test_target_assessment087 import png, shop


class TargetPerformance088Tests(unittest.TestCase):
    def test_complete_shop_keeps_exact_result_without_per_sample_generators(self):
        data = png(shop())
        profiler = cProfile.Profile()
        result = profiler.runcall(target.classify_png, data)
        self.assertEqual(dict(outcome='target', reason='icon_and_name', row=[470, 120],
            slots=[dict(slot=0, icon_score=.344309933, icon_box=[448, 177, 32, 28]),
                   dict(slot=1, icon_score=1., icon_box=[488, 154, 33, 28]),
                   dict(slot=2, icon_score=.344309933, icon_box=[520, 177, 32, 28])],
            word=dict(slot=1, iou=1., coverage=1., box=[464, 131, 84, 11])), result)
        lines, first = inspect.getsourcelines(target._icon)
        generator_calls = sum(entry.callcount for entry in profiler.getstats()
            if hasattr(entry.code, 'co_name') and entry.code.co_name == '<genexpr>'
            and entry.code.co_filename == target._icon.__code__.co_filename
            and first <= entry.code.co_firstlineno < first+len(lines))
        # Four rows, three slots, three sprites, 34x17 placements: allow one
        # generator per placement, never one generator per sampled RGB point.
        self.assertLessEqual(generator_calls, 4*3*3*34*17,
                             'RGB sampling must not create millions of Python generator calls')

    def test_equal_raw_upper_bound_keeps_first_box_and_checks_each_scan_row(self):
        rgba = bytearray(bytes((0, 0, 0, 255))*(target.WIDTH*target.HEIGHT))
        for y in range(124, 160):
            for x in range(76, 130, 2):
                at = 4*(y*target.WIDTH+x)
                rgba[at:at+3] = bytes((200, 100, 20))
        bright = ((0, 0, 200, 100, 20), (2, 0, 200, 100, 20), (4, 0, 200, 100, 20))
        dark = ((1, 0), (3, 0))
        sprite = (32, 28, bright, dark, (320,)*3, 3*(200**2+100**2+20**2), 960, 0.)
        # Every even placement attains the same maximum: equal candidates
        # cannot replace the first box, including the second sprite pass.
        self.assertEqual((.55, [76, 124, 32, 28]),
                         target._icon(rgba, 100, 100, (sprite, sprite), lambda: False))
        calls = [0]
        def cancelled():
            calls[0] += 1
            return calls[0] == 5
        with self.assertRaisesRegex(target.AssessmentError, 'target_cancelled'):
            target._icon(rgba, 100, 100, (sprite, sprite), cancelled)
        self.assertEqual(5, calls[0], 'pruned candidates still reach each row cancellation check')
