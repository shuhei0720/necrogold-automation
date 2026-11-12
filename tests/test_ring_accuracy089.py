"""Derived synthetic accuracy boundaries; no independent positive holdout.

The fixtures redraw frozen features. Brightness/position variations and missing
text test intended witness joining and candidate retention, not unknown-run
recognition accuracy or iSH speed. No rare real target farming is required.
"""
from contextlib import ExitStack
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import ring_native as ring, target_assessment as target
from tests.test_target_assessment087 import FEATURES, png, shop

RUNNER_PREFIX = []


def gained(pixels, gain):
    result = bytearray(pixels)
    for at in range(0, len(result), 4):
        for channel in range(3):
            result[at+channel] = min(255, round(result[at+channel]*gain))
    return bytes(result)


class RingAccuracy089Tests(unittest.TestCase):
    def test_readable_translated_dimmed_same_slot_targets_and_partial_name_candidate(self):
        with tempfile.TemporaryDirectory(prefix='ring-accuracy089-') as home, ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'home', return_value=Path(home)))
            if RUNNER_PREFIX:
                stack.enter_context(patch.object(ring, '_popen',
                    side_effect=lambda argv, **kwargs: subprocess.Popen(list(RUNNER_PREFIX)+argv, **kwargs)))
            cases = [(360,80,.75,1,()), (250,200,.9,1,()),
                     (360,80,1.15,1,()), (250,200,.9,2,(2,))]
            for left, sy, gain, named_slot, extra_icons in cases:
                with self.subTest(left=left, sign_y=sy, gain=gain, named_slot=named_slot):
                    pixels = shop(left=left, sign_y=sy, word_slot=named_slot, extra_icon_slots=extra_icons)
                    value = target.classify_png(png(gained(pixels, gain)))
                    self.assertEqual('target', value['outcome'])
                    self.assertEqual([left,sy], value['row'])
                    self.assertEqual(named_slot, value['word']['slot'])
                    self.assertGreaterEqual(value['slots'][named_slot]['icon_score'], .88)
                    self.assertGreaterEqual(value['word']['iou'], .82)
                    self.assertGreaterEqual(value['word']['coverage'], .90)
            left, sy = 250, 200
            pixels = bytearray(shop(left=left, sign_y=sy))
            rows = [int(row,16) for row in FEATURES['word']['rows_hex']]
            removed = sum(bin(row).count('1') for row in rows[:4])
            self.assertEqual(70, removed)
            self.assertLess((FEATURES['word']['ink']-removed)/FEATURES['word']['ink'], .90)
            # Remove only the upper four glyph rows' ink. Merchandise and
            # prices lie below this ROI and retain their original bytes.
            for dy, bits in enumerate(rows[:4]):
                for dx in range(84):
                    if bits >> dx & 1:
                        at = 4*((sy+11+dy)*896+left+36-42+dx)
                        pixels[at:at+4] = bytes((12,8,7,255))
            value = target.classify_png(png(bytes(pixels)))
            self.assertEqual('candidate', value['outcome'])
            self.assertEqual('icon_only', value['reason'])
            self.assertGreaterEqual(value['slots'][1]['icon_score'], .80)
            self.assertNotEqual('target', value['outcome'])


if __name__ == '__main__': unittest.main()
