"""Run only TEST072 observed shop fixes and passage approach changes and related units before device feedback.

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


DOOR072_METHODS = frozenset({
    'test_sparse_opening_uses_strong_independent_terrain_in_four_directions',
    'test_protected_gold_walls_allow_the_observed_interior_floor',
    'test_opening_requires_a_preserved_bracket_and_unprotected_endpoints',
    'test_invalid_scenes_are_rejected_before_the_supplemental_proof',
    'test_weak_repeating_one_band_and_ui_only_pixels_do_not_prove_an_opening',
    'test_nonzero_and_existing_primary_motion_results_are_not_reclassified',
    'test_gold_wall_exception_never_allows_protected_floor_or_other_cells',
})
OBSERVATION072_METHODS = frozenset({
    'test_unknown_goods_observed_vantage_keeps_original_beat_for_irrelevant_drift',
    'test_protected_gold_wall_does_not_block_the_same_observed_entry',
    'test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket',
    'test_current_floor_refresh_rejects_changed_action_protection_and_old_input_authority',
    'test_independent_floor_proof_and_published_ticket_keep_full_current_permission',
    'test_current_hud_fifty_ms_preparation_and_original_budgets_remain_required',
    'test_goods_cancellation_phase_and_owner_guards_preempt_observing_or_issued_refresh',
    'test_refresh_limit_is_once_per_verified_progress_and_eight_per_session',
})
PASSAGE_NAV072_METHODS = frozenset({
    'test_candidate_bits_cover_annotated_families_and_multiple_mouths',
    'test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps',
    'test_shadowed_mouth_requires_outside_floor_and_wall_line_support',
    'test_unknown_outside_uses_a_monotone_observed_vantage_then_new_view',
    'test_invalid_start_gold_goods_ordinary_exits_and_protection_do_not_explore',
    'test_chooser_rejects_unsafe_steps_invalid_world_targets_and_unreachable_floor',
    'test_fixed_second_mouth_remains_reachable_across_the_initial_room',
    'test_shop_chooser_stays_separate_and_null_outputs_fail_closed',
})
PASSAGE072_METHODS = frozenset({
    'test_gold_clear_passage_moves_on_observed_floor_instead_of_restarting',
    'test_moved_gold_reveal_uses_normal_shop_without_restart',
    'test_final_vantage_requires_independent_clear_before_restart',
    'test_gold_reveal_retires_unsent_exploration_before_new_shop_ticket',
    'test_walked_restart_uses_endpoint_fingerprint_and_level_local_calibration',
    'test_restart_never_extends_original_walk_equality_deadline',
    'test_goods_item_and_protection_hold_at_every_exploration_stage',
    'test_cancel_foreground_and_owner_stop_every_exploration_stage',
    'test_unknown_sent_exploration_and_restart_cannot_issue_or_reset',
    'test_shadowed_outer_goal_waits_for_observed_floor_and_never_steps_unknown',
    'test_multiple_fixed_mouths_are_retained_until_both_independent_inspections',
    'test_restarted_level_retune_and_initial_recovery_use_local_zero',
    'test_partial_or_protected_after_inspection_revokes_pause_and_restart_authority',
    'test_new_gold_revokes_skip_and_started_pause_holds_candidate',
    'test_one_native_session_restarts_searches_enters_and_completes_only_on_goods',
    'test_final_inspection_discards_old_prefix_unstable_and_overlapping_frames',
    'test_acknowledged_unknown_visual_motion_never_becomes_another_exploration_step',
    'test_acknowledged_restart_proves_new_gold_level_before_normal_shop',
    'test_new_shop_ticket_requires_hud_at_or_after_independent_geometry_proof',
    'test_first_skip_pause_new_gold_starts_walk_once_at_real_device_uptime',
    'test_uncertain_floor_gold_evidence_revokes_local_completion_and_skip',
    'test_pause_ui_gold_unknown_is_not_uncertain_floor_and_can_restart',
})
RELATED_SHOP_METHODS = frozenset({
    'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker',
    'test_exception_does_not_allow_other_local_cells_materials_or_missing_open_ack',
})
RELATED_NAV_METHODS = frozenset({
    'test_signature_normalization_and_all73_scores_exact_reference',
})
RELATED_LEVEL_METHODS = frozenset({
    'test_preparation_epoch_fresh_dirt_and_door_keep_identity_without_safe_floor_or_reference',
    'test_restart_unchanged_timeout_never_resends',
    'test_initial_sync_twelve_second_limit_and_walk_forty_five',
    'test_fresh_and_same_share_run_eight_and_chain_two_budgets',
})
RELATED_CADENCE_METHODS = frozenset({
    'test_third_strict_move_uses_earlier_image_and_preserves_original_next_beat',
    'test_goods_latch_on_unstable_or_too_early_recheck_without_motion_credit',
})
RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})
NATIVE_CASES = (
    ('tests.test_native_door072', 'NativeDoor072Tests', 'test072-door', DOOR072_METHODS, True),
    ('tests.test_native_observation072', 'NativeObservation072Tests', 'test072-observation', OBSERVATION072_METHODS, True),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test072-passage-navigation', PASSAGE_NAV072_METHODS, True),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test072-passage-control', PASSAGE072_METHODS, True),
    ('tests.test_native_shop071', 'NativeShop071Tests', 'test072-related-shop', RELATED_SHOP_METHODS, False),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test072-related-navigation', RELATED_NAV_METHODS, False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test072-related-level', RELATED_LEVEL_METHODS, False),
    ('tests.test_native_cadence070', 'NativeCadence070Tests', 'test072-related-cadence', RELATED_CADENCE_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test072-related-recovery', RECOVERY_METHODS, False),
)
CLIENT_CASES = ()
PACKAGE_CASES = ()
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception', 'tests.test_native_navigation')
NATIVE_BASELINE = '605f2e5c526cf2da515235550a471133750dd05d'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
                           'LoopCtrlUITests/NG2Core.h'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test072')


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
    entry = importlib.import_module('necroprobe.test072')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST072 entry is not bound to the actual driver publication wrapper')
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
        raise ValueError('TEST072 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST072 native change scope differs')
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
    record = {'scope': 'TEST072 observed shop fixes and passage approach units and named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unselected client and RPC suites', 'unchanged package/profile and client version unit suites',
                          'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test072-door': 'supplemental zero-vector door opening retains original scores and primary motions; protected GOLD differs from protected walkable floors',
                  'test072-observation': 'exhausted same-action updates retire the unsent ticket and require independent current proof under original budgets and authority',
                  'test072-passage-navigation': 'fixed top/left mouths and world targets use only observed safe floors; ambiguity, protected routes and ordinary exits fail closed',
                  'test072-passage-control': 'bounded passage approach, interruption and gold handoff; independent clear before restart and level reset preserve global diagnostics and budgets',
                  'test072-related-shop': 'retain verified gold entrance and old-ticket retirement without movement credit when new observation proof is required',
                  'test072-related-navigation': 'retain independent normalization and all73 original intensity scores',
                  'test072-related-level': 'retain dig/door preparation identity, SAME/FRESH caps, unchanged-restart timeout and original sync/walk clocks',
                  'test072-related-cadence': 'retain early next-beat proof and goods priority before visual assessment',
                  'test072-related-recovery': 'unchanged public ABI confirmed through actual C queries with the extended pure helper header'}}
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
    print('PASS TEST072 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
