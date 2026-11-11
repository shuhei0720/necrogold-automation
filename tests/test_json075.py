"""TEST075 JSON work and validation contracts.

Line work is a deterministic proxy for Python interpreter overhead on numeric
status replies. It does not measure iSH elapsed time or prove a two-second RPC.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from necroprobe import validation


class JSON075Tests(unittest.TestCase):
    def python_work(self, raw):
        """Count parser-module Python work while preserving any outer tracer."""
        source = str(Path(validation.__file__).resolve())
        lines = 0

        def trace(frame, event, _argument):
            nonlocal lines
            if frame.f_code.co_filename != source:
                return None
            if event == 'line':
                lines += 1
            return trace

        previous = sys.gettrace()
        sys.settrace(trace)
        try:
            result = validation.json_object(raw)
        finally:
            sys.settrace(previous)
        return lines, result

    def test_numeric_status_work_does_not_grow_with_ns_digit_count(self):
        measurements = []
        for stamp in (1, 2**63-1):
            expected = {'captures': [stamp]*1000}
            raw = json.dumps(expected, separators=(',', ':')).encode()
            lines, result = self.python_work(raw)
            self.assertEqual(expected, result)
            self.assertGreater(lines, 0)
            measurements.append(lines)
        # Both payloads have the same number and types of nodes. Integer-byte
        # scanning belongs in the native tokenizer, not an interpreter loop.
        self.assertLessEqual(measurements[1], measurements[0]*1.5,
            'numeric status parsing must not amplify Python work with timestamp length')

    def test_short_long_unicode_and_escaped_keys_keep_the_same_values(self):
        for length in (0, 1, 127, 128, 129, 1024):
            for key in ('k'*length, '😀'*length, 'key["\\:'*length):
                for ensure_ascii in (True, False):
                    with self.subTest(length=length, key_family=key[:8], ensure_ascii=ensure_ascii):
                        expected = {key: ['["not syntax]\\"', None, True, 2**63-1, 1e-309]}
                        raw = json.dumps(expected, ensure_ascii=ensure_ascii).encode()
                        self.assertEqual(expected, validation.json_object(raw))

    def test_overflow_duplicate_and_root_type_keep_error_precedence(self):
        cases = (
            (b'{"x":1e9999}', 'nonfinite_json'),
            (b'{"x":-1e9999}', 'nonfinite_json'),
            (b'{"x":NaN}', 'nonfinite_json'),
            (b'{"x":Infinity}', 'nonfinite_json'),
            (b'{"x":-Infinity}', 'nonfinite_json'),
            (b'{"x":1,"x":1e9999}', 'duplicate_json_key'),
            (b'{"x":1e9999,"x":1}', 'duplicate_json_key'),
            (b'{"x":1,"\\u0078":1e9999}', 'duplicate_json_key'),
            (b'[1e9999]', 'json_object_required'),
            (b'{"x":1e9999,"y":NaN}', 'nonfinite_json'),
        )
        for raw, code in cases:
            with self.subTest(raw=raw), self.assertRaisesRegex(validation.ProbeError, '^'+code+'$'):
                validation.json_object(raw)
        for value in (0.0, -0.0, 1e308, 1e-309):
            expected = {'x': value}
            self.assertEqual(expected, validation.json_object(json.dumps(expected).encode()))

    def test_depth_and_node_limits_reject_before_object_allocation(self):
        invalid = (
            (b'{"x":'+b'['*16+b'0'+b']'*16+b'}', 'json_depth'),
            (b'{"x":['+b'0,'*9998+b'0]}', 'json_nodes'),
        )
        for raw, code in invalid:
            with self.subTest(code=code), patch.object(validation.json, 'loads') as loads:
                with self.assertRaisesRegex(validation.ProbeError, '^'+code+'$'):
                    validation.json_object(raw)
                loads.assert_not_called()
        self.assertEqual(9998, len(validation.json_object(
            b'{"x":['+b'0,'*9997+b'0]}')['x']))
        self.assertEqual({'x': [[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]},
            validation.json_object(b'{"x":'+b'['*15+b'0'+b']'*15+b'}'))

    def test_raw_size_utf8_and_invalid_strings_are_still_rejected(self):
        for raw in (b'', b'\xff', b'{"x":"bad\\q"}', b'{"x":"bad\x00"}',
                    b'{"x":01}', b'{"x":1:2}', b'{}{}'):
            with self.subTest(raw=raw), self.assertRaises(validation.ProbeError):
                validation.json_object(raw)
        for raw in ('{}', bytearray(b'{}')):
            with self.subTest(kind=type(raw)), self.assertRaisesRegex(validation.ProbeError, '^json_size$'):
                validation.json_object(raw)
        self.assertEqual({}, validation.json_object(b'{}', 2))
        with self.assertRaisesRegex(validation.ProbeError, '^json_size$'):
            validation.json_object(b'{}', 1)
