"""Run only TEST065 pending-expiry changes and related unit regressions before device feedback.

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


CONTROLLER_METHODS = frozenset({
    'test_continuous_expiry_after_revalidation_never_searches_later_beat',
    'test_continuous_original_deadline_equality_and_expiry',
    'test_continuous_chain_limit_two_then_stops_without_next_beat',
    'test_continuous_run_limit_eight_and_first_latest_diagnostics',
    'test_continuous_prefix_stability_and_started_ack_unknown_never_reissue',
    'test_continuous_guard_or_cancel_after_revalidation_rejects_new_and_old_ids',
    'test_continuous_pending_change_stops_instead_of_accumulating_refreshes',
})
RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})
UNSENT_CONTINUOUS_METHODS = frozenset({
    'test_complete_zero_late_retires_known_unsent_ticket_and_restarts_from_verified_pose',
    'test_same_and_fresh_reissues_retire_without_mutating_old_fields',
    'test_started_ack_unknown_cancel_and_goods_never_use_unsent_recovery',
    'test_repeated_unsent_recovery_keeps_original_episode_and_deadline',
})
INITIAL064_METHODS = frozenset({
    'test_initial_remote_flicker_preserves_ticket_across_publication_window',
    'test_initial_remote_flicker_after_replan_budget_and_refit_keeps_budget',
    'test_initial_remote_coalescing_uses_actual_commit_and_original_deadline',
    'test_initial_early_window_rejects_changed_authority',
    'test_initial_early_window_control_guards_and_goods_priority',
})
GATE064_METHODS = frozenset({
    'test_distant_dirt_stone_drift_keeps_same_gate_ticket_and_can_begin',
    'test_gate_local_gold_protected_and_blocker_changes_are_not_coalesced',
    'test_gate_signature_drift_requires_actual_blocked_motion_proof',
    'test_gate_expired_commit_never_reuses_an_in_time_capture_end',
    'test_gate_goods_latch_and_cancel_preempt_distant_drift',
    'test_gate_discarded_prefix_and_inflight_frames_supply_no_new_authority',
})
PENDING065_METHODS = frozenset({
    'test_pending_same_and_fresh_expiry_reacquire_without_rewriting_retired_ticket',
    'test_pending_original_deadline_equality_still_reissues_only_the_same_beat',
    'test_repeated_pending_expiry_preserves_verified_progress_budget_and_episode',
    'test_pending_expiry_cannot_reopen_sync_walk_or_session_budget',
    'test_pending_expiry_retains_authority_goods_and_latest_visual_guards',
    'test_pending_old_callbacks_and_backdated_clocks_cannot_trigger_recovery',
})
NATIVE_CASES = (
    ('tests.test_native_device065', 'NativeDevice065Tests', 'test065-pending', PENDING065_METHODS, True),
    ('tests.test_native_device064', 'NativeDevice064Tests', 'test064-initial', INITIAL064_METHODS, True),
    ('tests.test_native_gate064', 'NativeGate064Tests', 'test064-gate', GATE064_METHODS, True),
    ('tests.test_native_controller', 'NativeControllerTests', 'test065-related-controller', CONTROLLER_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test065-related-recovery', RECOVERY_METHODS, False),
    ('tests.test_native_unsent_continuous', 'NativeUnsentContinuousTests', 'test063-related-unsent', UNSENT_CONTINUOUS_METHODS, False),
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
        raise ValueError('TEST065 sealed source identity is not installed')
    suites = native_suites(upstream)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST065 pending-expiry C units and named related regressions; device feedback first',
              'source_identity': before, 'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat suites', 'Runtime synthetic public/mutation suites',
                          'synthetic shop/world suites', 'unchanged client and RPC suites',
                          'unchanged TEST062 cadence suite', 'remaining unrelated TEST063 unsent cases', 'superseded TEST061 quiet-window cases',
                          'unchanged workflow/publisher unit suites'],
              'selection_reasons': {
                  'test065-pending': 'TEST064 fourth-run pending SAME/FRESH expiry; original ticket, current authority and bounded recovery',
                  'test064-initial': 'retain the successful initial publication-window and authority path',
                  'test064-gate': 'retain the successful UNKNOWN/PARTIAL stationary shop-entry path',
                  'test065-related-controller': 'pending-state changes, original deadline equality, counters2/8 and prefix/input/ownership guards',
                  'test065-related-recovery': 'unchanged public ABI confirmed through actual C queries',
                  'test063-related-unsent': 'retain state1 late-unsent recovery, frozen reissues, state exclusions and original episode budget'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci', ('DeviceHostSelectionTests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test062-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    record['sealed_sources_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST065 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
