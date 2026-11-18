"""Actual Python 3.9 for the frozen TEST116 continuous-client scope."""
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
    ('tests.test_continuous_client116', 'ContinuousClientWire116Tests', 'test116-python39-ContinuousClientWire116Tests', frozenset({
        'test_continuous_start_is_explicit_without_the_old_yield_flag',
        'test_old_client_keeps_rejecting_new_flags_and_new_query',
        'test_root_status_has_only_the_root_identity_and_typed_keepalive',
        'test_root_status_rejects_duplicate_out_of_order_missing_and_mistyped_children',
        'test_running_and_stopped_root_statuses_keep_all_ordered_children',
        'test_start_refuses_false_untyped_flags_extra_fields_and_other_profiles',
    }), True),
    ('tests.test_continuous_client116', 'ContinuousClientRun116Tests', 'test116-python39-ContinuousClientRun116Tests', frozenset({
        'test_authenticated_not_admitted_resets_intent_without_reposting_and_rechecks_prepare',
        'test_cancel_between_durable_intent_and_transport_sends_no_start',
        'test_cancelled_last_child_may_retain_a_real_unused_qualified_snapshot',
        'test_collection_failure_resumes_original_children_without_new_start',
        'test_continuation_requires_the_real_negative_restart_and_epoch_chain',
        'test_first_floor_itself_and_parent_deadline_equality_remain_legal',
        'test_live_handoffs_export_nothing_then_collect_and_publish_every_child',
        'test_local_status_save_failure_still_cancels_the_live_root',
        'test_lost_selector_uses_durable_root_intent_instead_of_new_start',
        'test_missing_new_capability_never_posts_a_start',
        'test_native_restart_reconstructs_all_child_links_and_only_recovers',
        'test_no_continuous_opt_in_cannot_create_a_new_native_root',
        'test_orphan_native_namespaces_are_all_recovered_without_a_new_start',
        'test_qualified_zero_snapshot_cannot_verify_a_continued_child',
        'test_recovered_root_keeps_unknown_diagnostics_from_every_child',
        'test_root_deadline_cannot_be_extended_by_a_later_status_reply',
        'test_seal_clock_session_terminal_and_qualified_binding_cannot_be_forged',
        'test_uncertain_start_is_never_posted_again_and_recovery_has_no_keepalive',
        'test_unordered_orphan_namespaces_reconstruct_in_child_index_order',
        'test_unsealed_storage_failure_keeps_all_archives_and_incomplete_result',
        'test_untrusted_not_admitted_code_keeps_the_uncertain_original_intent',
        'test_unused_last_qualification_is_not_a_zero_or_unexplained_positive_stop',
        'test_wrong_frames_digest_cannot_complete_or_drop_any_child_archive',
    }), True),
    ('tests.test_continuous_client116', 'ContinuousClientEntry116Tests', 'test116-python39-ContinuousClientEntry116Tests', frozenset({
        'test_known_not_started_notice_requests_normal_retry_instead_of_recovery',
    }), True),
    ('tests.test_forensic_orphan116', 'ForensicOrphanClient116Tests', 'test116-python39-ForensicOrphanClient116Tests', frozenset({
        'test_child_session_identity_and_owner_must_match_the_linked_parent',
        'test_closed_diagnostic_zip_loss_blocks_a_later_start',
        'test_diagnostic_entry_reports_collection_instead_of_a_gameplay_success',
        'test_existing_game_terminal_and_raw_evidence_are_not_an_orphan_fallback',
        'test_foreign_or_unreserved_parent_link_never_closes_collection',
        'test_lost_closed_selector_does_not_bypass_the_zip_check_before_new_start',
        'test_physical_evidence_failure_stays_pending_without_a_diagnostic_success',
        'test_reservation_must_precede_the_actual_restart_intent',
        'test_same_root_recovery_closes_then_only_a_later_explicit_call_starts',
        'test_session_complete_and_uncommitted_orphans_keep_a_diagnostic_row',
    }), True),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_suite(driver):
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST116 actual Python 3.9 author scope is pending')
    spec = importlib.util.spec_from_file_location('test116_host_source_utils', HERE/'run_test116_host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    host.ensure_scope()
    host.reject_fixture_overrides()
    selected = []
    for name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST116 Python fixture escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    return host, host.selected_cases(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not SCOPE_FINALIZED:
        raise SystemExit('TEST116 actual Python 3.9 scope is pending; no tests executed')
    if sys.version_info[:2] != (3, 9) or platform.python_implementation() != 'CPython' or hasattr(0, 'bit_count'):
        raise SystemExit('Actual CPython 3.9 is required')
    driver, output = args.driver.resolve(), args.output.resolve()
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    host, selected = selected_suite(driver)
    paths = (*host.PRODUCT_PATHS, *sorted(host.CLIENT_PRODUCT_CHANGES),
        'patches/loopctrl/run_test116_python39.py', 'patches/loopctrl/run_test116_host.py',
        *(row[0].replace('.', '/')+'.py' for row in CASES))
    code = subprocess.check_output(['git', '-C', str(driver), 'rev-parse', 'HEAD'], text=True).strip()
    before = {path: hashlib.sha256(host.pinned_bytes(driver, path, code)).hexdigest() for path in dict.fromkeys(paths)}
    syntax = subprocess.run(['sh', '-n', str(driver/'test_116.sh')], capture_output=True, text=True)
    check = subprocess.run([sys.executable, '-m', 'necroprobe.test116', '--check'], cwd=driver,
        capture_output=True, text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-device-failures-trial-v116 / 1.98.16-ngg2')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(selected))
    output.mkdir(parents=True, exist_ok=True)
    log = stream.getvalue()
    (output/'test116-python39.txt').write_text(log)
    print(sys.version)
    print(log, end='', flush=True)
    after = {name: sha(driver/name) for name in before}
    success = entry_ok and before == after and result.testsRun == len(selected) and (
        result.wasSuccessful() and not result.skipped and not result.expectedFailures)
    evidence = dict(driver_commit=code, scope='actual Python 3.9 selected TEST116 client contracts',
        interpreter_version=sys.version, interpreter=platform.python_implementation(),
        interpreter_executable_sha256=sha(Path(sys.executable).resolve()), python_version=list(sys.version_info[:3]),
        selected=[case.id() for case in selected], tests_run=result.testsRun, failures=len(result.failures),
        errors=len(result.errors), skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
        source_sha256=before, sources_unchanged=before == after, product_pass=success,
        shell_syntax=dict(returncode=syntax.returncode, stdout=syntax.stdout, stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr), device_test='not_run')
    (output/'test116-python39-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if not success:
        raise SystemExit('TEST116 actual Python 3.9 methods/entry must all execute Green')


if __name__ == '__main__':
    main()
