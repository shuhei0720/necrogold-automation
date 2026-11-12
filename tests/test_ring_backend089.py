"""Public classifier routes pixel work outside Python; fixtures are procedural."""
import cProfile
from contextlib import ExitStack
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import ring_native as ring, target_assessment as target
from tests.test_target_assessment087 import png, shop

# Developer harness may set this before unittest; product has no runner override.
RUNNER_PREFIX = []


class RingBackend089Tests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        if RUNNER_PREFIX:
            from necroprobe import ring_native
            home = tempfile.TemporaryDirectory(prefix='ring-backend089-')
            self.addCleanup(home.cleanup)
            self.stack.enter_context(patch.object(Path, 'home', return_value=Path(home.name)))
            self.stack.enter_context(patch.object(ring_native, '_popen',
                side_effect=lambda argv, **kwargs: subprocess.Popen(RUNNER_PREFIX+argv, **kwargs)))

    def test_observed_icon_and_name_keep_the_result_without_python_pixel_loops(self):
        data = png(shop()); profiler = cProfile.Profile()
        value = profiler.runcall(target.classify_png, data)
        self.assertEqual('target', value['outcome'])
        self.assertEqual([470, 120], value['row'])
        self.assertEqual([.344309933, 1., .344309933], [s['icon_score'] for s in value['slots']])
        self.assertEqual(dict(slot=1, iou=1., coverage=1., box=[464, 131, 84, 11]), value['word'])
        self.assertTrue(all(type(s['icon_score']) is float for s in value['slots']))
        self.assertIs(float, type(value['word']['iou']), 'canonical sidecars must keep 1.0 rather than 1')
        self.assertIs(float, type(value['word']['coverage']))
        old_pixel_functions = {'decode_png', '_observations', '_icon', '_word'}
        calls = [(entry.code.co_name, entry.callcount) for entry in profiler.getstats()
                 if hasattr(entry.code, 'co_name') and entry.code.co_name in old_pixel_functions
                 and entry.code.co_filename == target.__file__]
        self.assertEqual([], calls,
                         'the device classifier must not repeat image-sized Python pixel loops')

    def test_visible_ring_with_clipped_name_stays_candidate(self):
        data = png(shop(left=18, sign_y=200, name=False, extra_icon_slots=(0,)))
        try:
            value = target.classify_png(data)
        except TypeError as error:
            self.fail('a clipped name must retain the visible ring candidate: '+str(error))
        self.assertEqual('candidate', value['outcome'])
        self.assertEqual('icon_only', value['reason'])
        self.assertEqual([18, 200], value['row'])
        self.assertGreaterEqual(value['slots'][0]['icon_score'], .80)
        self.assertNotEqual('target', value['outcome'])

    def test_active_compiled_decoder_accepts_all_filters_and_rejects_nonopaque_pixels(self):
        pixels = shop()
        for kind in range(5):
            with self.subTest(filter=kind):
                result = target.classify_png(png(pixels, kind))
                self.assertEqual('target', result['outcome'])
                self.assertEqual([470, 120], result['row'])
                self.assertEqual([.344309933, 1., .344309933],
                                 [slot['icon_score'] for slot in result['slots']])
                self.assertEqual(dict(slot=1, iou=1., coverage=1., box=[464, 131, 84, 11]), result['word'])
        alpha = bytearray(pixels)
        alpha[3] = 254  # Outside all merchandise ROIs; every pixel must be checked.
        with self.assertRaisesRegex(target.AssessmentError, '^ring_native_child$'):
            target.classify_png(png(bytes(alpha), 4))

    def test_actual_engine_rejects_truncated_extra_wrong_mode_feature_and_filter_packets(self):
        raw = target._filtered_png(png(shop()), lambda: False)
        header = (b'NG2RING1'+struct.pack('<II', 0, len(raw))
                  +bytes.fromhex(target.FEATURE_SHA256)+hashlib.sha256(raw).digest())
        packet = header+raw
        bad_mode = packet[:8]+struct.pack('<I', 2)+packet[12:]
        bad_feature = packet[:16]+bytes(32)+packet[48:]
        bad_filter = packet[:80]+b'\x05'+packet[81:]
        bad_length = packet[:12]+struct.pack('<I', len(raw)-1)+packet[16:]
        engine = ring._engine(target.FEATURE_SHA256, lambda: False)
        # This invokes the distributed ELF itself, bypassing the parent's input
        # guards to exercise the child's independent boundary checks.
        for label, invalid in (('truncated_header', packet[:79]), ('truncated_pixels', packet[:-1]),
                               ('extra', packet+b'x'), ('mode', bad_mode), ('feature', bad_feature),
                               ('filter', bad_filter), ('length', bad_length)):
            with self.subTest(packet=label):
                child = subprocess.run(list(RUNNER_PREFIX)+[str(engine)],
                    input=invalid, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                    env={}, check=False)
                self.assertEqual(2, child.returncode)
                self.assertEqual(b'', child.stdout)
                self.assertEqual(b'ring_native_invalid\n', child.stderr)


if __name__ == '__main__':
    unittest.main()
