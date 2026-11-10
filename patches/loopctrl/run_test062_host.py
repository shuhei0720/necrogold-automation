"""Run only TEST066 shop-action and icon changes and related unit regressions before device feedback.

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
    'test_repeated_pending_expiry_preserves_verified_progress_budget_and_episode',
    'test_pending_expiry_retains_authority_goods_and_latest_visual_guards',
    'test_pending_old_callbacks_and_backdated_clocks_cannot_trigger_recovery',
})
DOOR066_METHODS = frozenset({
    'test_unchanged_door_survives_distant_palette_drift_and_opens_before_entry',
    'test_changed_local_door_bracket_goods_or_protection_never_reuses_the_ticket',
    'test_door_requires_strict_blocked_signature_proof',
    'test_door_quiet_uses_actual_commit_and_frozen_deadline',
    'test_door_goods_cancel_and_control_authority_preempt_distant_drift',
    'test_unstable_prefix_and_started_or_unknown_door_cannot_gain_quiet_authority',
})
SHOP066_METHODS = frozenset({
    'test_partial_interior_remote_drift_keeps_original_ticket_in_four_directions',
    'test_partial_interior_changed_authority_or_motion_is_not_coalesced',
    'test_partial_interior_goods_cancel_and_live_control_guards_remain_priorities',
    'test_partial_interior_late_actual_commit_and_wrong_prefix_never_extend_ticket',
})
ICON066_METHODS = frozenset({
    'test_fragmented_two_bar_icon_with_short_label_is_a_floor',
    'test_fragmented_icon_keeps_original_intensity_boundary',
    'test_missing_one_bar_white_region_and_short_glyphs_are_not_floor',
    'test_fragmented_icon_does_not_replace_other_hud_or_menu_guards',
    'test_displaced_bars_remain_rejected_at_the_fixed_hud_location',
    'test_original_bright_bars_and_long_opening_path_still_classify_floor',
})
PERCEPTION066_METHODS = frozenset({
    'test_invalid_input_clears_output',
    'test_synthetic_state_neutral_and_vertical_guards',
    'test_synthetic_goods_unknown_partial_and_exact_counts',
    'test_synthetic_hud_thresholds_and_symmetry',
})
NATIVE_CASES = (
    ('tests.test_native_device066', 'NativeDevice066Tests', 'test066-door', DOOR066_METHODS, True),
    ('tests.test_native_shop066', 'NativeShop066Tests', 'test066-shop', SHOP066_METHODS, True),
    ('tests.test_native_icon066', 'NativeIcon066Tests', 'test066-icon', ICON066_METHODS, True),
    ('tests.test_native_gate064', 'NativeGate064Tests', 'test064-gate', GATE064_METHODS, True),
    ('tests.test_native_device065', 'NativeDevice065Tests', 'test065-related-pending', PENDING065_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test066-related-recovery', RECOVERY_METHODS, False),
    ('tests.test_native_perception', 'NativePerceptionTests', 'test066-related-perception', PERCEPTION066_METHODS, False),
)
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception')
NATIVE_BASELINE = '20a55347c13ef2aefdbfd08cff1fa02d5d3c402d'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Perception.c'}


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
        raise ValueError('TEST066 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST066 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    suites = native_suites(upstream)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST066 shop-action/icon units and named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception suites',
                          'Runtime synthetic public/mutation suites', 'synthetic shop/world suites',
                          'unchanged client and RPC suites', 'unrelated initial/cadence/unsent suites',
                          'unchanged workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test066-door': 'TEST065 fourth-run closed-door ticket, all directions and unchanged control/terrain guards',
                  'test066-shop': 'TEST065 second-run PARTIAL interior floor ticket and fresh authority negatives',
                  'test066-icon': 'TEST065 third-run fragmented pause bars, original intensity and menu/HUD negatives',
                  'test064-gate': 'retain the successful opened-gate FLOOR action before entry',
                  'test065-related-pending': 'retain bounded SAME/FRESH recovery, original episode and live authority/stale-callback rejection',
                  'test066-related-recovery': 'unchanged public ABI confirmed through actual C queries',
                  'test066-related-perception': 'public synthetic invalid-input, state/menu, goods and HUD checks; private corpus stays local'}}
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
    print('PASS TEST066 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
