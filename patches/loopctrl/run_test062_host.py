"""Run only TEST068 fringe/collection changes and related units before device feedback.

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
FRINGE068_METHODS = frozenset({
    'test_unique_outside_bracket_is_explicit_hint_without_in_grid_gold',
    'test_both_raw_gold_samples_retain_the_original_280_pixel_boundary',
    'test_masked_in_grid_pair_restores_only_the_real_two_coordinates',
    'test_one_side_solid_gold_and_multiple_pairs_supply_no_edge_authority',
    'test_heart_arrow_or_short_bottom_bars_alone_are_not_a_gold_bracket',
    'test_partial_visible_goods_and_existing_gold_keep_their_original_authority',
})
EDGE068_METHODS = frozenset({
    'test_only_explicit_down_hint_can_choose_one_observed_floor_step',
    'test_down_hint_does_not_authorize_blockers_items_protection_or_other_origins',
    'test_one_verified_edge_step_returns_to_normal_gold_route_but_never_repeats_hint',
    'test_unstarted_edge_deadline_can_refit_without_reusing_id_or_sync_budget',
    'test_edge_blocked_unknown_motion_or_unknown_synth_never_gets_another_input',
    'test_edge_authority_prefix_goods_control_and_visual_deadline_stay_frozen',
})
RELATED_CADENCE_METHODS = frozenset({
    'test_second_proof_checks_actual_commit_against_unchanged_visual_deadline',
    'test_early_second_move_can_publish_the_original_next_beat_without_reacquiring',
})
RELATED_MOTION_METHODS = frozenset({
    'test_strong_gate_detail_confirms_one_move_with_transient_overlay',
    'test_extra_evidence_requires_exact_closed_gold_bracket',
})
RELATED_PERCEPTION_METHODS = frozenset({
    'test_synthetic_state_neutral_and_vertical_guards',
    'test_gold_peak_thresholds_edges_and_colour_inequalities',
    'test_synthetic_hud_thresholds_and_symmetry',
    'test_synthetic_goods_unknown_partial_and_exact_counts',
})
RELATED_NAVIGATION_METHODS = frozenset({
    'test_signature_normalization_and_all73_scores_exact_reference',
    'test_public_one_step_zero_tween_two_opposite_and_unknown',
    'test_invalid_arguments_zero_outputs_and_do_not_authorize_input',
})
RELATED_DOOR_METHODS = frozenset({
    'test_unchanged_door_survives_distant_palette_drift_and_opens_before_entry',
})
RELATED_SHOP_METHODS = frozenset({
    'test_partial_interior_remote_drift_keeps_original_ticket_in_four_directions',
})
NATIVE_CASES = (
    ('tests.test_native_fringe068', 'NativeFringe068Tests', 'test068-fringe', FRINGE068_METHODS, True),
    ('tests.test_native_edge068', 'NativeEdge068Tests', 'test068-edge', EDGE068_METHODS, True),
    ('tests.test_native_perception', 'NativePerceptionTests', 'test068-related-perception', RELATED_PERCEPTION_METHODS, False),
    ('tests.test_native_cadence067', 'NativeCadence067Tests', 'test068-related-cadence', RELATED_CADENCE_METHODS, False),
    ('tests.test_native_motion067', 'NativeMotion067Tests', 'test068-related-motion', RELATED_MOTION_METHODS, False),
    ('tests.test_native_device066', 'NativeDevice066Tests', 'test068-related-door', RELATED_DOOR_METHODS, False),
    ('tests.test_native_shop066', 'NativeShop066Tests', 'test068-related-shop', RELATED_SHOP_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test068-related-recovery', RECOVERY_METHODS, False),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test068-related-navigation', RELATED_NAVIGATION_METHODS, False),
)
COLLECTION068_METHODS = frozenset({
    'test_verified_complete_images_are_revalidated_without_image_or_per_image_journal_writes',
    'test_slow_complete_replay_fits_the_original_attempt_by_avoiding_unchanged_writes',
    'test_completed_metadata_never_replaces_validation_of_saved_bytes_or_the_full_cursor',
    'test_complete_png_header_and_geometry_are_checked_even_with_a_matching_full_digest',
    'test_complete_fragment_without_identical_published_image_uses_the_existing_publish_order',
    'test_complete_revalidation_checks_deadline_and_cancel_after_reading_without_republishing',
    'test_literal_legacy_recovery_keeps_its_api_uuid_clock_and_complete_image_evidence',
})
COLLECTION068_CLI_METHODS = frozenset({
    'test_cli_announces_read_only_recovery_before_status_and_separates_goods_from_old_collection_timeout',
    'test_cli_incomplete_recovery_reports_collection_failure_without_claiming_a_new_game',
})
RELATED_PAGED_METHODS = frozenset({
    'test_fragment_rename_before_checkpoint_replays_identical_bytes_and_rejects_conflicts',
    'test_final_image_rename_before_image_checkpoint_is_recovered_without_another_input',
    'test_final_journal_io_cannot_publish_a_late_or_newly_cancelled_export_as_resolved',
    'test_manifest_processing_and_zero_or_already_verified_exports_still_check_the_attempt_deadline',
    'test_full_png_digest_and_header_are_verified_before_image_publish',
})
RELATED_IMAGE_METHODS = frozenset({
    'test_atomic_journal_tolerates_only_unsupported_directory_fsync',
    'test_old_journal_images_project_extra_fields_and_resave_no_secrets',
})
RELATED_CLIENT_METHODS = frozenset({
    'test_unknown_terminal_is_retained_and_reexecution_cannot_start_again',
})
CLIENT_CASES = (
    ('tests.test_native_collection068', 'NativeCollection068Tests', 'test068-collection', COLLECTION068_METHODS, True),
    ('tests.test_native_collection068', 'NativeCollection068CliTests', 'test068-collection-cli', COLLECTION068_CLI_METHODS, True),
    ('tests.test_native_paged_results', 'PagedResultsTests', 'test068-related-paged', RELATED_PAGED_METHODS, False),
    ('tests.test_native_walk', 'NativeImageTests', 'test068-related-image', RELATED_IMAGE_METHODS, False),
    ('tests.test_native_walk', 'NativeWalkTests', 'test068-related-client', RELATED_CLIENT_METHODS, False),
)
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception', 'tests.test_native_navigation')
NATIVE_BASELINE = '0b8a4cce4a216c28d841de256393bbec56d52b9a'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Core.h', 'LoopCtrlUITests/NG2Controller.c',
                           'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Perception.c'}


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
    path = driver / 'necroprobe/native_walk.py'
    if Path(native.__file__).resolve() != path:
        raise ValueError('collection client was imported outside the actual driver')
    code = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=driver, text=True).strip()
    committed = subprocess.check_output(['git', 'show', code+':necroprobe/native_walk.py'], cwd=driver)
    raw = path.read_bytes()
    if raw != committed:
        raise ValueError('collection client differs from the pinned driver commit')
    if (native.REVISION != 'native-walk-v14' or native.API_VERSION != '1.98.15-ngg2'
            or native.CAPABILITY != 'necrogold_native_v13'):
        raise ValueError('collection client revision/API/capability changed')
    return {'path': 'necroprobe/native_walk.py', 'sha256': hashlib.sha256(raw).hexdigest(),
            'driver_commit': code, 'revision': native.REVISION, 'api_version': native.API_VERSION,
            'capability': native.CAPABILITY}


def client_suites():
    modules = {name: importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native = importlib.import_module('necroprobe.native_walk')
    for name, module in modules.items():
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        for fixture in (module, alias):
            if fixture is not None and fixture.native is not native:
                raise ValueError('collection fixture is not bound to the actual driver client: '+name)
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in CLIENT_CASES]


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
        raise ValueError('TEST068 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST068 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites()
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST068 fringe/collection units and named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime synthetic public/mutation suites', 'synthetic shop/world suites',
                          'unselected client and RPC suites', 'unrelated initial/icon/unsent suites',
                          'unchanged workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test068-fringe': 'unique raw gold pair and original pixel boundaries; no fabricated grid coordinates or HUD authority',
                  'test068-edge': 'one observed DOWN floor step with one-run limit, frozen authority and bounded unstarted recovery',
                  'test068-collection': 'validated completed bytes avoid republishing while cursor, PNG, cancel, deadline and legacy evidence remain mandatory',
                  'test068-collection-cli': 'read-only collection notice precedes RPC; terminal native reason and collection completion are distinct',
                  'test068-related-perception': 'preserve existing state/HUD guards, gold peak thresholds and exact goods counts',
                  'test068-related-cadence': 'preserve successful original next beat and actual-commit visual deadline',
                  'test068-related-motion': 'preserve transient-overlay one-step proof and exact closed gold bracket requirement',
                  'test068-related-door': 'retain closed-door opening and entry distinction on normal gold routes',
                  'test068-related-shop': 'retain PARTIAL interior floor action in all four directions',
                  'test068-related-recovery': 'unchanged public ABI confirmed through actual C queries',
                  'test068-related-navigation': 'independent 73-score parity, original motion classifications and invalid-input rejection',
                  'test068-related-paged': 'preserve atomic rename recovery, final cancel/deadline checks and full PNG validation',
                  'test068-related-image': 'preserve atomic journal durability and closed legacy image projection',
                  'test068-related-client': 'UNKNOWN terminal recovery must keep the same run without a new start'}}
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
    print('PASS TEST068 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
