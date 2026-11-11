"""Run TEST080 sparse closed-gate motion and independently closed passage units with named related regressions.

All native fixtures compile the sealed patched upstream used by the IPA.
Historical synthetic worlds and Runtime mutation suites remain explicit lanes.
"""
import argparse
import ctypes
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import unittest


SPARSE_GATE080_METHODS = frozenset({
    'test_public_four_direction_sparse_arrival_reaches_closed_door_without_entry',
    'test_scope_closed_geometry_old_anchors_and_observed_endpoints_are_required',
    'test_only_all_positive_infinite_legacy_and_unknown_output_may_use_proof',
    'test_phase_uses_all_nine_actual_dependencies_and_fixed_disjoint_bands',
    'test_phase_all73_matches_independent_scalar_specification',
    'test_phase_score_gap_support_bands_contrast_and_gain_boundaries',
    'test_fixed_axis_strength_and_all73_competitor_lead_are_required',
    'test_zero_reverse_two_cells_partial_pixels_and_known_public_results_are_distinct',
})

CLOSED_MOUTH080_METHODS = frozenset({
    'test_independent_closed_upper_and_left_mouth_use_existing_restart_without_step_credit',
    'test_only_closed_candidate_retires_and_other_fixed_candidate_is_still_inspected',
    'test_unknown_changed_or_unsupported_mouth_never_becomes_a_closed_inspection',
    'test_independence_stable_prefix_and_strict_zero_are_required_before_any_restart',
    'test_original_two_beat_and_walk_session_deadlines_are_not_extended',
    'test_gold_goods_protection_cancel_owner_and_unknown_input_preempt_closed_skip',
})

RELATED_NAVIGATION_METHODS = frozenset({
    'test_closed_gate_high_intensity_rescue_and_repeated_texture_rejection',
    'test_signed_texture_thresholds_exact75_95_and15point_lead',
})

RELATED_CLOSED_GATE_METHODS = frozenset({
    'test_public_four_direction_arrival_returns_next_door_without_entry',
    'test_cache_equals_direct_scalar_all73_and_camera_center_bands_are_independent',
})

RELATED_REVEALED_GATE_METHODS = frozenset({
    'test_public_four_direction_reveal_is_a_unit_then_nav_approaches_without_entry',
    'test_raw_normal_side_unit_gap_and_known_output_boundaries',
})

RELATED_CONTROLLER_METHODS = frozenset({
    'test_door_and_dirt_opening_count_operation_without_step',
    'test_goods_frame_preserves_evidenced_move_before_holding_pause',
})

RELATED_PASSAGE_METHODS = frozenset({
    'test_shadowed_outer_goal_waits_for_observed_floor_and_never_steps_unknown',
    'test_final_vantage_requires_independent_clear_before_restart',
    'test_multiple_fixed_mouths_are_retained_until_both_independent_inspections',
    'test_walked_restart_uses_endpoint_fingerprint_and_level_local_calibration',
    'test_unknown_sent_exploration_and_restart_cannot_issue_or_reset',
    'test_uncertain_floor_gold_evidence_revokes_local_completion_and_skip',
})

RELATED_VIEW_METHODS = frozenset({
    'test_genuine_post_ui_passage_reaches_first_move_and_moved_origin_is_not_reclassified',
})

RELATED_STATIONARY_METHODS = frozenset({
    'test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit',
})

RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})

NATIVE_CASES = (
    ('tests.test_native_sparse_gate080', 'NativeSparseGate080Tests', 'test080-sparse-gate', SPARSE_GATE080_METHODS, True),
    ('tests.test_native_closed_mouth080', 'NativeClosedMouth080Tests', 'test080-closed-mouth', CLOSED_MOUTH080_METHODS, True),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test080-related-navigation', RELATED_NAVIGATION_METHODS, False),
    ('tests.test_native_closed_gate078', 'NativeClosedGate078Tests', 'test080-related-closed-gate', RELATED_CLOSED_GATE_METHODS, False),
    ('tests.test_native_revealed_gate079', 'NativeRevealedGate079Tests', 'test080-related-revealed-gate', RELATED_REVEALED_GATE_METHODS, False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test080-related-controller', RELATED_CONTROLLER_METHODS, False),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test080-related-passage', RELATED_PASSAGE_METHODS, False),
    ('tests.test_native_view074', 'NativeView074Tests', 'test080-related-view', RELATED_VIEW_METHODS, False),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test080-related-stationary', RELATED_STATIONARY_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test080-related-recovery', RECOVERY_METHODS, False),
)

CLIENT_CASES = ()
PACKAGE_CASES = ()
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception',
                'tests.test_native_motion067', 'tests.test_native_blocked067',
                'tests.test_native_observation072', 'tests.test_native_ui073',
                'tests.test_native_passage_unsent076', 'test_native_perception')
NATIVE_BASELINE = '88705eac9c64ace365a1bc8e60bbc3f50399ec10'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Controller.c'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test080',
                         'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_',
                             'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_',
                             'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_',
                             'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_',
                             'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_')

def reject_fixture_overrides():
    present = sorted(name for name in os.environ
                     if name.startswith(FIXTURE_OVERRIDE_PREFIXES) or name == 'BASELINE_NAV')
    if present:
        raise ValueError('sealed fixture baseline overrides are forbidden: '+', '.join(present))


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
    reject_fixture_overrides()
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
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in NATIVE_CASES]


def client_source_identity(driver):
    native = importlib.import_module('necroprobe.native_walk')
    validation = importlib.import_module('necroprobe.validation')
    protocol = importlib.import_module('necroprobe.protocol')
    code = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=driver, text=True).strip()
    sources = {}
    for name in CLIENT_SOURCE_MODULES:
        module = importlib.import_module(name)
        relative = name.replace('.', '/')+'.py'
        path = driver / relative
        if Path(module.__file__).resolve() != path:
            raise ValueError('client module was imported outside the actual driver: '+name)
        committed = subprocess.check_output(['git', 'show', code+':'+relative], cwd=driver)
        raw = path.read_bytes()
        if raw != committed:
            raise ValueError('client module differs from the pinned driver commit: '+name)
        if name != 'necroprobe.test080' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST080 client source differs from the baseline: '+name)
        sources[name] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
    if (native.REVISION != 'native-walk-v15' or native.API_VERSION != '1.98.16-ngg2'
            or native.CAPABILITY != 'necrogold_native_v14'):
        raise ValueError('collection client revision/API/capability changed')
    if (protocol.json_object is not validation.json_object
            or protocol.Client._call.__globals__.get('json_object') is not validation.json_object
            or native.json_object is not validation.json_object
            or native.Client is not protocol.Client):
        raise ValueError('actual RPC client is not bound to the pinned JSON validator')
    return {'modules': sources, 'driver_commit': code, 'revision': native.REVISION, 'api_version': native.API_VERSION,
            'capability': native.CAPABILITY,
            'json_binding': {'protocol_json_object_is_validation_json_object': True,
                            'client_call_global_is_validation_json_object': True,
                            'native_json_object_is_validation_json_object': True,
                            'native_client_is_protocol_client': True}}


def client_suites():
    modules = {name: importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native = importlib.import_module('necroprobe.native_walk')
    publication = importlib.import_module('necroprobe.test069')
    entry = importlib.import_module('necroprobe.test080')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST080 entry is not bound to the actual driver publication wrapper')
    for name, module in modules.items():
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        for fixture in (module, alias):
            if fixture is not None and getattr(fixture, 'native', native) is not native:
                raise ValueError('collection fixture is not bound to the actual driver client: '+name)
            if fixture is not None and getattr(fixture, 'publication', publication) is not publication:
                raise ValueError('publication fixture is not bound to the actual driver wrapper: '+name)
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in CLIENT_CASES]


def package_suites():
    return [(label, method_cases(getattr(importlib.import_module(name), class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in PACKAGE_CASES]


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
    if (before['api_version'] != '1.98.16-ngg2' or before['client_capability'] != 'necrogold_native_v14'
            or len(before['native_source_sha256']) != 22):
        raise ValueError('TEST080 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST080 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST080 sparse closed-gate motion and independently closed passage units with named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'fixture_source_policy': {'baseline_override_env_prefixes': list(FIXTURE_OVERRIDE_PREFIXES),
                  'baseline_override_env_names': ['BASELINE_NAV'],
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unchanged Perception and JSON suites (same TEST079 bytes; historical results are not current TEST080 executions)',
                          'unchanged client and RPC suites', 'unchanged package/profile and client version unit suites',
                          'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {'test080-sparse-gate': 'a fully unavailable legacy phase may use the fixed expanded phase and strict spatial image evidence only for an exact closed-gate unit; finite legacy candidates and known outputs retain their old meaning', 'test080-closed-mouth': 'a reached fixed mouth is retired as locally closed only after independent strict stationary wall proof within all original budgets; this grants no movement or outside-goal inspection credit', 'test080-related-navigation': 'prior closed-gate and signed texture threshold boundaries remain unchanged', 'test080-related-closed-gate': 'prior arrival/entry separation, cached all73 evidence and camera-center bands stay intact', 'test080-related-revealed-gate': 'the preceding singleton reveal and original raw/known-result boundaries remain intact', 'test080-related-controller': 'opening does not credit displacement and visible goods preserve evidenced movement before pausing', 'test080-related-passage': 'unknown outer goals, independent final clearance, fixed multiple candidates, level calibration, uncertain gold and unknown-input stops retain their original behavior', 'test080-related-view': 'initial-room candidate retirement remains distinct from a moved camera origin', 'test080-related-stationary': 'unknown unsent passage or shop evidence retires authority without motion credit', 'test080-related-recovery': 'unchanged public ABI confirmed through actual C queries'}}
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
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST080 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
