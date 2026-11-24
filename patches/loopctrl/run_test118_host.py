"""TEST118 exact source and boundary selection; pending scopes fail closed."""
import argparse
import ctypes
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test118_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = '419b558681ed1c12b01db26c5dadad1f569fcd7e'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Ring.c'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset({
    'AGENTS.md', '.github/workflows/loopctrl-geometry.yml', 'necroprobe/campaign116.py',
    'patches/loopctrl/apply_ngg2.py', 'patches/loopctrl/ngg2-manifest.json', 'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/ngg2/NG2Controller.c', 'patches/loopctrl/ngg2/NG2Ring.c',
    'patches/loopctrl/verify_package.py', 'tests/test_continuous_client117.py',
    'tests/test_native_controller.py', 'tests/test_native_offer_witness109.py',
})
NEW_PATHS = frozenset({
    'necroprobe/test118.py', 'test_118.sh', 'tests/test_continuous_client118.py',
    'tests/test_native_preinput_refresh118.py', 'tests/test_native_price_fragments118.py',
    'tests/test_native_upper118.py', 'tests/test_native_floor_moments118.py',
    'tests/test_native_current_data118.py', 'tests/test_native_upper_single_face118.py',
    'tests/test_native_upper_begin118.py',
    'tests/test_native_upper_single_controller118.py', 'patches/loopctrl/run_test118_host.py',
    'patches/loopctrl/run_test118_python39.py', 'patches/loopctrl/test_device_ci118.py',
    'patches/loopctrl/check_runtime118.py', 'patches/loopctrl/ngg2_runtime118_tests.swift',
    'patches/loopctrl/ngg2_runtime118_fixture.c', 'patches/loopctrl/generate_shop118_pixels.py',
})
CASES = (
    ('patches.loopctrl.test_device_ci118', 'DeviceImplementationCapability118Tests', 'test118-capability', frozenset({
        'test_current_patch_advertises_the_exact_118_implementation',
        'test_sealing_metadata_requires_the_real_array_entry_not_comments_or_duplicates',
        'test_package_records_118_binding_without_changing_API_or_profile',
        'test_resealed_mismatched_118_metadata_patch_and_rpc_are_rejected',
        'test_prior_manifests_do_not_gain_an_unrequested_118_claim',
    }), True),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test118-package-related', frozenset({
        'test_native_cycle_requires_strict_ring_profile_three_without_changing_legacy_cap',
        'test_changed_and_new_source_install_together',
        'test_seal_pins_each_canonical_shared_source_without_repository_copies',
        'test_seal_still_rejects_empty_native_assets_despite_shared_kernel',
        'test_native_v14_package_requires_actual_api16_and_strict_profile_v2',
        'test_native_v15_evidence_package_keeps_api16_and_strict_profile_v2',
        'test_package_provenance_rejects_even_resealed_stale_runtime_envelope_api',
        'test_package_provenance_rejects_changed_native_source',
    }), False),
    ('tests.test_native_price_fragments118', 'NativePriceFragments118Tests', 'test118-price-fragments', frozenset({
        'test_lower_entry_uses_existing_eighteen_ink_rule_for_small_nonprice_fragments',
        'test_independent_fourth_price_at_eighteen_ink_still_rejects_absence',
        'test_small_fragment_cannot_replace_missing_price_or_cap_visibility',
        'test_target_image_and_own_price_stay_prior_to_nonprice_fragment',
    }), True),
    ('tests.test_native_preinput_refresh118', 'NativePreinputRefresh118Tests', 'test118-preinput', frozenset({
        'test_same_tiles_independent_preinput_source_reissues_same_logical_MOVE_once',
        'test_capture_start_spacing_boundary_and_nonoverlap_are_required',
        'test_once_is_keyed_by_logical_epoch_not_reissued_command_ID',
        'test_spacing_origin_stays_at_frozen_logical_source_after_ordinary_reissue',
        'test_clear_passage_same_tiles_uses_new_primary_with_original_epoch',
        'test_at_not_before_optional_refresh_keeps_old_authority',
        'test_first_step_and_started_ACK_UNKNOWN_do_not_refresh',
        'test_bad_prefix_stability_same_capture_and_reverse_time_do_not_refresh',
        'test_nonzero_and_unknown_Motion_never_supply_a_new_source',
        'test_changed_protection_item_and_local_terrain_do_not_use_optional_refresh',
        'test_chain_and_run_budget_exhaustion_are_optional_noops',
    }), True),
    ('tests.test_native_upper118', 'NativeUpper118Tests', 'test118-upper', frozenset({
        'test_same_opening_remote_gold_and_shielded_palette_get_data_not_motion',
        'test_row4_one_sign_route_keeps_parent_through_all_four_safe_steps',
        'test_candidate_and_target_never_fund_a_row4_input',
        'test_changed_protection_or_unknown_next_floor_cannot_fund_move',
        'test_first_v2_snapshot_may_finish_after_data_return_if_born_after_source',
        'test_first_snapshot_before_worker_or_result_cannot_prepare',
        'test_row4_admission_allocates_one_period_once_and_funds_fifth_step',
    }), True),
    ('tests.test_native_upper_begin118', 'NativeUpperBegin118Tests', 'test118-upper-begin', frozenset({
        'test_exact_V2_pair_reuses_normal_zero_at_begin_with_newer_current',
        'test_discarded_new_capture_cannot_use_the_old_pair_cache',
        'test_new_nonzero_signature_cannot_borrow_a_previous_zero',
        'test_changed_floor_protection_or_old_gold_never_borrows_cached_zero',
        'test_candidate_target_and_new_job_preempt_the_old_cached_command',
        'test_owner_cancel_and_original_deadline_still_revoke_begin',
        'test_old_id_is_inert_and_begin_attempt_consumes_only_its_own_proof',
        'test_V1_retains_its_normal_begin_motion_call',
    }), True),
    ('tests.test_native_floor_moments118', 'NativeFloorMoments118Tests', 'test118-floor-moments', frozenset({
        'test_mottled_floor_uses_both_raw_moments_without_moving_thresholds',
        'test_mean_cancelling_foreign_colors_cannot_prove_the_cap',
        'test_both_halves_keep_texture_visibility_brightness_and_gain_guards',
        'test_existing_three_percent_bound_is_exact_on_both_sides',
        'test_observed_caps_extra_items_prices_protection_and_hud_stay_required',
        'test_strong_target_and_old_offer_policy_results_are_preserved',
    }), True),
    ('tests.test_native_current_data118', 'NativeCurrentData118Tests', 'test118-current-data', frozenset({
        'test_pending_full_keeps_normal_negative_without_reviving_observation_move',
        'test_data_downgrade_unknown_stays_held_without_observation_move',
        'test_bound_positive_remains_prior_to_distant_material',
        'test_changed_goods_protection_local_floor_door_and_gold_loss_still_veto',
        'test_a_later_safe_image_does_not_erase_a_prior_sticky_rejection',
        'test_unchanged_source_keeps_existing_two_proof_observation_path',
        'test_downgrade_cannot_reopen_an_observation_epoch_after_result',
        'test_a_fresh_material_image_does_not_extend_the_original_parent',
    }), True),
    ('tests.test_native_upper_single_face118', 'NativeUpperSingleFace118Tests', 'test118-upper-single-face', frozenset({
        'test_mirrored_four_rows_high_entrance_and_small_measured_offsets',
        'test_every_one_of_fourteen_supports_and_the_opening_is_required',
        'test_three_items_lower_floors_caps_exact_halo_and_row_one_stay_required',
        'test_one_full_face_three_prices_and_uncovered_objects_stay_observed',
        'test_eighteen_ink_price_support_and_dual_floor_moments_are_inherited',
        'test_strong_target_and_priceless_candidate_precede_any_negative',
        'test_numeric_evidence_cannot_be_forged_or_relabelled_from_another_row',
    }), True),
    ('tests.test_native_upper_single_controller118', 'NativeUpperSingleFaceController118Tests', 'test118-upper-single-controller', frozenset({
        'test_normal_mirrored_high_entrance_reaches_durable_restart_and_next_floor',
        'test_c_rechecks_all_fourteen_supports_opening_and_exact_three_offer_footprint',
        'test_a_typed_numeric_certificate_cannot_replace_scene_geometry_or_prices',
        'test_target_and_priceless_candidate_stay_held_before_any_negative_restart',
    }), True),
    ('tests.test_native_controller', 'NativeControllerTests', 'test118-controller-related', frozenset({
        'test_continuous_run_limit_eight_and_first_latest_diagnostics',
    }), False),
    ('tests.test_native_shop117', 'NativeFullCurrentData117Tests', 'test118-retained-full-data', frozenset({
        'test_changed_goods_masks_player_neighborhood_walls_and_old_candidates_veto_data',
        'test_current_unknown_is_held_without_phase_proofs_or_move_credit',
        'test_finite_latest_full_data_accepts_normal_negative_in_both_callback_orders',
        'test_new_current_epoch_invalidates_negative_but_keeps_bound_positive_priority',
        'test_parent_equality_or_stale_latest_cannot_start_a_new_data_epoch',
        'test_prepared_pause_is_retired_only_while_definitely_unbegun',
    }), True),
    ('tests.test_native_shop117', 'NativePartialFootprint117Tests', 'test118-retained-partial-entry', frozenset({
        'test_actual_walk_cells_unexplained_masks_and_parent_deadline_still_veto_entry',
        'test_exact_item_halo_is_not_dilated_again_over_actual_entry_destination',
        'test_remote_observed_wall_retires_old_partial_into_new_data_with_original_horizon',
    }), True),
    ('tests.test_native_initial_restart_controller117', 'NativeInitialRestartController117Tests', 'test118-retained-initial-restart', frozenset({
        'test_default_false_still_resumes_and_continuous_successor_rejects_optin',
        'test_early_post_ack_goods_preserves_first_job_and_input_settle',
        'test_first_floor_goods_cannot_be_erased_by_a_later_clear_frame',
        'test_fixed_first_source_parent_is_not_renewed_by_fresh_views',
        'test_initial_floor_unknown_uses_pause_then_restart_without_a_ring_absence_job',
        'test_initial_goods_nonpositive_verdict_is_a_skip_without_negative_credit',
        'test_initial_pause_is_restart_only_and_first_floor_enters_normal_mode',
        'test_initial_ui_completion_does_not_claim_old_fingerprint_change',
        'test_initial_visible_or_partial_pending_and_positive_result_never_restart',
        'test_live_menu_and_original_parent_are_rechecked_before_begin',
        'test_unknown_synth_never_reissues_initial_restart',
        'test_wrong_job_and_unaggregated_or_late_positive_never_grant_restart',
        'test_wrong_prefix_or_missing_hud_does_not_complete_initial_ui',
    }), True),
    ('tests.test_native_ring117', 'NativeRing117Tests', 'test118-retained-lower-negative', frozenset({
        'test_closed_price_recovers_same_row_without_turning_partial_into_absence',
        'test_new_numeric_witness_rejects_field_forgery',
        'test_new_price_layout_has_generic_absence_and_its_own_numeric_bounds',
        'test_new_price_layout_requires_exact_projection_and_all_supporting_floors',
        'test_one_complete_face_with_observed_lower_entrance_certifies_three_offers',
        'test_original_partial_positive_search_outside_selected_strip_is_retained',
        'test_single_face_requires_each_observed_support_and_complete_merchandise',
        'test_three_independent_price_glyphs_do_not_require_identity_of_another_product',
    }), True),
    ('tests.test_native_shop117', 'NativeSingleLowerEntryController117Tests', 'test118-retained-lower-adoption', frozenset({
        'test_immutable_anchor_and_numeric_fields_are_rechecked_independently',
        'test_layout3_complete_certificate_translation_cannot_cross_central_pixel_domain',
        'test_layout3_rechecks_exact_anchor_and_each_separate_price_boundary',
        'test_ordinary_producer_certificate_reaches_durable_restart_and_next_floor',
        'test_shared_lower_price_geometry_reaches_independent_adoption_and_real_restart',
    }), True),
)
CORE_MODULES = shared.CORE_MODULES
MAC_CASE_GROUPS = (('check_runtime118.py', ('preinput_refresh', 'upper_side_hhddd', 'full_data_palette')),)
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh')
PRESERVED_PATHS = (*shared.UNCHANGED_CONTINUATION_PATHS,
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2Raster.swift', 'patches/loopctrl/ngg1.patch',
    'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST118 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED:
        raise ValueError('TEST118 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES, MAC_CASE_GROUPS)):
        raise ValueError('TEST118 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST118 empty or duplicate selected native scope')
    mac_cases = [case for _checker, methods in MAC_CASE_GROUPS for case in methods]
    if not mac_cases or len(mac_cases) != len(set(mac_cases)) or any(not methods for _, methods in MAC_CASE_GROUPS):
        raise ValueError('TEST118 selected Mac boundary scope is empty or duplicated')


def source_identity(driver, sealed, upstream):
    ensure_scope(); reject_fixture_overrides()
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    path = 'patches/loopctrl/ngg2-manifest.json'; raw = pinned_bytes(driver, path, code)
    manifest = json.loads(raw)
    old = manifest_sources(json.loads(git(driver, 'show', NATIVE_BASELINE+':'+path)))
    current = sealed['native_source_sha256']
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST118 exact native changed/added inventory differs')
    if manifest_sources(manifest) != current or any(manifest.get(k) != v for k, v in EXPECTED_API.items()):
        raise ValueError('TEST118 installed source/API/capability identity differs')
    spec = importlib.util.spec_from_file_location('test118_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST118 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST118 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_118.sh').strip():
        raise ValueError('TEST118 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST118 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST118 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST118 preserved source changed: '+name)
        preserved[name] = sha(data)
    fixtures = {name.replace('.', '/')+'.py' for name in (*CORE_MODULES, *(row[0] for row in CASES))}
    fixtures.update(p for p in NEW_PATHS if p.startswith(('tests/', 'patches/loopctrl/')))
    fixtures.update('patches/loopctrl/run_test'+v+'_host.py' for v in ('094', '116', '117'))
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE, native_manifest_sha256=sha(raw),
        changed_native_sources=sorted(changed), native_added=sorted(added),
        preserved_native_source_sha256={n: v for n, v in current.items() if n not in changed|added},
        fixture_source_sha256={p: sha(pinned_bytes(driver, p, code)) for p in sorted(fixtures)},
        product_sha256={p: sha(pinned_bytes(driver, p, code)) for p in PRODUCT_PATHS},
        fixture_compile_source_binding=compile_binding, preserved_source_sha256=preserved,
        retained_root_compile_scope='driver source byte-identical to sealed additions; not sealed-location compilation',
        changed_repository_paths=sorted(existing), new_repository_paths=sorted(new),
        mac_case_groups=[dict(checker=checker, cases=list(cases)) for checker, cases in MAC_CASE_GROUPS],
        historical_runtime_replayed=False, limitation='Software checks do not establish iPhone reach rate or speed.')


def native_suites(upstream, driver):
    ensure_scope(); reject_fixture_overrides()
    shared.CASES, shared.CORE_MODULES = CASES, CORE_MODULES
    return shared.native_suites(upstream, driver)


def run_scope(name, cases, output, evidence, *, receipt_name='test118-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test118-host-scope.json', 'test118-python39-scope.json'):
        raise ValueError('TEST118 scope receipt name is not permitted')
    cases = selected_cases(cases); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue(); (output/(name+'.txt')).write_text(log); print(log, end='', flush=True)
    evidence[name] = dict(selected=[c.id() for c in cases], tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures))
    (output/receipt_name).write_text(json.dumps(evidence, indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': selected methods must all execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args(); ensure_scope()
    driver, upstream, output = (getattr(args, n).resolve() for n in ('driver', 'upstream', 'output'))
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    verifier = importlib.import_module('verify_package')
    sealed = verifier.inspect_native_sources(upstream, driver); binding = source_identity(driver, sealed, upstream)
    suites = native_suites(upstream, driver); selected_cases(c for _, cases in suites for c in cases)
    native = importlib.import_module('tests.test_native_controller'); cycle = importlib.import_module('tests.test_native_cycle094')
    abi = {n: ctypes.sizeof(getattr(native, n)) for n in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    abi['Cycle'] = ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456, Cycle=216):
        raise ValueError('TEST118 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST118 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        not_run=['unchanged historical Runtime/spool suites', 'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci118')
    run_scope('test118-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection118Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST118 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test118-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST118 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
