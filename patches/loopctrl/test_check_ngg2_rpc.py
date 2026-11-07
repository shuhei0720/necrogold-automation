"""API mutation verifier must never count a compile/runner failure as Red."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ngg2_rpc_checker', HERE / 'check_ngg2_rpc.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class NGG2RPCVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.output = Path(self.temp.name) / 'output'
        self.source = self.root / 'LoopCtrlKit/JSONRPCServer.swift'
        self.source.parent.mkdir(parents=True)
        self.original = ('// fixture\n' + checker.TARGET + '\n').encode()
        self.source.write_bytes(self.original)

    def execute(self, code, stdout, stderr=''):
        result = subprocess.CompletedProcess(['xcodebuild'], code, stdout, stderr)
        with patch.object(sys, 'argv', ['check_ngg2_rpc.py', str(self.root), str(self.output)]), \
                patch.object(checker.subprocess, 'run', return_value=result), patch('builtins.print'):
            try:
                checker.main()
            finally:
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_expected_executed_assertion_is_recorded_and_original_restored(self):
        self.execute(65, checker.EXPECTED + '\nExecuted 1 test, with 5 failures\n** TEST FAILED **\n')
        self.assertTrue((self.output / 'ngg2-rpc-callsite-contract.json').is_file())

    def test_compile_failure_is_not_behavioral_red(self):
        with self.assertRaisesRegex(RuntimeError, 'assertion_red_not_observed'):
            self.execute(65, 'error: could not compile JSONRPCServer.swift\n** BUILD FAILED **\n')
        self.assertFalse((self.output / 'ngg2-rpc-callsite-contract.json').exists())

    def test_runner_failure_with_marker_but_no_executed_assertion_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'assertion_red_not_observed'):
            self.execute(65, checker.EXPECTED + '\n** TEST FAILED **\n')

    def test_mutant_success_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'assertion_red_not_observed'):
            self.execute(0, 'Executed 1 test, with 0 failures\n** TEST SUCCEEDED **\n')

    def test_timeout_restores_original_source(self):
        with patch.object(sys, 'argv', ['check_ngg2_rpc.py', str(self.root), str(self.output)]), \
                patch.object(checker.subprocess, 'run', side_effect=subprocess.TimeoutExpired('xcodebuild', 300)):
            with self.assertRaises(subprocess.TimeoutExpired):
                checker.main()
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
