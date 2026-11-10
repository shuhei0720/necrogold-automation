"""Run only TEST070 cadence/compatibility/publication changes and related units before device feedback.

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


CADENCE070_METHODS = frozenset({
    'test_third_strict_move_uses_earlier_image_and_preserves_original_next_beat',
    'test_each_recheck_uses_last_actual_capture_start_for_minimum_spacing',
    'test_finite_cap_reserves_the_old_one_period_final_opportunity',
    'test_eighth_late_strict_move_can_still_confirm_under_original_visual_deadline',
    'test_fourth_proof_checks_original_visual_deadline_at_actual_commit',
    'test_goods_latch_on_unstable_or_too_early_recheck_without_motion_credit',
    'test_unstable_prefix_and_owner_guards_preempt_additional_assessments',
    'test_unknown_synth_never_uses_any_visual_recheck_or_another_input',
})
COMPAT070_METHODS = frozenset({
    'test_version_map_and_feature_memberships_preserve_every_prior_revision',
    'test_unbound_diagnostics_keep_three_while_trusted_new_status_keeps_eight_recursively',
    'test_status_and_manifest_limits_are_bound_to_expected_api_and_reject_invalid_types',
    'test_encrypted_current_run_roundtrips_eight_in_status_manifest_and_both_journals',
    'test_all_historical_journals_keep_their_api_limit_and_required_evidence',
    'test_started_v14_recovers_same_uuid_and_original_api_without_a_new_start',
    'test_never_started_v14_upgrades_only_its_first_start_and_rejects_an_old_ipa',
    'test_persisted_preflight_and_result_api_cannot_cross_revision_boundaries',
})
RELEASE070_METHODS = frozenset({
    'test_new_number_isolates_archive_root_and_prevents_a_second_start',
    'test_missing_publication_is_repaired_before_a_new_run_and_default_069_stays',
    'test_invalid_numbers_do_not_read_journals_or_start',
})
RELATED_CADENCE067_METHODS = frozenset({
    'test_second_unknown_allows_early_checks_and_keeps_late_final_without_input_retry',
})
RELATED_MOTION_CADENCE_METHODS = frozenset({
    'test_third_comparison_uses_tenth_spacing_then_confirms',
    'test_eight_scheduled_unknowns_stop_without_ninth_comparison_or_input',
})
RELATED_BLOCKED_METHODS = frozenset({
    'test_matching_stable_ack_prefix_is_required_and_unknown_input_never_retries',
})
RELATED_EDGE_METHODS = frozenset({
    'test_edge_blocked_unknown_motion_or_unknown_synth_never_gets_another_input',
})
RELATED_LIGHTING_METHODS = frozenset({
    'test_fresh_pending_full_five_fields_cannot_drift',
    'test_fresh_pending_change_goods_and_guard_failures_never_send',
    'test_fresh_then_same_keeps_new_direction_and_sticky_reference_until_budget',
})
RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})
RELATED_PUBLICATION_METHODS = frozenset({
    'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh',
    'test_interrupted_or_corrupted_provider_copy_is_never_published_and_can_retry',
    'test_cancellation_and_old_runtime_leave_every_source_byte_intact',
})
RELATED_OLD_API_METHODS = frozenset({
    'test_literal_v1_through_v13_recover_ready_old_api_journals_with_no_get_or_start',
})
RELATED_OLD_IMAGES_METHODS = frozenset({
    'test_literal_legacy_recovery_keeps_its_api_uuid_clock_and_complete_image_evidence',
})
PACKAGE_SEAL_METHODS = frozenset({
    'test_native_v14_package_requires_actual_api16_and_strict_profile_v2',
})
PACKAGE_PROFILE_METHODS = frozenset({
    'test_native_v14_package_requires_both_current_strict_compiler_proofs',
})
WORKFLOW070_METHODS = frozenset({
    'test_changed_dispatch_boundary_runs_focused_runtime_before_ipa_and_keeps_evidence',
})
NATIVE_CASES = (
    ('tests.test_native_cadence070', 'NativeCadence070Tests', 'test070-cadence', CADENCE070_METHODS, True),
    ('tests.test_native_cadence067', 'NativeCadence067Tests', 'test070-related-cadence067', RELATED_CADENCE067_METHODS, False),
    ('tests.test_native_motion_cadence', 'NativeMotionCadenceTests', 'test070-related-motion-cadence', RELATED_MOTION_CADENCE_METHODS, False),
    ('tests.test_native_blocked067', 'NativeBlocked067Tests', 'test070-related-blocked', RELATED_BLOCKED_METHODS, False),
    ('tests.test_native_edge068', 'NativeEdge068Tests', 'test070-related-edge', RELATED_EDGE_METHODS, False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test070-related-lighting', RELATED_LIGHTING_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test070-related-recovery', RECOVERY_METHODS, False),
)
CLIENT_CASES = (
    ('tests.test_native_compat070', 'NativeCompatibility070Tests', 'test070-compat', COMPAT070_METHODS, True),
    ('tests.test_native_release070', 'Release070Tests', 'test070-release', RELEASE070_METHODS, True),
    ('tests.test_native_publication069', 'Publication069Tests', 'test070-related-publication', RELATED_PUBLICATION_METHODS, False),
    ('tests.test_native_recovery_results', 'RecoveryResultsTests', 'test070-related-old-api', RELATED_OLD_API_METHODS, False),
    ('tests.test_native_collection068', 'NativeCollection068Tests', 'test070-related-old-images', RELATED_OLD_IMAGES_METHODS, False),
)
PACKAGE_CASES = (
    ('test_apply_ngg2', 'NGG2ApplyTests', 'test070-package-seal', PACKAGE_SEAL_METHODS, False),
    ('test_package', 'NativePackageProfileTests', 'test070-package-profile', PACKAGE_PROFILE_METHODS, False),
    ('test_device_ci', 'DeviceNativeWorkflowTests', 'test070-workflow-boundary', WORKFLOW070_METHODS, False),
)
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception', 'tests.test_native_navigation')
NATIVE_BASELINE = '5782a4aac6ed3f2878bea0f5c97fb6cea8cb035a'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Runtime.swift',
                           'Tests/LoopCtrlKitTests/NG2RPCContractsTests.swift', 'LoopCtrlKit/RPCMethod.swift'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test070')


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


def client_source_identity(driver):
    native = importlib.import_module('necroprobe.native_walk')
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
        sources[name] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
    if (native.REVISION != 'native-walk-v15' or native.API_VERSION != '1.98.16-ngg2'
            or native.CAPABILITY != 'necrogold_native_v14'):
        raise ValueError('collection client revision/API/capability changed')
    return {'modules': sources, 'driver_commit': code, 'revision': native.REVISION, 'api_version': native.API_VERSION,
            'capability': native.CAPABILITY}


def client_suites():
    modules = {name: importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native = importlib.import_module('necroprobe.native_walk')
    publication = importlib.import_module('necroprobe.test069')
    entry = importlib.import_module('necroprobe.test070')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST070 entry is not bound to the actual driver publication wrapper')
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
        raise ValueError('TEST070 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST070 native change scope differs')
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
    record = {'scope': 'TEST070 cadence/compatibility/publication units and named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unselected client and RPC suites', 'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test070-cadence': 'up to eight same-input assessments with minimum capture spacing, original late final opportunity and unchanged deadlines/authority',
                  'test070-compat': 'new API16 revision15 alone accepts eight; all prior revision APIs, three-attempt bounds and same-run recovery stay pinned',
                  'test070-release': 'separate TEST070 spool and ZIP namespace while preserving default TEST069 publication and no-new-start boundary',
                  'test070-related-cadence067': 'migrate the changed UNKNOWN sequence while retaining final opportunity and no input retry',
                  'test070-related-motion-cadence': 'retain early strict proof and stop at exactly eight assessments without a ninth or another input',
                  'test070-related-blocked': 'UNKNOWN motion and unknown synth cannot gain stationary retry authority',
                  'test070-related-edge': 'edge UNKNOWN/BLOCKED/synth outcomes cannot send a second edge input',
                  'test070-related-lighting': 'retain FRESH/SAME direction, complete five-field proof and goods/protected/control rejection',
                  'test070-related-recovery': 'unchanged public ABI confirmed through actual C queries',
                  'test070-related-publication': 'incomplete images, interrupted copy and cancellation cannot certify a ZIP or start another game',
                  'test070-related-old-api': 'literal revision1 through13 keep API14 and same UUID without schema/start RPCs',
                  'test070-related-old-images': 'literal revision13/API14 and revision14/API15 retain PNG export cursor and evidence without republishing',
                  'test070-package-seal': 'capability14 requires actual API16 response even if a stale resealed response has a matching comment',
                  'test070-package-profile': 'capability14 requires both strict source compiler proofs before publishing provenance',
                  'test070-workflow-boundary': 'actual focused Mac Runtime step and saved evidence must precede the unchanged IPA build'}}
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
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST070 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
