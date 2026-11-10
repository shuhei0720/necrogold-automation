"""Run only TEST062 changes and related unit regressions before device feedback.

All native fixtures compile the sealed patched upstream used by the IPA.
Historical synthetic worlds and Runtime mutation suites remain explicit lanes.
"""
import argparse
import ctypes
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import unittest


DEVICE_METHODS = frozenset({
    'test_late_initial_irrelevant_flickers_preserve_ticket_and_reach_ack',
    'test_late_initial_coalescing_window_and_actual_commit_boundaries',
    'test_late_initial_coalescing_rejects_changed_authority',
})
CADENCE_METHODS = frozenset({
    'test_first_complete_move_is_immediate_without_cadence_delay',
    'test_adjacent_unknown_frames_do_not_exhaust_attempts_before_quarter_move',
    'test_quarter_boundary_uses_capture_start_and_skips_even_a_complete_frame',
    'test_third_comparison_waits_a_full_frozen_period_then_confirms',
    'test_three_scheduled_unknowns_stop_without_fourth_comparison_or_input',
    'test_visual_expiry_is_checked_before_a_retry_would_be_skipped',
    'test_goods_on_a_skipped_retry_still_latch_and_never_send_another_direction',
    'test_tween_and_unknown_share_the_same_settling_schedule',
})
CONTROLLER_METHODS = frozenset({
    'test_initial_replan_rejects_unsafe_or_changed_evidence',
    'test_initial_replan_discards_unstable_wrong_prefix_and_old_capture',
    'test_initial_replan_keeps_original_deadline_equal_and_rejects_one_ns_late',
    'test_initial_replan_guard_and_cancel_still_reject_latest_id',
    'test_initial_replan_never_reopens_sent_or_unknown_input',
    'test_initial_replan_same_beat_and_new_source_motion_in_all_four_directions',
    'test_goods_frame_after_original_motion_deadline_holds_without_move_credit',
    'test_cancel_foreground_owner_and_unknown_synth_never_retry_waited_direction',
})
RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
    'test_actual_commit_after_visual_deadline_rejects_all_proof_branches',
    'test_actual_tick_after_visual_deadline_cannot_issue_from_any_proof',
    'test_unknown_synth_never_enters_visual_or_recovery',
})
UNSENT_CONTINUOUS_METHODS = frozenset({
    'test_complete_zero_late_retires_known_unsent_ticket_and_restarts_from_verified_pose',
    'test_direct_begin_and_tick_late_share_definite_unsent_retirement',
    'test_same_and_fresh_reissues_retire_without_mutating_old_fields',
    'test_expired_old_callbacks_cannot_advance_recovery_state_or_clock',
    'test_new_slot_is_future_and_prepared_without_extra_input',
    'test_in_time_complete_zero_does_not_recover_and_deadline_equality_can_begin',
    'test_started_ack_unknown_cancel_and_goods_never_use_unsent_recovery',
    'test_live_authority_failures_prioritize_cancellation_over_recovery',
    'test_proof_twelve_second_equality_and_late_stop_without_new_episode',
    'test_repeated_unsent_recovery_keeps_original_episode_and_deadline',
    'test_only_new_verified_motion_can_start_new_recovery_budget',
    'test_proof_budget_uses_actual_commit_and_global_budgets_do_not_reopen',
})
NATIVE_CASES = (
    ('tests.test_native_device061', 'NativeDevice061Tests', 'test062-initial', DEVICE_METHODS, True),
    ('tests.test_native_motion_cadence', 'NativeMotionCadenceTests', 'test062-cadence', CADENCE_METHODS, True),
    ('tests.test_native_controller', 'NativeControllerTests', 'test062-related-controller', CONTROLLER_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test062-related-recovery', RECOVERY_METHODS, False),
    ('tests.test_native_unsent_continuous', 'NativeUnsentContinuousTests', 'test063-unsent-continuous', UNSENT_CONTINUOUS_METHODS, True),
)
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery', 'tests.test_native_beat')


def selected_cases(cases):
    cases = list(cases)
    identifiers = [case.id() for case in cases]
    if not cases or len(identifiers) != len(set(identifiers)):
        raise ValueError('missing or duplicate device cases')
    return cases


def method_cases(case_type, methods, *, exact=False):
    available = set(unittest.defaultTestLoader.getTestCaseNames(case_type))
    if not methods or not methods <= available or (exact and available != set(methods)):
        raise ValueError('device method inventory changed: ' + case_type.__name__)
    return selected_cases(case_type(method) for method in sorted(methods))


def native_suites(upstream):
    names = tuple(dict.fromkeys((*CORE_MODULES, *(case[0] for case in NATIVE_CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for module in modules.values():
        module.CORE = upstream / 'LoopCtrlUITests'
    # Support fixture imports under their historical bare names without
    # selecting either module's unrelated tests.
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream / 'LoopCtrlUITests'
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in NATIVE_CASES]


def run_scope(name, cases, output, record):
    cases = selected_cases(cases)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue()
    (output / (name + '.txt')).write_text(log)
    print(log, end='', flush=True)
    record[name] = {'selected': [case.id() for case in cases], 'tests_run': result.testsRun,
                   'failures': len(result.failures), 'errors': len(result.errors),
                   'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures)}
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    if (result.testsRun != len(cases) or not result.wasSuccessful()
            or result.skipped or result.expectedFailures):
        raise RuntimeError(name + ': selected device tests must execute Green without skips/errors')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    driver, upstream, output = (value.resolve() for value in (args.driver, args.upstream, args.output))
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver/'tests'), str(driver/'patches/loopctrl')]
    verifier = importlib.import_module('verify_package')
    before = verifier.inspect_native_sources(upstream, driver)
    if (before['api_version'] != '1.98.15-ngg2' or before['client_capability'] != 'necrogold_native_v13'
            or len(before['native_source_sha256']) != 22):
        raise ValueError('TEST062 sealed source identity is not installed')
    suites = native_suites(upstream)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST062 changed C units and named related regressions; device feedback first',
              'source_identity': before, 'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat suites', 'Runtime synthetic public/mutation suites',
                          'synthetic shop/world suites', 'unchanged client and RPC suites']}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci', ('DeviceNativeWorkflowTests', 'DeviceHostSelectionTests', 'DownloadPublisherTests')),
                                 ('test_focused_ci', ('FocusedNativeWorkflowTests',))):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test062-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    record['sealed_sources_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST062 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
