"""Guard Runtime assertion-Red provenance and public fixture selection."""
import importlib.util
import json
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


class Test061PublicSelectionTests(unittest.TestCase):
    fixture = ('func test061RecoveryPublic() {\n'
               '    require(true, "test061_fixture_boundary")\n}\n'
               'test061RecoveryPublic()\n'
               'print("PASS production Runtime public API/TEST061 recovery and actual commit fixtures")\n')

    def select(self, fixture=None, tests=None):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'ngg2_recovery_tests.swift').write_text(
                self.fixture if fixture is None else fixture)
            with patch.object(checker, 'HERE', Path(folder)):
                return checker.test061_public_fixture_source(
                    (HERE / 'ngg2_runtime_tests.swift').read_text() if tests is None else tests)

    def test_selects_only_registered_recovery_fixture_with_original_helpers(self):
        selected = self.select()
        calls = re.findall(r'^(test\w+)\(\)$', selected, flags=re.MULTILINE)
        self.assertEqual(calls, ['test061RecoveryPublic'])
        self.assertTrue(selected.endswith(self.fixture))
        self.assertIn('func require(', selected)
        self.assertNotIn('func testPagedResultsManifestPublicBaseline(', selected)
        self.assertNotIn('testShopWorld058Public()', selected)

    def test_actual_recovery_fixture_is_registered_and_contains_no_old_top_level_calls(self):
        selected = checker.test061_public_fixture_source((HERE / 'ngg2_runtime_tests.swift').read_text())
        calls = re.findall(r'^(test\w+)\(\)$', selected, flags=re.MULTILINE)
        self.assertEqual(calls, ['test061RecoveryPublic'])
        self.assertIn('test061_unsent_deadline_complete0_reacquires', selected)
        self.assertIn('test061_actual_commit_after_visual_deadline_rejects_all_motion_credit_', selected)
        self.assertNotIn('testShopWorld058Public()', selected)

    def test_rejects_missing_or_duplicate_helper_boundary(self):
        tests = (HERE / 'ngg2_runtime_tests.swift').read_text()
        marker = '// This public request is intentionally runnable'
        for broken in (tests.replace(marker, ''), tests + marker):
            with self.subTest(source=broken[-40:]), self.assertRaisesRegex(
                    ValueError, 'runtime_test061_public_fixture_boundary'):
                self.select(tests=broken)

    def test_rejects_empty_nonexecuting_duplicate_or_unregistered_fixture(self):
        cases = ('', '// no executable test',
                 self.fixture.replace('test061RecoveryPublic()\n', ''),
                 self.fixture + 'test061RecoveryPublic()\n',
                 self.fixture + 'testShopWorld058Public()\n',
                 self.fixture.replace('    require(true, "test061_fixture_boundary")\n', ''),
                 self.fixture.replace('func test061RecoveryPublic()', 'func unregisteredFixture()'))
        for fixture in cases:
            with self.subTest(fixture=fixture), self.assertRaisesRegex(
                    ValueError, 'runtime_test061_public_fixture_body'):
                self.select(fixture)

    def test_three_new_faults_are_separate_and_match_current_Runtime_once(self):
        mutations = checker.test061_runtime_mutations()
        self.assertEqual(set(mutations), checker.EXPECTED_TEST061_RUNTIME_MUTATIONS)
        self.assertEqual(len(mutations), 3)
        self.assertFalse(set(mutations) & (checker.EXPECTED_RUNTIME_MUTATIONS |
                                         checker.EXPECTED_TEST056_MUTATIONS))
        runtime = (HERE / 'ngg2/NG2Runtime.swift').read_text()
        for label, (old, new, expected) in mutations.items():
            with self.subTest(label=label):
                self.assertEqual(runtime.count(old), 1)
                self.assertNotEqual(old, new)
                self.assertTrue(expected.startswith('FAIL test061_'))

    def test_mutation_runner_keeps_focused_fixture_and_restores_Runtime(self):
        mutations = checker.test061_runtime_mutations()
        source = '\n'.join(value[0] for value in mutations.values())
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            (stage / 'main.swift').write_text(self.fixture)
            (stage / 'NG2Runtime.swift').write_text(source)
            sources = [stage / 'NG2Runtime.swift', stage / 'main.swift']
            def compile_focused(actual_sources, executable, output, label, extra, **kwargs):
                self.assertEqual(actual_sources, sources)
                self.assertEqual((stage / 'main.swift').read_text(), self.fixture)
                key = label.removeprefix('runtime-test061-').removesuffix('-mutation-red')
                old, new, expected = mutations[key]
                self.assertEqual((stage / 'NG2Runtime.swift').read_text(), source.replace(old, new))
                return subprocess.CompletedProcess(['focused-runtime'], 1, expected + '\n', '')
            with patch.object(checker, 'compile_run', side_effect=compile_focused) as compile_call, \
                    patch('builtins.print'):
                report = checker.test061_runtime_mutation_reds(source, sources, stage, stage, ['objects'])
            self.assertEqual(compile_call.call_count, 3)
            self.assertEqual(report['mutation_count'], 3)
            self.assertEqual(set(report['mutation_red']), set(mutations))
            self.assertEqual((stage / 'NG2Runtime.swift').read_text(), source)
            self.assertEqual((stage / 'main.swift').read_text(), self.fixture)

    def test_mutation_runner_rejects_compile_error_and_wrong_assertion_then_restores_source(self):
        mutations = checker.test061_runtime_mutations()
        source = '\n'.join(value[0] for value in mutations.values())
        for compile_failure in (True, False):
            with self.subTest(compile_failure=compile_failure), tempfile.TemporaryDirectory() as folder:
                stage = Path(folder)
                (stage / 'main.swift').write_text(self.fixture)
                (stage / 'NG2Runtime.swift').write_text(source)
                outcome = (subprocess.CalledProcessError(1, ['swiftc']) if compile_failure else
                           subprocess.CompletedProcess(['focused-runtime'], 1, 'FAIL other_assertion\n', ''))
                with patch.object(checker, 'compile_run', **(
                        {'side_effect': outcome} if compile_failure else {'return_value': outcome})) as run, \
                        patch('builtins.print'), self.assertRaises(
                            subprocess.CalledProcessError if compile_failure else RuntimeError):
                    checker.test061_runtime_mutation_reds(source, [], stage, stage, [])
                self.assertEqual(run.call_count, 1)
                self.assertEqual((stage / 'NG2Runtime.swift').read_text(), source)
                self.assertEqual((stage / 'main.swift').read_text(), self.fixture)

    def test_controller_complete0_fault_matches_current_source_and_substitutes_one_object(self):
        source = (HERE / 'ngg2/NG2Controller.c').read_text()
        old, new, expected = checker.test061_controller_mutation()
        self.assertEqual(source.count(old), 1)
        self.assertEqual(checker.EXPECTED_TEST061_C_MUTATIONS, frozenset(('recovery-unsent-complete0',)))
        self.assertFalse(checker.EXPECTED_TEST061_C_MUTATIONS & checker.EXPECTED_TEST061_RUNTIME_MUTATIONS)
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            native = stage / 'upstream'; native.mkdir()
            (native / 'NG2Controller.c').write_text(source)
            original = stage / 'app' / 'NG2Controller.o'
            extra = ['-D', 'NG2_RUNTIME_HOST_TEST', original, stage / 'app' / 'NG2Perception.o']
            red = subprocess.CompletedProcess(['focused-runtime'], 1, expected + '\n', '')
            with patch.object(checker.subprocess, 'run', return_value=
                    subprocess.CompletedProcess(['clang'], 0, '', '')) as clang, \
                    patch.object(checker, 'compile_run', return_value=red) as swift:
                report = checker.test061_controller_mutation_red(native, ['sources'], stage, stage, extra)
            self.assertEqual(set(report['mutation_red']), {'recovery-unsent-complete0'})
            command = clang.call_args.args[0]
            self.assertIn('-O0', command)
            self.assertEqual(command[command.index('-I') + 1], str(native))
            mutated_source = Path(command[command.index('-c') + 1])
            self.assertEqual(mutated_source.read_text(), source.replace(old, new))
            actual_extra = swift.call_args.args[4]
            self.assertNotIn(original, actual_extra)
            self.assertEqual(actual_extra[:2], extra[:2])
            self.assertEqual(actual_extra[-1], extra[-1])
            self.assertEqual(Path(actual_extra[2]).name, 'NG2Controller-test061-unsent.o')
            self.assertEqual((native / 'NG2Controller.c').read_text(), source)

    def test_controller_compile_failure_is_never_a_named_assertion_red(self):
        old, _, _ = checker.test061_controller_mutation()
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            (stage / 'NG2Controller.c').write_text(old)
            with patch.object(checker.subprocess, 'run', return_value=
                    subprocess.CompletedProcess(['clang'], 1, 'FAIL fake\n', 'error: C failed\n')), \
                    patch.object(checker, 'compile_run') as swift, patch('builtins.print'), \
                    self.assertRaises(subprocess.CalledProcessError):
                checker.test061_controller_mutation_red(stage, [], stage, stage, [stage / 'app' / 'NG2Controller.o'])
            swift.assert_not_called()

    def producer_stdout(self, *, clock=1, samples=True, count=5):
        rows = []
        for index in range(count):
            report = {'terminal': 1, 'paused': 1, 'workers_drained': True,
                      'recovery': {'records': [{'clock': clock if index == 0 else 2,
                'model': {'period_ns': 520_000_000}, 'samples': [{}] if samples else []}]}}
            tag = 'REPORT test061_recovery_unsent ' if index < 3 else 'REPORT test061_recovery_late '
            rows.append(tag + json.dumps(report))
        return '\n'.join(rows) + '\n'

    def test_producer_artifact_contains_exact_five_actual_report_rows_and_artifact_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            evidence = checker.test061_producer_reports(self.producer_stdout(), output)
            artifact = output / 'runtime-test061-recovery-reports.json'
            self.assertEqual(len(json.loads(artifact.read_text())), 5)
            self.assertEqual(evidence['producer_reports'], 5)
            self.assertEqual(evidence['producer_report_clocks'], [1, 2])
            self.assertEqual(evidence['retained_model_sample_snapshots'], 5)
            self.assertEqual(evidence['producer_reports_sha256'], checker.hashlib.sha256(artifact.read_bytes()).hexdigest())

    def test_producer_artifact_rejects_missing_clock_or_empty_snapshot_or_wrong_count(self):
        for stdout in (self.producer_stdout(count=4), self.producer_stdout(count=6),
                       self.producer_stdout(clock=2), self.producer_stdout(clock=True),
                       self.producer_stdout(samples=False),
                       self.producer_stdout().replace('520000000', 'NaN', 1)):
            with self.subTest(stdout=stdout[:100]), tempfile.TemporaryDirectory() as folder:
                output = Path(folder)
                with self.assertRaises((RuntimeError, ValueError)):
                    checker.test061_producer_reports(stdout, output)
                self.assertFalse((output / 'runtime-test061-recovery-reports.json').exists())

    def test_producer_artifact_rejects_unpaused_nonterminal_or_undrained_lifecycle(self):
        for key, value in (('terminal', 0), ('terminal', True), ('terminal', None),
                           ('paused', 0), ('paused', True), ('paused', None),
                           ('workers_drained', False), ('workers_drained', 1), ('workers_drained', None)):
            lines = self.producer_stdout().splitlines()
            tag = 'REPORT test061_recovery_unsent '
            first = json.loads(lines[0].removeprefix(tag))
            first[key] = value
            lines[0] = tag + json.dumps(first)
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as folder:
                output = Path(folder)
                with self.assertRaisesRegex(RuntimeError, 'runtime_test061_actual_paused_terminal_drained_producers_required'):
                    checker.test061_producer_reports('\n'.join(lines), output)
                self.assertFalse((output / 'runtime-test061-recovery-reports.json').exists())

    def test_actual_Runtime_response_requires_api15_and_rejects_same_source_api14(self):
        source = (HERE / 'ngg2/NG2Runtime.swift').read_text()
        checker.require_test061_runtime_api(source)
        actual = '"api_version": .string("1.98.15-ngg2")'
        self.assertEqual(source.count(actual), 1)
        old_api = source.replace(actual, '"api_version": .string("1.98.14-ngg2")')
        with self.assertRaisesRegex(ValueError, 'runtime_test061_response_api15_required'):
            checker.require_test061_runtime_api(old_api)
        # An API15 literal outside the actual response cannot repair the value.
        with self.assertRaisesRegex(ValueError, 'runtime_test061_response_api15_required'):
            checker.require_test061_runtime_api(old_api + '\n// ' + actual + '\n')

    def test_old_response_API_is_rejected_before_any_TEST061_native_compile(self):
        source = (HERE / 'ngg2/NG2Runtime.swift').read_text().replace(
            '"api_version": .string("1.98.15-ngg2")', '"api_version": .string("1.98.14-ngg2")')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            native = root / 'upstream' / 'LoopCtrlUITests'; native.mkdir(parents=True)
            (native / 'NG2Runtime.swift').write_text(source)
            with patch.object(checker, 'test061_native_objects') as compile_native, \
                    patch.object(checker.subprocess, 'run') as compile_other, \
                    self.assertRaisesRegex(ValueError, 'runtime_test061_response_api15_required'):
                checker.test061_contract(root / 'upstream', root / 'output')
            compile_native.assert_not_called()
            compile_other.assert_not_called()

    def test_green_rejects_zero_missing_skip_and_unexpected_diagnostic_results(self):
        accepted = subprocess.CompletedProcess(['focused-runtime'], 0,
                                               checker.TEST061_PUBLIC_PASS + '\n', '')
        checker.require_test061_green(accepted)
        for stdout, stderr in (('', ''), ('PASS other fixture\n', ''),
                               ('SKIP TEST061\n' + accepted.stdout, ''),
                               (' skipped fixture\n' + accepted.stdout, ''),
                               (accepted.stdout, 'unexpected diagnostic\n')):
            with self.subTest(stdout=stdout, stderr=stderr), self.assertRaisesRegex(
                    RuntimeError, 'runtime_test061_public_contract_missing'):
                checker.require_test061_green(subprocess.CompletedProcess(
                    ['focused-runtime'], 0, stdout, stderr))
        with patch('builtins.print'), self.assertRaises(subprocess.CalledProcessError):
            checker.require_test061_green(subprocess.CompletedProcess(
                ['focused-runtime'], 1, accepted.stdout, ''))

    def test_new_standalone_modes_dispatch_without_historical_runtime_modes(self):
        for flag, mutations in (('--test061-public-only', False),
                                ('--test061-new-mutations-only', True)):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as folder:
                paths = [str(Path(folder) / 'upstream'), str(Path(folder) / 'output')]
                report = {'runtime': {'production_green': 'focused result'}}
                with patch.object(checker.sys, 'argv', ['check_ngg2.py', flag, *paths]), \
                        patch.object(checker, 'test061_contract', return_value=report) as focused, \
                        patch.object(checker, 'runtime_contract') as historical, patch('builtins.print'):
                    checker.main()
                focused.assert_called_once_with(Path(paths[0]), Path(paths[1]), mutations_only=mutations)
                historical.assert_not_called()

    def test_new_standalone_modes_reject_conflicting_modes_and_missing_paths(self):
        for arguments in (['--test061-public-only', '--test061-new-mutations-only', 'a', 'b'],
                          ['--test061-public-only', '--test058-shop-only', 'a', 'b'],
                          ['--test061-public-only', '--red-only', 'a', 'b'],
                          ['--test061-public-only', 'a']):
            with self.subTest(arguments=arguments), \
                    patch.object(checker.sys, 'argv', ['check_ngg2.py', *arguments]), \
                    patch.object(checker, 'test061_contract') as focused, \
                    patch.object(checker.sys, 'stderr'), self.assertRaises(SystemExit) as error:
                checker.main()
            self.assertEqual(error.exception.code, 2)
            focused.assert_not_called()

    def test_native_compile_uses_only_four_current_upstream_sources_and_app_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            native = output / 'upstream' / 'LoopCtrlUITests'
            native.mkdir(parents=True)
            names = ('NG2Beat.c', 'NG2Controller.c', 'NG2Navigation.c', 'NG2Perception.c')
            for name in names:
                (native / name).write_text('/* ' + name + ' */\n')
            with patch.object(checker.subprocess, 'run', return_value=
                    subprocess.CompletedProcess(['clang'], 0, '', '')) as compile_call:
                objects, provenance = checker.test061_native_objects(native, output)
            self.assertEqual(set(provenance), set(names))
            self.assertEqual(len(objects), 4)
            self.assertEqual(compile_call.call_count, 4)
            for call in compile_call.call_args_list:
                command = call.args[0]
                source = Path(command[command.index('-c') + 1])
                target = Path(command[command.index('-o') + 1])
                self.assertEqual(source.parent, native)
                self.assertEqual(target.parent, output / 'test061-native')
                flags = checker.native_object_flags(source.name)
                self.assertEqual(provenance[source.name]['flags'], flags)
                self.assertTrue(all(flag in command for flag in flags))
            self.assertTrue(all(path.parent == output / 'test061-native' for path in objects))

    def test_native_compile_rejects_missing_extra_or_failed_sources(self):
        names = ('NG2Beat.c', 'NG2Controller.c', 'NG2Navigation.c', 'NG2Perception.c')
        for selected in (names[:-1], names + ('NG2Unexpected.c',)):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                native = root / 'native'; native.mkdir()
                for name in selected:
                    (native / name).write_text('/* fixture */\n')
                with patch.object(checker.subprocess, 'run') as run, self.assertRaisesRegex(
                        ValueError, 'native_C_source_set'):
                    checker.test061_native_objects(native, root)
                run.assert_not_called()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            native = root / 'native'; native.mkdir()
            for name in names:
                (native / name).write_text('/* fixture */\n')
            with patch.object(checker.subprocess, 'run', return_value=
                    subprocess.CompletedProcess(['clang'], 1, '', 'error: compile failed\n')) as run, \
                    patch('builtins.print'), self.assertRaises(subprocess.CalledProcessError):
                checker.test061_native_objects(native, root)
            self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
