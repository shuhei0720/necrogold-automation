"""Run TEST078 closed gate arrival units with named related regressions.

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


CLOSED_GATE078_METHODS = frozenset({
    'test_public_four_direction_arrival_returns_next_door_without_entry',
    'test_zero_reverse_two_cells_partial_and_known_primary_stay_distinct',
    'test_scope_requires_both_unknown_candidate_unprotected_item_free_floors',
    'test_exact_closed_geometry_keeps_all_gold_and_rejects_other_gate_patterns',
    'test_raw_phase_boundaries_and_known_results_are_not_overwritten',
    'test_axis_is_fixed_per_frame_with_all_actual_dependencies_and_ui_checked',
    'test_cache_equals_direct_scalar_all73_and_camera_center_bands_are_independent',
    'test_support_strength_two_bands_and_sufficient_competitor_lead_boundaries',
})

RELATED_NAVIGATION_METHODS = frozenset({
    'test_closed_gate_high_intensity_rescue_and_repeated_texture_rejection',
    'test_signed_texture_thresholds_exact75_95_and15point_lead',
    'test_opening_is_not_entry_and_dirt_requires_both_unprotected',
    'test_invalid_arguments_zero_outputs_and_do_not_authorize_input',
})

RELATED_MOTION074_METHODS = frozenset({
    'test_stationary_lighting_opening_has_gradient_evidence_in_four_directions',
    'test_arrival_proof_does_not_authorize_or_require_a_future_step',
    'test_original_primary_classification_and_invalid_abi_remain_unchanged',
})

RELATED_STATIC075_METHODS = frozenset({
    'test_same_floor_gradient_confirms_only_blocked_in_four_directions',
    'test_static_proof_requires_safe_unchanged_local_scene_and_gold_set',
})

RELATED_MOTION075_METHODS = frozenset({
    'test_existing_primary_and_invalid_inputs_remain_unchanged',
})

RELATED_CONTROLLER_METHODS = frozenset({
    'test_door_and_dirt_opening_count_operation_without_step',
    'test_goods_frame_preserves_evidenced_move_before_holding_pause',
    'test_cancel_foreground_owner_and_unknown_synth_never_retry_waited_direction',
})

RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})

NATIVE_CASES = (
    ('tests.test_native_closed_gate078', 'NativeClosedGate078Tests', 'test078-closed-gate', CLOSED_GATE078_METHODS, True),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test078-related-navigation', RELATED_NAVIGATION_METHODS, False),
    ('tests.test_native_motion074', 'NativeMotion074Tests', 'test078-related-motion074', RELATED_MOTION074_METHODS, False),
    ('tests.test_native_static075', 'NativeStatic075Tests', 'test078-related-static075', RELATED_STATIC075_METHODS, False),
    ('tests.test_native_motion075', 'NativeMotion075Tests', 'test078-related-motion075', RELATED_MOTION075_METHODS, False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test078-related-controller', RELATED_CONTROLLER_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test078-related-recovery', RECOVERY_METHODS, False),
)

CLIENT_CASES = ()
PACKAGE_CASES = ()
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception',
                'tests.test_native_motion067', 'tests.test_native_blocked067',
                'test_native_perception')
NATIVE_BASELINE = '63ca426770349bab73953241982a171d76ca35e6'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Navigation.c'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test078',
                         'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_',
                             'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_',
                             'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_',
                             'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_')


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
        if name != 'necroprobe.test078' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST078 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test078')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST078 entry is not bound to the actual driver publication wrapper')
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
        raise ValueError('TEST078 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST078 native change scope differs')
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
    record = {'scope': 'TEST078 closed gate arrival units with named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'fixture_source_policy': {'baseline_override_env_prefixes': list(FIXTURE_OVERRIDE_PREFIXES),
                  'baseline_override_env_names': ['BASELINE_NAV'],
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unchanged Perception and JSON suites (same TEST077 bytes; historical results are not current TEST078 executions)',
                          'unchanged client and RPC suites', 'unchanged package/profile and client version unit suites',
                          'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test078-closed-gate': 'only a previously UNKNOWN strict unit arrival below a closed gold gate may gain supplemental motion evidence; geometry, independent gradient bands and original score/support limits remain required',
                  'test078-related-navigation': 'existing high-intensity gate rescue, signed texture thresholds, opening versus entry, dirt protection and invalid-input outputs remain unchanged',
                  'test078-related-motion074': 'the existing stationary opening gradient, arrival without future-step authority and known primary classifications remain unchanged',
                  'test078-related-static075': 'same-floor gradients still prove only BLOCKED and require safe unchanged local terrain and gold',
                  'test078-related-motion075': 'known primary and invalid-input results remain unchanged, including all73 cached-gradient parity',
                  'test078-related-controller': 'opening does not credit displacement, visible goods preserve evidenced movement, and cancelled, owner-lost or unknown sent input never retries',
                  'test078-related-recovery': 'unchanged public ABI confirmed through actual C queries'}}
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
    print('PASS TEST078 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
