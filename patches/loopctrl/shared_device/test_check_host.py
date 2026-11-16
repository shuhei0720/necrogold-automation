"""Only the observed public Mac VM line may precede the exact Red assertion."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('normal_host_red_parser',HERE/'check_host.py')
host=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(host)


class ExactRedProofTests(unittest.TestCase):
    def result(self,stderr,*,code=1,stdout=''):
        return subprocess.CompletedProcess(['public-fixture'],code,stdout,stderr)

    def test_exact_assertion_without_vm_line_passes_and_keeps_full_text(self):
        proof=host.gap_red_proof(self.result(host.EXPECTED_GAP_RED))
        self.assertEqual(host.EXPECTED_GAP_RED,proof['stderr'])
        self.assertFalse(proof['observed_scaler_vm_line'])

    def test_one_observed_vm_prefix_passes_and_is_preserved(self):
        stderr=host.OBSERVED_SCALER_VM_LINE+host.EXPECTED_GAP_RED
        try:proof=host.gap_red_proof(self.result(stderr))
        except RuntimeError:outcome='rejected'
        else:
            outcome='accepted'
            self.assertEqual(stderr,proof['stderr'])
            self.assertTrue(proof['observed_scaler_vm_line'])
        self.assertEqual('accepted',outcome)

    def test_other_or_repeated_lines_and_other_failures_remain_rejected(self):
        for stderr in (host.OBSERVED_SCALER_VM_LINE*2+host.EXPECTED_GAP_RED,
                       host.EXPECTED_GAP_RED+host.OBSERVED_SCALER_VM_LINE,
                       'unknown warning\n'+host.EXPECTED_GAP_RED,
                       host.OBSERVED_SCALER_VM_LINE+'FAIL unrelated_assertion\n',
                       host.OBSERVED_SCALER_VM_LINE,
                       'FAIL identical_geometry_renders_when_input_gap_mask_31\n'):
            with self.subTest(stderr=stderr),self.assertRaises(RuntimeError):
                host.gap_red_proof(self.result(stderr))

    def test_stdout_and_wrong_exit_never_pass(self):
        for result in (self.result(host.EXPECTED_GAP_RED,code=0),
                       self.result(host.EXPECTED_GAP_RED,code=2),
                       self.result(host.EXPECTED_GAP_RED,stdout='extra output')):
            with self.subTest(result=result),self.assertRaises(RuntimeError):
                host.gap_red_proof(result)
