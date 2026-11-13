"""TEST097 selected candidates, motion and partial continuation contracts.

Current C units test software contracts, not iPhone/game acceptance. Fresh Mac
API/spool/export checks and the bounded PAUSE Runtime096 callbacks run separately.
The old Runtime094 PAUSE-before-classifier fixture is preserved, not executed.
"""
import argparse
import ctypes
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test097_shared_source_utils', HERE/'run_test096_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '0f6953fb3f685641cba84d5eb289c6669e7b1942'
RUNTIME_BASELINE = 'c071f41d4a38b4b513d342ea3f3c68f5db8ec067'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c'})
CASES = (
    ('tests.test_native_occluded_corner097', 'NativeOccludedCorner097Tests', 'test097-occluded-corner',
     frozenset({
         'test_elbow_requires_each_observed_turn_wall_floor_and_unknown_direct_outside',
         'test_fixed_world_chooser_advances_only_existing_floor_and_holds_before_unknown',
         'test_left_elbow_uses_diagonal_outside_floor_without_inventing_direct_outside_floor',
         'test_old_mouths_shadows_corners_and_unrelated_sides_keep_original_masks',
         'test_scene_central_floor_goods_gold_all_protection_and_abi_guards_are_preserved',
         'test_upper_dark_portal_and_inside_materials_do_not_authorize_walls_doors_or_hidden_floor',
         'test_upper_requires_independent_outer_roof_and_left_boundary_positive_walls',
         'test_upper_shadow_retains_floor_or_unknown_inside_and_mixed_opaque_wall_support',
     }), True),
    ('tests.test_native_preserved_sparse097', 'NativePreservedSparse097Tests', 'test097-preserved-sparse',
     frozenset({
         'test_complete_witness_rois_and_observed_endpoints_are_required',
         'test_exact_old_gold_stones_and_unique_projection_are_required',
         'test_finite_rank_and_independent_sparse_axis_planes_are_required',
         'test_four_directions_need_only_the_arrival_floor',
         'test_known_results_and_input_scenes_remain_unchanged',
         'test_old_dirt_support_and_noncollinearity_are_required',
         'test_other_displacements_and_scene_scope_do_not_credit_a_unit',
         'test_public_sparse_known_one_cell_is_not_lost',
     }), True),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test097-partial-entry',
     frozenset({
         'test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit',
         'test_nearby_or_protected_material_and_other_stone_destinations_are_not_quiet',
         'test_new_ticket_keeps_its_frozen_bounds_and_completed_opening_id_does_not_revive',
         'test_original_prefix_continuation_horizon_and_cancel_remain_required',
         'test_partial_relation_still_requires_same_decision_and_independent_strict_zero',
         'test_remote_stone_to_dirt_keeps_observation_credit',
         'test_shield_permission_requires_actual_same_direction_opening_and_unchanged_gold',
     }), True),
    ('tests.test_native_partial_framing097', 'NativePartialFraming097Tests', 'test097-partial-framing',
     frozenset({
         'test_empty_unknown_keeps_result_and_waits_for_independent_up_framing',
         'test_exactly_one_move_requires_new_assessment_and_cannot_reuse_old_ticket',
         'test_framing_requires_actual_up_opening_and_correct_result_domain',
         'test_hypothetical_fringe_item_bounds_and_new_hud_occlusion_are_conservative',
         'test_independent_frame_needs_original_item_protection_choice_and_zero',
         'test_new_full_observation_before_framing_move_gets_new_normal_job',
         'test_original_horizon_cancel_and_foreground_guards_never_renew_framing',
         'test_same_or_pre_release_frame_wrong_prefix_and_unstable_cannot_release_credit',
         'test_top_item_and_protection_are_positive_complete_footprint_witnesses',
     }), True),
    ('tests.test_native_sparse_gate080', 'NativeSparseGate080Tests', 'test097-related-sparse080',
     frozenset({
         'test_fixed_axis_strength_and_all73_competitor_lead_are_required',
         'test_only_all_positive_infinite_legacy_and_unknown_output_may_use_proof',
         'test_phase_all73_matches_independent_scalar_specification',
         'test_phase_score_gap_support_bands_contrast_and_gain_boundaries',
         'test_phase_uses_all_nine_actual_dependencies_and_fixed_disjoint_bands',
         'test_public_four_direction_sparse_arrival_reaches_closed_door_without_entry',
         'test_scope_closed_geometry_old_anchors_and_observed_endpoints_are_required',
         'test_zero_reverse_two_cells_partial_pixels_and_known_public_results_are_distinct',
     }), True),
    ('tests.test_native_single_gold086', 'NativeSingleGold086Tests', 'test097-related-single-gold086',
     frozenset({
         'test_axis_independence_all73_competition_and_blur_dependency_closure_are_required',
         'test_complete_old_stones_dirt_support_noncollinearity_and_unique_nine_are_required',
         'test_public_four_directions_retained_single_gold_unit_requires_independent_old15_unknown_proof',
         'test_raw_all73_phase_unit_and_both_strong_planes_keep_their_original_boundaries',
         'test_scope_gold_projection_endpoints_global_materials_and_known_results_remain_separate',
     }), False),
    ('tests.test_native_revealed_singleton096', 'NativeRevealedSingleton096Tests', 'test097-related-revealed096',
     frozenset({
         'test_both_proof_domains_move_in_four_directions_without_future_floor_credit',
         'test_common_floor_goods_protection_direction_and_scene_bounds_fail_closed',
         'test_entire_old_and_projected_witness_rois_exclude_hud',
         'test_every_placement_is_checked_before_a_unique_unit_is_accepted',
         'test_existing_nonunknown_motion_is_untouched_and_inputs_are_immutable',
         'test_finite_runner_exact_unit_and_separate_raw_domains_reject_bad_rankings',
         'test_independent_pixel_strength_and_both_spatial_regions_are_required',
         'test_nine_matched_old_dirt_and_noncollinear_old_gold_stone_support_are_required',
         'test_old_single_gold_closed_bracket_and_only_unknown_new_leaf_are_required',
         'test_old_stone_cannot_be_replaced_by_new_stone_or_near_material_changes',
         'test_public_known_unit_reveals_side_gate_with_one_old_stone',
     }), True),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test097-related-mouth072',
     frozenset({
         'test_candidate_bits_cover_annotated_families_and_multiple_mouths',
         'test_chooser_rejects_unsafe_steps_invalid_world_targets_and_unreachable_floor',
         'test_fixed_second_mouth_remains_reachable_across_the_initial_room',
         'test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps',
         'test_invalid_start_gold_goods_ordinary_exits_and_protection_do_not_explore',
         'test_shadowed_mouth_requires_outside_floor_and_wall_line_support',
         'test_shop_chooser_stays_separate_and_null_outputs_fail_closed',
         'test_unknown_outside_uses_a_monotone_observed_vantage_then_new_view',
     }), True),
    ('tests.test_native_supported_mouth084', 'NativeSupportedMouth084Tests', 'test097-related-supported084',
     frozenset({
         'test_gold_goods_invalid_scenes_and_ordinary_right_down_exits_stay_out',
         'test_missing_flank_needs_outside_floor_and_three_current_walls',
         'test_observed_outside_floor_with_one_unknown_flank_selects_fixed_upper_left_mouths',
         'test_old_two_wall_and_shadowed_mouth_masks_and_source_bytes_are_preserved',
         'test_only_current_safe_floor_paths_authorize_approach',
     }), True),
    ('tests.test_native_corner_vantage086', 'NativeCornerVantage086Tests', 'test097-related-corner086',
     frozenset({
         'test_fixed_world_mouth_approaches_only_floor_and_holds_until_a_new_observed_route',
         'test_observed_mouth_outside_two_walls_and_unknown_inboard_are_all_required',
         'test_only_four_fixed_upper_left_corners_gain_the_new_hypothesis',
         'test_scene_guards_and_all_original_ten_mouth_branches_stay_unchanged',
         'test_unknown_inboard_keeps_observed_corner_candidate_for_safe_vantage',
         'test_vantage_requires_observed_shortest_three_step_route_and_clear_crosses',
     }), True),
    ('tests.test_native_shadow_passage094', 'NativeShadowPassage094Tests', 'test097-related-shadow094',
     frozenset({
         'test_black_gaps_other_sides_goods_gold_protection_and_invalid_scenes_fail_closed',
         'test_fixed_world_mouth_moves_only_on_observed_floor_then_holds',
         'test_four_dark_cells_and_observed_short_floor_vantage_are_required',
         'test_marked_shadow_shape_keeps_unknown_and_adds_only_fixed_upper_left_mouth',
         'test_original_ten_mouths_supported_mouths_and_corner_masks_remain_unchanged',
         'test_tall_brown_column_and_opposite_roof_wall_are_required',
     }), True),
    ('tests.test_native_split_shadow095', 'NativeSplitShadow095Tests', 'test097-related-split095',
     frozenset({
         'test_all_six_dark_cells_remain_unknown_and_are_required',
         'test_both_roof_sides_and_lower_left_wall_need_observed_support',
         'test_fixed_world_mouth_uses_three_actual_floor_steps_then_holds',
         'test_marked_split_roof_adds_only_fixed_upper_left_hypothesis',
         'test_observed_approach_floor_shortest_path_and_all_protections_are_required',
         'test_old_candidates_and_invalid_gold_goods_other_corners_are_preserved',
     }), True),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test097-related-cycle094',
     frozenset({
         'test_ack_and_real_changed_floor_wait_for_linked_outcome_durability',
         'test_actual_closed_container_footprints_fit_only_the_ignored_policy_strip',
         'test_container_extension_rejects_one_pixel_overflow_cross_slot_and_unknown',
         'test_deadline_and_cancelled_worker_results_are_inert',
         'test_goods_hold_keeps_cycle_open_after_real_pause_observation',
         'test_ignored_closed_container_is_explicit_policy_witness',
         'test_inflight_goods_credit_real_move_once_and_keep_unknown_motion_held',
         'test_late_old_level_writer_failure_cannot_change_new_search',
         'test_negative_authority_needs_durable_checkpoint_and_new_pause_source',
         'test_negative_missing_or_conflicting_witness_is_held',
         'test_negative_restart_begin_rechecks_cumulative_walk_deadline_after_writer_wait',
         'test_partial_candidate_survives_queued_full_goods_unknown_or_negative',
         'test_partial_credit_unproven_change_retires_new_move_and_holds',
         'test_partial_observe_more_uses_one_new_safe_move_without_reviving_old_ticket',
         'test_partial_safe_flag_without_observed_slot_is_not_continuation_authority',
         'test_queued_full_frame_becomes_a_fresh_serial_job_after_safe_partial',
         'test_recorded_named_full_sprite_poses_use_finite_bank_search_not_presence_window',
         'test_restart_begin_requires_exact_durable_intent_and_fresh_pause',
         'test_restart_changed_floor_with_partial_goods_starts_new_bound_hold_after_outcome',
         'test_restart_changed_floor_with_visible_goods_starts_new_bound_hold_after_outcome',
         'test_search_restart_crossed_first_goods_waits_for_current_stable_prefix',
         'test_search_restart_first_partial_goods_drains_and_binds_new_level',
         'test_search_restart_first_visible_goods_drains_and_binds_new_level',
         'test_search_restart_unchanged_goods_holds_without_new_level_or_retry',
         'test_storage_failure_pauses_then_stops_without_fabricating_durability',
         'test_storage_failure_revokes_an_already_reserved_restart_before_begin',
         'test_target_candidate_and_unknown_keep_pause_without_restart',
         'test_two_shops_continue_and_fourth_shop_holds_with_cumulative_budget',
         'test_unknown_synth_freeze_survives_late_classifier_and_writer',
     }), True),
    ('tests.test_native_partial_continuation095', 'NativePartialContinuation095Tests', 'test097-related-partial095',
     frozenset({
         'test_only_remote_unprotected_dirt_to_floor_or_unknown_is_admitted',
         'test_remote_change_cannot_clear_candidate_or_started_unknown',
         'test_remote_change_requires_strict_zero_prefix_stability_and_original_deadline',
         'test_remote_dirt_clearance_after_new_ticket_keeps_its_frozen_qualified_input',
         'test_remote_dirt_clearance_in_first_post_assessment_frame_keeps_new_observation_credit',
     }), True),
    ('tests.test_native_opened_entry093', 'NativeOpenedEntry093Tests', 'test097-related-opened093',
     frozenset({
         'test_expired_partial_entry_reacquires_independent_future_permission',
         'test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative',
         'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
         'test_original_ticket_windows_epochs_and_actual_begin_boundaries_are_frozen',
         'test_projected_top_goods_growth_and_shrink_use_latest_separate_ticket',
         'test_projection_surface_gold_and_motion_counterexamples_reject_revalidation',
     }), True),
    ('tests.test_native_shop071', 'NativeShop071Tests', 'test097-related-shop071',
     frozenset({
         'test_exception_does_not_allow_other_local_cells_materials_or_missing_open_ack',
         'test_goods_cancel_and_control_guards_preempt_preserved_entry',
         'test_original_actual_deadline_and_matching_stable_prefix_remain_required',
         'test_unknown_entry_synth_never_reuses_the_quiet_permission',
         'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker',
     }), True),
)

CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_controller',
    'tests.test_native_first_gold083',
    'tests.test_native_motion067',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_passage_motion082',
    'tests.test_native_perception',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_side_gate081',
    'tests.test_target_assessment087',
)
DEPENDENCY_FIXTURES = ()
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,
    'necroprobe/test096.py', 'test_096.sh',
    'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/test_device_ci096.py',
    *shared.CURRENT_MAC_SOURCES)
PRODUCT_PATHS = ('necroprobe/test097.py', 'test_097.sh')
CURRENT_MAC_SOURCES = shared.CURRENT_MAC_SOURCES
NAV086_FILES = shared.shared.AXIS091_FILES
nav086_snapshot = shared.shared.axis091_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO097_') for name in os.environ):
        raise ValueError('TEST097 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST097 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST097 scope is empty or duplicated')
    required = {'tests.test_native_occluded_corner097', 'tests.test_native_preserved_sparse097',
                'tests.test_native_partial_entry097', 'tests.test_native_partial_framing097'}
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST097 new focused scopes are missing')


native_delta = shared.native_delta

def native_suites(upstream, driver=None, nav086_source=None):
    driver = HERE.parents[1] if driver is None else driver
    reject_fixture_overrides()
    helper_names = tuple(path[:-3].replace('/', '.') for path in DEPENDENCY_FIXTURES)
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES), *helper_names)))
    modules = {name: importlib.import_module(name) for name in names}
    for name,module in modules.items():
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('fixture import escaped pinned driver: '+name)
        module.CORE = upstream/'LoopCtrlUITests'
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream/'LoopCtrlUITests'
    name = 'tests.test_native_single_gold086'
    if nav086_source is None:
        raise ValueError('current eight-file single-gold086 Nav snapshot is required')
    modules[name].CORE = nav086_source
    alias = sys.modules.get(name.rsplit('.',1)[-1])
    if alias is not None:
        alias.CORE = nav086_source
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in CASES]

def runtime_boundary_identity(driver):
    boundary = importlib.import_module('check_runtime_pause096')
    if Path(boundary.__file__).resolve() != driver/CURRENT_MAC_SOURCES[0]:
        raise ValueError('Runtime checker import escaped pinned driver')
    baseline = git(driver, 'show', RUNTIME_BASELINE+':patches/loopctrl/ngg2/NG2Runtime.swift')
    if boundary.BASELINE_CODE != RUNTIME_BASELINE or sha(baseline) != boundary.BASELINE_RUNTIME_SHA:
        raise ValueError('Runtime096 baseline identity changed')
    new, related = list(boundary.CASES), list(boundary.RELATED_CASES)
    if len(new) != 4 or len(related) != 8 or len(set(new+related)) != 12:
        raise ValueError('Runtime096 callback inventory changed')
    return dict(baseline_code=RUNTIME_BASELINE, baseline_runtime_sha256=sha(baseline),
        new_cases=new, related_cases=related, pass_line=boundary.PASS,
        expected_assertion_red=boundary.RED_ASSERTION,
        scope='Selection metadata only; actual baseline assertion Red and current Runtime Green execute on Mac')


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest = json.loads(pinned_bytes(driver, 'patches/loopctrl/ngg2-manifest.json', code))
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    if len(old) != 36:
        raise ValueError('baseline native inventory is not 36')
    changed = native_delta(old, current, EXPECTED_NATIVE_CHANGES)
    expected_meta = {'api_version':'1.98.16-ngg2', 'client_capability':'necrogold_native_v15',
                     'cycle_capability':'necrogold_native_cycle_v1', 'cycle_profile':'normal-1-1-cycle-v1',
                     'compiler_profile_version':3}
    if any(manifest.get(key) != value for key, value in expected_meta.items()):
        raise ValueError('native API/profile/compiler identity changed')
    if (sealed['api_version'],sealed['client_capability']) != ('1.98.16-ngg2','necrogold_native_v15'):
        raise ValueError('installed native API changed')
    preserved = {}
    paths = list(PRESERVED_REPOSITORY)
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('097')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('097')]
    paths += ['patches/loopctrl/run_test096_host.py', 'patches/loopctrl/test_device_ci096.py']
    paths += [p.decode() for p in git(driver,'ls-tree','-r','--name-only','-z',NATIVE_BASELINE,'legacy/r12').split(b'\0') if p]
    if sum(path.startswith('legacy/r12/') for path in paths) != 40:
        raise ValueError('R12 source inventory changed')
    for path in dict.fromkeys(paths):
        preserved[path] = retained_identity(pinned_bytes(driver,path,code),git(driver,'show',NATIVE_BASELINE+':'+path))
    repository = {}
    for name, spec in manifest['additions'].items():
        digest = addition_identity(driver,name,spec)
        directory = 'tools/ring_native/' if spec.get('source_root') == 'ring_native' else 'patches/loopctrl/ngg2/'
        pinned_bytes(driver,directory+spec['source'],code)
        if current[name] != digest:
            raise ValueError('driver addition differs from installed source: '+name)
        repository[name] = digest
    ring_raw = pinned_bytes(driver,'necroprobe/ring_native_manifest.json',code)
    retained_identity(ring_raw,git(driver,'show',NATIVE_BASELINE+':necroprobe/ring_native_manifest.json'))
    ring = json.loads(ring_raw)
    if len(ring['sources']) != 15:
        raise ValueError('canonical ring source inventory changed')
    for path,digest in ring['sources'].items():
        retained_identity(pinned_bytes(driver,path,code),git(driver,'show',NATIVE_BASELINE+':'+path),digest)
    engine = pinned_bytes(driver,'necroprobe/bin/ring-i386',code)
    if len(engine) != 56088 or len(engine) != ring['binary_bytes'] or sha(engine) != ring['binary_sha256']:
        raise ValueError('canonical engine identity changed')
    retained_identity(engine,git(driver,'show',NATIVE_BASELINE+':necroprobe/bin/ring-i386'))
    for module_name in ('necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097'):
        module = importlib.import_module(module_name)
        if Path(module.__file__).resolve() != driver/(module_name.replace('.','/')+'.py'):
            raise ValueError('client import escaped pinned driver: '+module_name)
    client = importlib.import_module('necroprobe.native_cycle')
    if (client.REVISION,client.API_VERSION,client.CAPABILITY,client.PROFILE) != (
            'native-cycle-v1','1.98.16-ngg2','necrogold_native_cycle_v1','normal-1-1-cycle-v1'):
        raise ValueError('native cycle protocol identity changed')
    fixture_names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES))))
    fixture_paths = [name.replace('.', '/')+'.py' for name in fixture_names]
    fixture_paths += ['tests/test_native_ring094.py', *DEPENDENCY_FIXTURES,
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py',
                      'patches/loopctrl/test_device_ci097.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    current_mac = {path:sha(pinned_bytes(driver,path,code)) for path in CURRENT_MAC_SOURCES}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        current_mac_source_sha256=current_mac,
        runtime_callback_selection=runtime_boundary_identity(driver),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        historical_mac_boundary_proof=dict(code='c12e66667de54ea69180c0b6629cf11e7498a1af',run=43427316593,build=171,
            source_reference=NATIVE_BASELINE,executed_this_run=False,
            limitation='Historical TEST096 metadata only. Runtime/Ring bytes are unchanged but C callees changed; fresh selected Mac boundaries prove only current procedural integration, not phone acceptance.'),
        direct_c_compiler_binding='Selected C fixtures use installed CORE; old086 Nav uses eight exact current sealed files. No Ring classification replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test097-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test097-nav086-current-') as temporary:
        binding=source_identity(driver,before)
        snapshot_root=Path(temporary)/'single-gold086'
        snapshot=nav086_snapshot(upstream,snapshot_root,before['native_source_sha256'])
        suites=native_suites(upstream,driver,nav086_source=snapshot_root)
        selected_cases(case for _,cases in suites for case in cases)
        fixture=importlib.import_module('tests.test_native_controller');cycle=importlib.import_module('tests.test_native_cycle094')
        abi={n:ctypes.sizeof(getattr(fixture,n)) for n in ('Scene','Status','Event','MotionWait','RecoveryStatus')}
        abi['Cycle']=ctypes.sizeof(cycle.Cycle)
        if abi != dict(Scene=23864,Status=192,Event=128,MotionWait=48,RecoveryStatus=456,Cycle=216):
            raise ValueError('native public or companion ABI changed')
        evidence=dict(scope='TEST097 selected candidates, motion and partial continuation repairs',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,device_test='not_run',
            fixture_source_snapshots={'test097-related-single-gold086':snapshot},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'old086 sixth eight-file Controller wrapper: incompatible with current Ring headers; only its first five Nav cases use the current eight-source snapshot',
                     'old095/096 complete host suites and separate Runtime095 four-case executable',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci097')
        run_scope('test097-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection097Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test097-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST097 selected contracts against exact sealed IPA sources; Mac checks are separate and phone acceptance is not run')


if __name__=='__main__':main()
