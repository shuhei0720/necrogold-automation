"""Guard Runtime assertion-Red provenance and public fixture selection."""
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ngg2_checker', HERE / 'check_ngg2.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def without_host_fixture_seams(source):
    """Independently remove complete marked lines, preserving all other bytes."""
    for name in ('METHOD', 'SNAPSHOT'):
        begin = '// TEST056 HOST ' + name + ' BEGIN.\n'
        end = '// TEST056 HOST ' + name + ' END.\n'
        start = source.index(begin)
        start = source.rfind('\n', 0, start) + 1
        stop = source.index(end, start) + len(end)
        source = source[:start] + source[stop:]
    # The seam overwrites only local fixture query arrays and their lengths.
    source = source.replace('        var count = events.withUnsafeMutableBufferPointer',
                            '        let count = events.withUnsafeMutableBufferPointer')
    source = source.replace('        var changeCount = changes.withUnsafeMutableBufferPointer',
                            '        let changeCount = changes.withUnsafeMutableBufferPointer')
    return source


# This is the established inventory, independently frozen before TEST056.
TEST055_MUTATIONS = frozenset('''
analysis-commit analysis-owner authority-origin callback-drain capture-admission
capture-failure-connection capture-failure-first capture-failure-generation
capture-failure-orientation continuous-callback-drain continuous-command-id
continuous-details-connection continuous-return-bookkeeping difference-reference
dispatch-failure-command dispatch-failure-connection dispatch-failure-first
dispatch-failure-generation dispatch-failure-query-start export-chunk-offset
export-chunk-reply-current export-chunk-reply-owner export-manifest-immutable
export-manifest-reply-current export-manifest-reply-owner export-parallel-build
export-per-image-boundary export-retired-raw-storage export-selection-count
export-stale-generation-cache export-total-boundary final-generation final-lock
final-query foreground-lock fresh-old-direction-reused fresh-revalidation-disabled
initial-slot-early-publication initial-slot-missing-preparation-margin legacy-pending
main-admission main-clock motion-clock motion-reference
motion-reference-fallback-disabled motion-reference-original-discarded
motion-reference-producer-disconnected move-input observe-start-connection
observe-start-placement prepare-token raster-trace stale-cleanup stale-entry
target-drift-after-action target-drift-pending-action worker-analysis
'''.split())


class NGG2RuntimeVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tests = (HERE / 'ngg2_runtime_tests.swift').read_text()
        cls.runtime = (HERE / 'ngg2/NG2Runtime.swift').read_text()

    def test_fixed_test055_baseline_identity(self):
        self.assertEqual(checker.TEST055_RUNTIME_COMMIT,
                         '2d77c02665c27d0e1e813c8d6bb65ec980d26b2b')
        self.assertEqual(checker.TEST055_RUNTIME_SHA256,
                         'b83c19d30294228abb6aeae9a339917d3c9afde8f5a57d01b1575a2e3b76d261')

    def test_established_57_and_new_two_fault_inventories_are_separate(self):
        self.assertEqual(len(TEST055_MUTATIONS), 57)
        self.assertEqual(checker.EXPECTED_RUNTIME_MUTATIONS, TEST055_MUTATIONS)
        self.assertEqual(checker.EXPECTED_TEST056_MUTATIONS, frozenset((
            'stop-evidence-pin-priority', 'stop-evidence-selection-priority')))
        self.assertFalse(checker.EXPECTED_RUNTIME_MUTATIONS & checker.EXPECTED_TEST056_MUTATIONS)
        self.assertEqual(len(checker.EXPECTED_RUNTIME_MUTATIONS |
                             checker.EXPECTED_TEST056_MUTATIONS), 59)

    def test_only_executed_named_assertion_is_accepted_as_red(self):
        expected = 'FAIL stop_evidence_required_frames'
        accepted = subprocess.CompletedProcess(['runtime-tests'], 1,
                                               'PASS fixture setup\n' + expected + '\n', '')
        checker.require_red(accepted, expected)
        cases = (
            (0, expected + '\n', ''),
            (1, '', ''),
            (1, 'error: Runtime could not compile\n', ''),
            (1, expected + '\n', 'compiler or runner failure\n'),
            (1, 'FAIL a_different_assertion\n', ''),
            (1, expected + '\nPASS unexpected continuation\n', ''),
            (-9, expected + '\n', ''),
        )
        for code, stdout, stderr in cases:
            with self.subTest(code=code, stdout=stdout, stderr=stderr), \
                    patch('builtins.print'), \
                    self.assertRaisesRegex(RuntimeError, 'compiled_behavioral_red_not_observed'):
                checker.require_red(subprocess.CompletedProcess(
                    ['runtime-tests'], code, stdout, stderr), expected)

    def test_compile_failure_cannot_run_or_become_an_assertion_red(self):
        failed = subprocess.CompletedProcess(['swiftc'], 1,
                                             'FAIL stop_evidence_required_frames\n',
                                             'error: failed to compile\n')
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(checker.subprocess, 'run', return_value=failed) as run, \
                patch('builtins.print'), self.assertRaises(subprocess.CalledProcessError):
            output = Path(directory)
            checker.compile_run([output / 'main.swift'], output / 'runtime-tests',
                                output, 'test056-baseline')
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], 'swiftc')

    def test_established_public_modes_keep_their_original_entrypoints(self):
        cases = {
            '051': ('testContinuousRevalidationCallbacksPublic', 'testPagedResultsPublic'),
            '052': ('testTargetDriftPlannerProof', 'testTargetDriftRevalidationCallbacksPublic'),
            '053': ('testStartupRemotePixelProof', 'testInitialSlotPreparationPublic'),
            '054': ('testOriginalMotionReferencePixelProof',
                    'testOriginalMotionReferenceCallbacksPublic'),
            '055': ('testFreshRevalidationPixelProof', 'testFreshRevalidationCallbacksPublic'),
        }
        for number, expected in cases.items():
            with self.subTest(mode=number):
                selected = getattr(checker, 'test' + number + '_public_fixture_source')(self.tests)
                calls = re.findall(r'^(test\w+)\(\)$', selected, flags=re.MULTILINE)
                self.assertEqual(calls, list(expected))
                for name in expected:
                    self.assertEqual(selected.count('func ' + name + '('), 1)
                self.assertNotIn('// TEST056 PUBLIC FIXTURES BEGIN.', selected)

    def test_established_public_modes_reject_missing_or_repeated_markers(self):
        for number in ('051', '052', '053', '054', '055'):
            extract = getattr(checker, 'test' + number + '_public_fixture_source')
            dependencies = ('051', number) if number in ('052', '054', '055') else (number,)
            markers = ['// TEST051 MANIFEST FIXTURE END.\n']
            for dependency in dependencies:
                markers += ['// TEST' + dependency + ' PUBLIC FIXTURES BEGIN.\n',
                            '// TEST' + dependency + ' PUBLIC FIXTURES END.\n']
            for marker in markers:
                for broken in (self.tests.replace(marker, '', 1), self.tests + marker):
                    with self.subTest(mode=number, marker=marker), self.assertRaises(ValueError):
                        extract(broken)

    def test_test056_public_mode_keeps_the_diagnostic_fixture_entrypoint(self):
        selected = checker.test056_public_fixture_source(self.tests)
        calls = re.findall(r'^(test\w+)\(\)$', selected, flags=re.MULTILINE)
        self.assertEqual(calls, ['testStopEvidenceRetentionPublic'])
        self.assertEqual(selected.count('func testStopEvidenceRetentionPublic('), 1)
        self.assertEqual(selected.count('func publicExportFixture('), 1)
        self.assertIn('no game progress asserted', selected)

    def test_test056_public_mode_rejects_missing_or_repeated_markers(self):
        markers = ('// TEST051 MANIFEST FIXTURE END.\n',
                   '// TEST051 PUBLIC FIXTURES BEGIN.\n',
                   '// TEST051 PUBLIC FIXTURES END.\n',
                   '// TEST056 PUBLIC FIXTURES BEGIN.\n',
                   '// TEST056 PUBLIC FIXTURES END.\n')
        for marker in markers:
            for broken in (self.tests.replace(marker, '', 1), self.tests + marker):
                with self.subTest(marker=marker), self.assertRaises(ValueError):
                    checker.test056_public_fixture_source(broken)

    def test_host_seam_injection_changes_only_fixture_blocks_and_query_lengths(self):
        original = without_host_fixture_seams(self.runtime)
        injected = checker.test056_host_fixture_seam(original, self.runtime)
        self.assertEqual(injected, self.runtime)
        self.assertEqual(without_host_fixture_seams(injected), original)
        # Pin and selection bodies must stay byte-for-byte those of the input.
        boundaries = (
            ('    private func selectedExportFrames(', '    private func imageMetadata('),
            ('        run.lock.ng2Locked {\n            var required = Set<UInt64>()',
             '        let encoded = events.'),
        )
        for begin, end in boundaries:
            with self.subTest(block=begin):
                before = original[original.index(begin):original.index(end, original.index(begin))]
                after = injected[injected.index(begin):injected.index(end, injected.index(begin))]
                self.assertEqual(after, before)

    def test_host_seam_reinjection_is_byte_identical(self):
        self.assertEqual(checker.test056_host_fixture_seam(self.runtime, self.runtime),
                         self.runtime)

    def test_host_seam_rejects_missing_or_repeated_fixture_boundaries(self):
        original = without_host_fixture_seams(self.runtime)
        for name, indent in (('METHOD', '    '), ('SNAPSHOT', '        ')):
            for edge in ('BEGIN', 'END'):
                marker = indent + '// TEST056 HOST ' + name + ' ' + edge + '.\n'
                for broken in (self.runtime.replace(marker, '', 1), self.runtime + marker):
                    with self.subTest(marker=marker), self.assertRaises(ValueError):
                        checker.test056_host_fixture_seam(original, broken)
                    with self.subTest(source_marker=marker), self.assertRaises(ValueError):
                        checker.test056_host_fixture_seam(broken, self.runtime)

    def test_host_seam_rejects_missing_or_repeated_insertion_anchors(self):
        original = without_host_fixture_seams(self.runtime)
        anchors = ('    static var testFrameStride:',
                   '        run.lock.ng2Locked {\n            var required = Set<UInt64>()')
        for anchor in anchors:
            for broken in (original.replace(anchor, '', 1), original + anchor):
                with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                    checker.test056_host_fixture_seam(broken, self.runtime)

    def test_host_seam_rejects_an_end_marker_without_any_begin(self):
        original = without_host_fixture_seams(self.runtime)
        for name in ('METHOD', 'SNAPSHOT'):
            with self.subTest(marker=name), self.assertRaises(ValueError):
                checker.test056_host_fixture_seam(original+'// TEST056 HOST '+name+' END.\n', self.runtime)


class Test058PublicSelectionTests(unittest.TestCase):
    def test_baseline_capture_clock_barrier_preserves_asserts_and_time_values(self):
        source = ('    var actualObserveEnd: UInt64 = 0\n'
            '        if armedObservation {\n'
            '                NG2Fake.advance(captureStart-now)\n'
            'require(observedEnd+observedRemainder == deadline, "unchanged")\n')
        selected = checker.test058_baseline_capture_clock_barrier(source)
        self.assertIn('captureLimit = NG2Fake.requests+1', selected)
        self.assertIn('NG2Fake.virtualClock() >= expectedObserveEnd', selected)
        self.assertIn('expectedObserveEnd = deadline-observedRemainder', selected)
        self.assertEqual(selected.count('NG2Fake.advance('), 1)
        self.assertTrue(selected.endswith('require(observedEnd+observedRemainder == deadline, "unchanged")\n'))
    def test_baseline_capture_clock_barrier_rejects_missing_duplicate_and_reinjection(self):
        source = ('    var actualObserveEnd: UInt64 = 0\n'
            '        if armedObservation {\n'
            '                NG2Fake.advance(captureStart-now)\n')
        for bad in ('', source+source, checker.test058_baseline_capture_clock_barrier(source)):
            with self.subTest(source=bad), self.assertRaises(ValueError):
                checker.test058_baseline_capture_clock_barrier(bad)
    def test_baseline_release_barrier_preserves_every_original_byte_and_assertion(self):
        source = 'before\n    NG2Fake.releaseTicket(replacement)\nafter\n'
        combined = checker.test058_baseline_release_barrier(source)
        barrier = combined.removeprefix('before\n').split('    NG2Fake.releaseTicket(replacement)\n')[0]
        self.assertIn('NG2Fake.heldTickets[replacement] != nil', barrier)
        self.assertIn('NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }', barrier)
        self.assertEqual(combined.replace(barrier, '', 1), source)
        self.assertNotIn('NG2Fake.advance', barrier)
        self.assertNotIn('require(', barrier)
    def test_baseline_release_barrier_rejects_missing_duplicate_or_reinjection(self):
        anchor = '    NG2Fake.releaseTicket(replacement)\n'
        for source in ('', anchor+anchor, checker.test058_baseline_release_barrier(anchor)):
            with self.subTest(source=source), self.assertRaises(ValueError):
                checker.test058_baseline_release_barrier(source)
    def test_selects_only_real_helpers_and_new_executable_fixture(self):
        tests=(HERE/'ngg2_runtime_tests.swift').read_text()
        fixture=(HERE/'ngg2_dispatch_preparation_tests.swift').read_text()
        selected=checker.test058_public_fixture_source(tests)
        self.assertTrue(selected.endswith(fixture))
        self.assertNotIn('// This public request is intentionally runnable',selected)
        self.assertIn('func require(',selected)
        self.assertIn('MISSING_prepared_continuous_reissue_sends_within_original_frozen_deadline',selected)
    def test_rejects_missing_or_duplicated_helper_boundary(self):
        tests=(HERE/'ngg2_runtime_tests.swift').read_text()
        marker='// This public request is intentionally runnable'
        for broken in (tests.replace(marker,''),tests+marker):
            with self.subTest(source=broken[-40:]),self.assertRaises(ValueError):
                checker.test058_public_fixture_source(broken)
    def test_rejects_empty_or_nonexecuting_new_fixture(self):
        tests=(HERE/'ngg2_runtime_tests.swift').read_text()
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'ngg2_dispatch_preparation_tests.swift'
            for content in ('','// no executable body','func test058PreparedContinuousDeadlinePublic() {}'):
                target.write_text(content)
                with patch.object(checker,'HERE',Path(folder)),self.assertRaises(ValueError):
                    checker.test058_public_fixture_source(tests)


if __name__ == '__main__':
    unittest.main()
