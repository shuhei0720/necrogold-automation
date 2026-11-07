"""TEST039: 同じ記録のcompact保存。ホスト経路検査は端末の速度証明ではない。"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import session, shop_walk as walk
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
import test_shop_walk as old


TEST038_REPORT_SHA256 = '6851c99101f7c04ffd9b06b906a5cc9a0b0f02f6095c28e02bdf34dbecff4ef1'


def nested_payload():
    """Schema-independent serialization fixture; strings retain meaningful spaces."""
    return {
        'phase': 'walk', '日本語': '商品 確認\n呪いの指輪🪙',
        'walk': {'input_pending': True, 'actions': [
            {'outcome': 'unknown', 'target_ns': 202845721411000,
             'rpc_timings': {}, 'target_checks': [
                 {'window': {'frame_ns': 202840000000000}, 'status': 'ready'}]},
            {'outcome': 'acknowledged', 'scheduled_inputs': 1}],
            'samples': [None, False, True, 0, -7, 1, 1.0, 0.0, -0.0, .521719,
                        1e-30, 2**53 + 1, 2**63 - 1]},
        'checkpoint_ms': [18.671, 104.8275, 176.675],
    }


def schema_report():
    start = 2**53 + 123
    report = walk.new_report(start, 'd' * 32)
    report['phase'] = 'walk'
    report['end_ns'] = 2**63 - 1
    report['search']['capture_ms'] = [0, 1.0, -0.0, 777.806]
    report['search']['checkpoint_ms'] = [18.671, 104.8275, 176.675]
    report['walk']['started_ns'] = start + 1
    report['walk']['navigation_ms'] = [0, 1.0, 301.156]
    report['walk']['motion_ms'] = [178.856]
    return report


class CheckpointEncodingTests(unittest.TestCase):
    def assert_json_identical(self, expected, actual):
        """Equality alone would hide float/int conversion and negative-zero loss."""
        self.assertIs(type(expected), type(actual))
        if type(expected) is dict:
            self.assertEqual(set(expected), set(actual))
            for key in expected:
                self.assert_json_identical(expected[key], actual[key])
        elif type(expected) is list:
            self.assertEqual(len(expected), len(actual))
            for before, after in zip(expected, actual):
                self.assert_json_identical(before, after)
        elif type(expected) is float:
            self.assertEqual(expected.hex(), actual.hex())
        else:
            self.assertEqual(expected, actual)

    @unittest.skipUnless(platform.python_implementation() == 'CPython'
                         and json.encoder.c_make_encoder is not None,
                         'CPython C encoder is required for this host path check')
    def test_public_write_avoids_python_iterative_encoder(self):
        report = nested_payload()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(json.encoder, '_make_iterencode',
                              wraps=json.encoder._make_iterencode) as python_encoder:
                walk.write(folder, report)
            self.assertEqual(0, python_encoder.call_count)
            raw = (Path(folder) / 'report.json').read_bytes()
            self.assert_json_identical(report, json.loads(raw))
            self.assertIn('商品 確認'.encode('utf-8'), raw)
            self.assertNotIn(b'\n', raw)

    def test_atomic_write_receives_complete_utf8_bytes_at_default_and_custom_name(self):
        report = nested_payload()
        before = deepcopy(report)
        # Explicit iterative encoding is an independent, existing-value reference.
        pretty = ''.join(json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                                         indent=2).iterencode(report)).encode('utf-8')
        with tempfile.TemporaryDirectory() as folder:
            for name in ('report.json', 'parent-result.json'):
                with self.subTest(name=name), patch.object(
                        walk.base, 'atomic_write', wraps=walk.base.atomic_write) as atomic:
                    if name == 'report.json':
                        walk.write(folder, report)
                    else:
                        walk.write(folder, report, name)
                    self.assertEqual(1, atomic.call_count)
                    path, raw = atomic.call_args.args
                    self.assertEqual(Path(folder) / name, path)
                    self.assertIs(type(raw), bytes)
                    self.assertEqual(raw, path.read_bytes())
                    self.assert_json_identical(json.loads(pretty), json.loads(raw))
                    self.assertLess(len(raw), len(pretty))
                    self.assertIn('呪いの指輪🪙'.encode('utf-8'), raw)
                    self.assertNotIn(b'\n', raw)
                    self.assertNotIn(b'": ', raw)
                    self.assertNotIn(b', ', raw)
            self.assertEqual({'report.json', 'parent-result.json'},
                             {path.name for path in Path(folder).iterdir()})
        self.assert_json_identical(before, report)

    def test_current_schema_and_numeric_types_survive_roundtrip(self):
        report = schema_report()
        with tempfile.TemporaryDirectory() as folder:
            walk.write(folder, report)
            parsed = walk.read_report(Path(folder) / 'report.json',
                                      report['run_id'], report['start_ns'])
        self.assert_json_identical(report, parsed)

    def test_schema_rejection_is_unchanged_by_compact_whitespace(self):
        report = schema_report()
        report['walk']['input_pending'] = 'true'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.json'
            path.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2),
                            encoding='utf-8')
            with self.assertRaises(ValueError) as pretty_error:
                walk.read_report(path, report['run_id'], report['start_ns'])
            walk.write(folder, report)
            with self.assertRaises(ValueError) as compact_error:
                walk.read_report(path, report['run_id'], report['start_ns'])
        self.assertEqual(str(pretty_error.exception), str(compact_error.exception))

    def test_without_c_encoder_fallback_preserves_all_values(self):
        report = nested_payload()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(json.encoder, 'c_make_encoder', None), patch.object(
                    json.encoder, '_make_iterencode',
                    wraps=json.encoder._make_iterencode) as python_encoder:
                walk.write(folder, report)
            self.assertGreater(python_encoder.call_count, 0)
            raw = (Path(folder) / 'report.json').read_bytes()
            self.assert_json_identical(report, json.loads(raw))
            self.assertIn('日本語'.encode('utf-8'), raw)
            self.assertNotIn(b'\n', raw)

    def test_nonfinite_values_never_reach_atomic_write_or_replace_existing_report(self):
        encoders = [('available', json.encoder.c_make_encoder), ('fallback', None)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.json'
            old_bytes = b'{"previous":"safe report"}\n'
            path.write_bytes(old_bytes)
            for encoder_name, encoder in encoders:
                for value in (float('nan'), float('inf'), -float('inf')):
                    with self.subTest(encoder=encoder_name, value=value):
                        report = nested_payload()
                        report['walk']['actions'][0]['rpc_timings']['http_end_ns'] = value
                        with patch.object(json.encoder, 'c_make_encoder', encoder), patch.object(
                                walk.base, 'atomic_write', wraps=walk.base.atomic_write) as atomic:
                            with self.assertRaises(ValueError):
                                walk.write(folder, report)
                        atomic.assert_not_called()
                        self.assertEqual(old_bytes, path.read_bytes())
                        self.assertEqual(['report.json'], [p.name for p in Path(folder).iterdir()])

    def test_partial_temporary_write_failure_preserves_previous_file_and_removes_temp(self):
        real_fdopen = session.os.fdopen

        class PartialWriter:
            def __init__(self, fd, mode):
                self.file = real_fdopen(fd, mode)

            def __enter__(self):
                self.file.__enter__()
                return self

            def write(self, raw):
                self.file.write(raw[:7])
                self.file.flush()
                raise OSError('injected partial temporary write failure')

            def __exit__(self, *args):
                return self.file.__exit__(*args)

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.json'
            old_bytes = b'{"previous":"safe report"}\n'
            path.write_bytes(old_bytes)
            with patch.object(session.os, 'fdopen', side_effect=PartialWriter), patch.object(
                    session.os, 'replace', wraps=session.os.replace) as replace:
                with self.assertRaises(OSError):
                    walk.write(folder, nested_payload())
            replace.assert_not_called()
            self.assertEqual(old_bytes, path.read_bytes())
            self.assertEqual(['report.json'], [p.name for p in Path(folder).iterdir()])

    def test_replace_failure_preserves_previous_file_and_removes_complete_temp(self):
        report = nested_payload()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.json'
            old_bytes = b'{"previous":"safe report"}\n'
            path.write_bytes(old_bytes)
            checked = []

            def fail_replace(source, target):
                self.assertEqual(path, Path(target))
                self.assertEqual(old_bytes, path.read_bytes())
                self.assert_json_identical(report, json.loads(Path(source).read_bytes()))
                checked.append(Path(source))
                raise OSError('injected atomic replacement failure')

            with patch.object(session.os, 'replace', side_effect=fail_replace):
                with self.assertRaises(OSError):
                    walk.write(folder, report)
            self.assertEqual(1, len(checked))
            self.assertFalse(checked[0].exists())
            self.assertEqual(old_bytes, path.read_bytes())
            self.assertEqual(['report.json'], [p.name for p in Path(folder).iterdir()])

    def test_actual_test038_report_preserves_values_and_validates_with_current_identity(self):
        source = os.environ.get('NECRO_TEST038_REPORT')
        if not source and os.environ.get('NECRO_TEST038_FRAMES'):
            source = str(Path(os.environ['NECRO_TEST038_FRAMES']) / 'report.json')
        if not source:
            self.skipTest('external TEST038 report not supplied')
        original = Path(source).read_bytes()
        self.assertEqual(TEST038_REPORT_SHA256, hashlib.sha256(original).hexdigest())
        report = json.loads(original)
        self.assertEqual('TEST-038', report['test_id'])
        before = deepcopy(report)
        with tempfile.TemporaryDirectory() as folder:
            walk.write(folder, report)
            raw = (Path(folder) / 'report.json').read_bytes()
            self.assert_json_identical(report, json.loads(raw))
            self.assertLess(len(raw), len(original))
            self.assert_json_identical(before, report)
            # Only adapt the old outer identity for today's strict validator.
            # The hash-checked TEST038 record above is preserved without edits.
            current = deepcopy(report)
            identity = walk.new_report(current['start_ns'], current['run_id'])
            current['test_id'] = identity['test_id']
            current['revision'] = identity['revision']
            current['startup'] = identity['startup']
            walk.write(folder, current, 'parent-result.json')
            parsed = walk.read_report(Path(folder) / 'parent-result.json',
                                      current['run_id'], current['start_ns'])
            self.assert_json_identical(current, parsed)


class CheckpointControlTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    def test_pending_bytes_are_persisted_before_rpc_and_unknown_prevents_retry_or_cleanup(self):
        # Actual Driver/serializer/atomic_write with simulated transport and images.
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (
                driver, now, captures, scenes, sent):
            before, model = driver.synchronize(driver.observe())
            call = driver.client.call
            persisted_before_rpc = []

            def unknown_rpc(method, params, timeout):
                if method != 'run_steps':
                    return call(method, params, timeout)
                saved = walk.read_report(Path(folder) / 'report.json',
                                         driver.outer['run_id'], driver.outer['start_ns'])
                self.assertTrue(saved['walk']['input_pending'])
                self.assertEqual('unknown', saved['walk']['actions'][-1]['outcome'])
                self.assertIsNone(saved['walk']['actions'][-1]['issued_ns'])
                persisted_before_rpc.append(saved)
                call(method, params, timeout)
                return RpcReply({}, {})

            with patch.object(driver.client, 'call', side_effect=unknown_rpc):
                with self.assertRaises(ProbeError) as caught:
                    driver.perform('left', before, model)
                self.assertEqual('batch_unknown', caught.exception.code)
                self.assertTrue(driver.pending)
                saved = walk.read_report(Path(folder) / 'report.json',
                                         driver.outer['run_id'], driver.outer['start_ns'])
                self.assertTrue(saved['walk']['input_pending'])
                self.assertEqual('unknown', saved['walk']['actions'][-1]['outcome'])
                self.assertIsNotNone(saved['walk']['actions'][-1]['issued_ns'])
                calls_before_finish = len(driver.client.calls)
                driver.finish('batch_unknown', None)
                self.assertEqual(calls_before_finish, len(driver.client.calls))
                with self.assertRaises(ProbeError):
                    driver.perform('left', before, model)
            self.assertEqual(1, len(persisted_before_rpc))
            self.assertEqual(1, len(sent))
            self.assertTrue(driver.state['input_pending'])


if __name__ == '__main__':
    unittest.main()
