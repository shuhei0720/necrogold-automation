"""Actual CPython3.9: TEST126 client14, retained startup14 and direct19."""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SCOPE_FINALIZED = True
PENDING_SCOPE_ITEMS = ()
EXPECTED_SELECTED_METHOD_COUNT = 47
CASES = (
    ('tests.test_continuous_client126', 'ContinuousClient126Tests', 'test126-client', frozenset({
        'test_both_modes_require_126_implementation_without_changing_old_clients',
        'test_old_ipa_is_blocked_before_either_pipeline_sends_native_requests',
        'test_126_schema_is_distinct_and_only_supported_numbers_are_admitted',
        'test_116_117_118_119_120_121_122_123_124_125_126_histories_remain_isolated_with_or_without_selector',
        'test_wrong_history_or_spool_makes_no_native_request',
        'test_live_chain_keeps_126_archives_and_posts_initial_restart_once',
        'test_uncertain_start_recovers_same_root_without_a_second_post',
        'test_finite_mode_keeps_the_single_initial_restart_post',
        'test_check_and_finite_entry_use_126_identity',
        'test_continuous_and_saved_recovery_entry_keep_126_namespace',
        'test_shell_has_126_identity_and_rejects_conflicting_modes_before_device_use',
        'test_126_inherits_startup_wait_and_initial_restart_in_both_modes',
        'test_126_pending_scan_uses_the_inherited_wait_then_starts_once',
        'test_126_reports_inherited_scan_timeout_without_new_game',
    }), True),
    ('tests.test_campaign_startup125', 'CampaignStartup125Tests', 'test125-startup', frozenset({
        'test_actual_pending_then_scan_ready_starts_once_after_prepare',
        'test_pending_stops_at_original_admission_deadline_without_a_journal_or_post',
        'test_ready_reply_at_or_after_original_deadline_never_admits_a_start',
        'test_sole_post_guard_reuses_the_first_prepare_deadline_after_durable_intent',
        'test_explicit_failure_states_are_not_all_notification_errors',
        'test_late_explicit_failure_is_reported_before_admission_expiry',
        'test_read_connection_failure_is_not_replayed_and_does_not_write_start_intent',
        'test_uncertain_post_after_prepare_wait_is_never_posted_again',
        'test_cancellation_after_a_read_or_wait_never_admits_or_retries',
        'test_late_authenticated_unpublished_ids_still_enter_only_old_recovery',
        'test_recovery_only_waits_for_complete_scan_before_reporting_no_records',
        'test_only_125_continuous_client_opts_in_and_false_flag_keeps_single_query',
        'test_malformed_ready_cannot_be_repaired_or_used_to_start',
        'test_source_fix_banner_and_error_details_do_not_change_check_identity',
    }), True),
    ('tests.test_continuous_client125', 'ContinuousClient125Tests', 'test125-direct-client', frozenset({
        'test_both_modes_require_125_implementation_without_changing_old_clients',
        'test_old_ipa_is_blocked_before_either_pipeline_sends_native_requests',
        'test_125_schema_is_distinct_and_only_supported_numbers_are_admitted',
        'test_116_117_118_119_120_121_122_123_124_125_histories_remain_isolated_with_or_without_selector',
        'test_wrong_history_or_spool_makes_no_native_request',
        'test_live_chain_keeps_125_archives_and_posts_initial_restart_once',
        'test_uncertain_start_recovers_same_root_without_a_second_post',
        'test_finite_mode_keeps_the_single_initial_restart_post',
        'test_check_and_finite_entry_use_125_identity',
        'test_continuous_and_saved_recovery_entry_keep_125_namespace',
        'test_shell_has_125_identity_and_rejects_conflicting_modes_before_device_use',
    }), True),
    ('tests.test_continuous_client116', 'ContinuousClientRun116Tests', 'test116-direct-start-recovery', frozenset({
        'test_live_handoffs_export_nothing_then_collect_and_publish_every_child',
        'test_uncertain_start_is_never_posted_again_and_recovery_has_no_keepalive',
        'test_collection_failure_resumes_original_children_without_new_start',
        'test_lost_selector_uses_durable_root_intent_instead_of_new_start',
        'test_native_restart_reconstructs_all_child_links_and_only_recovers',
        'test_cancel_between_durable_intent_and_transport_sends_no_start',
        'test_authenticated_not_admitted_resets_intent_without_reposting_and_rechecks_prepare',
        'test_untrusted_not_admitted_code_keeps_the_uncertain_original_intent',
    }), False),
)
SOURCE_PATHS = (
    '.github/workflows/test126-startup-memory.yml',
    'necroprobe/__init__.py', 'necroprobe/campaign099.py', 'necroprobe/campaign116.py',
    'necroprobe/campaign_diagnostics114.py', 'necroprobe/campaign_forensic116.py',
    'necroprobe/crypto.py', 'necroprobe/cycle_publication.py', 'necroprobe/deadlines.py',
    'necroprobe/irregular.py', 'necroprobe/native_cycle.py', 'necroprobe/native_walk.py',
    'necroprobe/protocol.py', 'necroprobe/rpc_diagnostics.py', 'necroprobe/test069.py',
    'necroprobe/test099.py', 'necroprobe/test111.py', 'necroprobe/test112.py',
    'necroprobe/test113.py', 'necroprobe/test114.py', 'necroprobe/test115.py',
    'necroprobe/test116.py', 'necroprobe/test117.py', 'necroprobe/test118.py',
    'necroprobe/test119.py', 'necroprobe/test120.py', 'necroprobe/test121.py',
    'necroprobe/test122.py', 'necroprobe/test123.py', 'necroprobe/test124.py',
    'necroprobe/test125.py', 'necroprobe/test126.py', 'necroprobe/trial_evidence099.py',
    'necroprobe/validation.py', 'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/check_perception_build.py', 'patches/loopctrl/run_test094_host.py',
    'patches/loopctrl/run_test116_host.py', 'patches/loopctrl/run_test126_host.py',
    'patches/loopctrl/run_test126_python39.py', 'patches/loopctrl/test_device_ci126.py',
    'patches/loopctrl/verify_package.py', 'test_125.sh', 'test_126.sh',
    'tests/test_campaign_startup125.py', 'tests/test_continuous_client116.py',
    'tests/test_continuous_client125.py', 'tests/test_continuous_client126.py',
    'tests/test_initial_restart117.py', 'tests/test_native_cycle_client094.py',
    'tests/test_native_irregular_client110.py', 'tests/test_protocol.py',
    'tests/test_restart_yield112.py', 'tests/timer_support.py',
)


def host_module():
    spec = importlib.util.spec_from_file_location('test126_python39_host', HERE/'run_test126_host.py')
    host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
    return host


def selected_suite(driver):
    if (not SCOPE_FINALIZED or PENDING_SCOPE_ITEMS or not CASES
            or type(EXPECTED_SELECTED_METHOD_COUNT) is not int
            or EXPECTED_SELECTED_METHOD_COUNT != sum(len(row[3]) for row in CASES)):
        raise ValueError('TEST126 actual Python3.9 author scope is pending')
    host = host_module(); host.ensure_scope(); host.reject_fixture_overrides()
    selected = []
    for name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST126 Python fixture escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    selected = host.selected_cases(selected)
    if len(selected) != EXPECTED_SELECTED_METHOD_COUNT:
        raise ValueError('TEST126 actual Python3.9 selected count differs')
    return host, selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 9) or platform.python_implementation() != 'CPython' or hasattr(0, 'bit_count'):
        raise SystemExit('Actual CPython3.9 is required')
    driver, output = args.driver.resolve(), args.output.resolve()
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    host, selected = selected_suite(driver)
    code = host.git(driver, 'rev-parse', 'HEAD').decode().strip()
    dependencies = set()
    for module in tuple(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path:
            try:
                relative = Path(path).resolve().relative_to(driver).as_posix()
            except ValueError:
                continue
            if relative.endswith('.py'):
                dependencies.add(relative)
    if len(SOURCE_PATHS) != len(set(SOURCE_PATHS)) or not dependencies <= set(SOURCE_PATHS):
        raise ValueError('TEST126 Python source dependency escaped the frozen inventory')
    before = {name: hashlib.sha256(host.pinned_bytes(driver, name, code)).hexdigest()
        for name in SOURCE_PATHS}
    syntax = subprocess.run(['sh', '-n', str(driver/'test_126.sh')], capture_output=True, text=True)
    check = subprocess.run([sys.executable, '-m', 'necroprobe.test126', '--check'], cwd=driver,
        capture_output=True, text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-device-failures-trial-v126 / 1.98.16-ngg2')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(schema='test126-python39-scope-v1', driver_commit=code,
        scope='actual Python3.9 TEST126 client14, retained TEST125 startup14 and direct19',
        interpreter_version=sys.version, interpreter=platform.python_implementation(),
        interpreter_executable_sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
        python_version=list(sys.version_info[:3]), source_sha256=before,
        shell_syntax=dict(returncode=syntax.returncode, stdout=syntax.stdout, stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr),
        not_run=['remaining historical client methods', 'gameplay C/Runtime/fault/world suites',
            'Spool is executed separately on actual Mac Swift', 'iPhone acceptance'], device_test='not_run')
    host.run_scope('test126-python39', selected, output, evidence, receipt_name='test126-python39-scope.json')
    after = {name: hashlib.sha256(host.pinned_bytes(driver, name, code)).hexdigest() for name in before}
    evidence.update(sources_unchanged=before == after, product_pass=entry_ok and before == after)
    (output/'test126-python39-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if not evidence['product_pass']:
        raise SystemExit('TEST126 actual Python3.9 entry/source identity must pass')


if __name__ == '__main__':
    main()
