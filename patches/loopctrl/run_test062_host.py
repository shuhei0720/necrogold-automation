"""Run only TEST067 motion-confirmation changes and related unit regressions before device feedback.

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
import subprocess
import unittest


RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})
CADENCE067_METHODS = frozenset({
    'test_second_complete_image_uses_tenth_capture_start_boundary_and_frozen_ticket',
    'test_second_image_with_unstable_or_wrong_prefix_never_uses_the_new_slot',
    'test_first_image_still_requires_ack_and_target_settling_boundary',
    'test_second_proof_checks_actual_commit_against_unchanged_visual_deadline',
    'test_second_unknown_keeps_full_period_third_and_never_retries_the_input',
    'test_early_second_move_can_publish_the_original_next_beat_without_reacquiring',
})
BLOCKED067_METHODS = frozenset({
    'test_floor_gate_blocked_reacquires_once_in_four_directions_without_progress_credit',
    'test_second_stationary_attempt_stops_and_cannot_receive_another_retry',
    'test_changed_gate_goods_or_local_proof_cannot_gain_stationary_retry',
    'test_matching_stable_ack_prefix_is_required_and_unknown_input_never_retries',
    'test_actual_visual_deadline_and_previous_verified_sync_budget_are_not_extended',
    'test_goods_cancel_and_control_guards_preempt_recovery_or_its_new_ticket',
})
MOTION067_METHODS = frozenset({
    'test_strong_gate_detail_confirms_one_move_with_transient_overlay',
    'test_extra_evidence_requires_floor_unknown_goods_and_no_protection',
    'test_extra_evidence_requires_exact_closed_gold_bracket',
    'test_stationary_reverse_partial_and_two_tiles_are_not_one_move',
    'test_weak_flat_and_ambiguous_repeating_texture_stays_unknown',
    'test_existing_normal_moves_blocks_openings_and_unexpected_are_preserved',
})
RELATED_CADENCE_METHODS = frozenset({
    'test_first_complete_move_is_immediate_without_cadence_delay',
    'test_third_comparison_waits_a_full_frozen_period_then_confirms',
    'test_three_scheduled_unknowns_stop_without_fourth_comparison_or_input',
    'test_goods_on_a_skipped_retry_still_latch_and_never_send_another_direction',
    'test_tween_and_unknown_share_the_same_settling_schedule',
})
RELATED_NAVIGATION_METHODS = frozenset({
    'test_signature_normalization_and_all73_scores_exact_reference',
    'test_public_one_step_zero_tween_two_opposite_and_unknown',
    'test_closed_gate_high_intensity_rescue_and_repeated_texture_rejection',
    'test_coarse_thresholds_and_texture_support_signed_regions_boundaries',
    'test_signed_texture_thresholds_exact75_95_and15point_lead',
    'test_invalid_arguments_zero_outputs_and_do_not_authorize_input',
})
RELATED_DOOR_METHODS = frozenset({
    'test_unchanged_door_survives_distant_palette_drift_and_opens_before_entry',
    'test_door_requires_strict_blocked_signature_proof',
})
RELATED_SHOP_METHODS = frozenset({
    'test_partial_interior_remote_drift_keeps_original_ticket_in_four_directions',
    'test_partial_interior_changed_authority_or_motion_is_not_coalesced',
})
RELATED_PENDING_METHODS = frozenset({
    'test_pending_expiry_retains_authority_goods_and_latest_visual_guards',
    'test_pending_old_callbacks_and_backdated_clocks_cannot_trigger_recovery',
})
NATIVE_CASES = (
    ('tests.test_native_cadence067', 'NativeCadence067Tests', 'test067-cadence', CADENCE067_METHODS, True),
    ('tests.test_native_blocked067', 'NativeBlocked067Tests', 'test067-blocked', BLOCKED067_METHODS, True),
    ('tests.test_native_motion067', 'NativeMotion067Tests', 'test067-motion', MOTION067_METHODS, True),
    ('tests.test_native_motion_cadence', 'NativeMotionCadenceTests', 'test067-related-cadence', RELATED_CADENCE_METHODS, False),
    ('tests.test_native_device066', 'NativeDevice066Tests', 'test067-related-door', RELATED_DOOR_METHODS, False),
    ('tests.test_native_shop066', 'NativeShop066Tests', 'test067-related-shop', RELATED_SHOP_METHODS, False),
    ('tests.test_native_device065', 'NativeDevice065Tests', 'test067-related-pending', RELATED_PENDING_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test067-related-recovery', RECOVERY_METHODS, False),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test067-related-navigation', RELATED_NAVIGATION_METHODS, False),
)
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception', 'tests.test_native_navigation')
NATIVE_BASELINE = '0a7062aeccc9fe10eda931223c6c75f000266bf2'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c'}


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
        raise ValueError('TEST067 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST067 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    suites = native_suites(upstream)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST067 motion-confirmation units and named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime synthetic public/mutation suites', 'synthetic shop/world suites',
                          'unchanged client and RPC suites', 'unrelated initial/icon/unsent suites',
                          'unchanged workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test067-cadence': 'second comparison at frozen one-tenth period; original ACK/prefix/ticket and deadline boundaries',
                  'test067-blocked': 'one fresh bounded gate attempt after a confirmed stationary input without fabricated progress',
                  'test067-motion': 'high-contrast closed one-tile evidence under transient text with strict ambiguity and protection rejection',
                  'test067-related-cadence': 'preserve immediate first comparison, full-period third, three-result budget and goods/TWEEN priorities',
                  'test067-related-door': 'retain closed-door opening/entry distinction and stationary signature authority',
                  'test067-related-shop': 'retain PARTIAL interior floor action and protected/motion rejection',
                  'test067-related-pending': 'retain live authority, gold/protected safety and stale callback clock rejection',
                  'test067-related-recovery': 'unchanged public ABI confirmed through actual C queries',
                  'test067-related-navigation': 'independent 73-score parity, signed geometry, repeated texture/support boundaries and invalid-input rejection'}}
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
    print('PASS TEST067 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
