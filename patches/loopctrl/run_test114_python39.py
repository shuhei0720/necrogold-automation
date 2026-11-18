"""Actual Python 3.9 entry and the explicitly selected TEST114 client contracts."""
import argparse
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SCOPE_FINALIZED = True
CASES = (
    ('tests.test_campaign_diagnostics114', 'CampaignDiagnostics114Tests', 'test114-python39-CampaignDiagnostics114Tests', frozenset({
        'test_existing_campaign_symlink_is_rejected_before_any_zip_read',
        'test_existing_rpc_timings_are_observed_without_changing_the_result_or_requests',
        'test_failed_diagnostic_reads_preserve_real_campaign_publication_and_handoff_qualification',
        'test_fixed_rpc_aggregates_bound_runs_and_store_no_request_bodies',
        'test_marker_grammar_drops_private_urls_tokens_and_arbitrary_messages',
        'test_observer_exceptions_do_not_replace_primary_rpc_error_or_cancel_run',
        'test_optional_clock_failure_preserves_primary_error_and_reports_missing_timing',
        'test_private_sidecar_is_optional_sealed_and_does_not_change_index_or_nested_run',
        'test_readonly_deadline_once_and_primary_failure_diagnostics_are_preserved',
        'test_readonly_observation_runs_once_only_after_real_drain_before_collection',
        'test_readonly_projection_retains_only_typed_native_numbers_and_static_markers',
        'test_sealed_reuse_rejects_duplicate_keys_and_noncanonical_hidden_bytes',
    }), True),
    ('tests.test_client_drain113', 'ClientDrain113Tests', 'test114-python39-ClientDrain113Tests', frozenset({
        'test_actual_terminal_draining_projection_is_readonly_for_both_protocols',
        'test_campaign_publishes_drained_predecessor_before_new_uuid',
        'test_cancelled_recovery_keeps_failure_in_collection_archive_and_publication',
        'test_explicit_cancel_during_draining_is_not_replaced_by_continuation',
        'test_incoherent_draining_and_changed_closed_fields_fail_closed',
        'test_non_cancelled_success_clears_old_retry_error',
        'test_repeated_draining_waits_before_manifest_without_cancel_or_resend',
        'test_unknown_input_still_waits_for_drain_and_remains_diagnostic_only',
    }), True),
    ('tests.test_native_cycle_client094', 'CycleClient094Tests', 'test114-python39-CycleClient094Tests', frozenset({
        'test_ack_failure_retains_same_archive_and_retries_no_game_start',
        'test_changed_completed_archive_blocks_ack_and_preserves_destination',
        'test_later_explicit_invocation_starts_new_id_only_after_prior_receipt_and_zip_verify',
        'test_method_admission_rejects_oldprofile_unknownfields_and_arbitrary_input',
        'test_published_ack_occurs_only_after_full_crc_sha_zip_and_destination_copy',
    }), False),
    ('tests.test_campaign099', 'Campaign099Tests', 'test114-python39-Campaign099Tests', frozenset({
        'test_negative_handoff_publishes_before_new_uuid_and_stops_at_target',
        'test_publication_ack_failure_returns_incomplete_fault_bundle_and_same_id_recovery',
        'test_single_mode_returns_a_checked_index_and_last_full_run_zip',
    }), False),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_suite(driver):
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST114 actual Python 3.9 author scope is pending')
    spec = importlib.util.spec_from_file_location('test114_host_source_utils', HERE/'run_test114_host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    host.reject_fixture_overrides()
    selected = []
    for name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST114 Python fixture import escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    return host, host.selected_cases(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not SCOPE_FINALIZED:
        raise SystemExit('TEST114 actual Python 3.9 author scope is pending; no test executed')
    if sys.version_info[:2] != (3, 9) or platform.python_implementation() != 'CPython' or hasattr(0, 'bit_count'):
        raise SystemExit('Actual CPython 3.9 is required')
    driver, output = args.driver.resolve(), args.output.resolve()
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    host, selected = selected_suite(driver)
    host.ensure_scope()
    paths = (*host.PRODUCT_PATHS, *sorted(host.CLIENT_PRODUCT_CHANGES),
        'patches/loopctrl/run_test114_python39.py', 'patches/loopctrl/run_test114_host.py',
        *(row[0].replace('.', '/')+'.py' for row in CASES))
    code = subprocess.check_output(['git', '-C', str(driver), 'rev-parse', 'HEAD'], text=True).strip()
    before = {path: hashlib.sha256(host.pinned_bytes(driver, path, code)).hexdigest() for path in dict.fromkeys(paths)}
    syntax = subprocess.run(['sh', '-n', str(driver/'test_114.sh')], capture_output=True, text=True)
    check = subprocess.run([sys.executable, '-m', 'necroprobe.test114', '--check'], cwd=driver,
        capture_output=True, text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-device-failures-trial-v114 / 1.98.16-ngg2')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(selected))
    output.mkdir(parents=True, exist_ok=True)
    log = stream.getvalue()
    (output/'test114-python39.txt').write_text(log)
    print(sys.version)
    print(log, end='', flush=True)
    after = {name: sha(driver/name) for name in before}
    success = entry_ok and before == after and result.testsRun == len(selected) and (
        result.wasSuccessful() and not result.skipped and not result.expectedFailures)
    evidence = dict(driver_commit=code, scope='actual Python 3.9 selected TEST114 client contracts',
        interpreter_version=sys.version, interpreter=platform.python_implementation(),
        interpreter_executable_sha256=sha(Path(sys.executable).resolve()),
        python_version=list(sys.version_info[:3]), selected=[case.id() for case in selected],
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
        source_sha256=before, sources_unchanged=before == after, product_pass=success,
        shell_syntax=dict(returncode=syntax.returncode, stdout=syntax.stdout, stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr),
        device_test='not_run')
    (output/'test114-python39-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if not success:
        raise SystemExit('TEST114 actual Python 3.9 selected methods/entry must all execute Green')


if __name__ == '__main__':
    main()
