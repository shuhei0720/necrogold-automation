"""TEST096 selected motion, structural shop and cycle contracts.

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
import unittest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test096_shared_source_utils', HERE/'run_test095_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'c071f41d4a38b4b513d342ea3f3c68f5db8ec067'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
                                    'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Runtime.swift'})
CASES = (
    ('tests.test_native_revealed_singleton096', 'NativeRevealedSingleton096Tests', 'test096-revealed-singleton',
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
    ('tests.test_native_structural_shop096', 'NativeStructuralShop096Tests', 'test096-structural-shop',
     frozenset({
         'test_certificate3_retains_all_numeric_identity_and_coverage_guards',
         'test_complete_board_roi_and_scene_support_must_fit_observed_bounds',
         'test_complete_structure_authorizes_without_shop_or_merchant_pixel_identity',
         'test_each_required_gold_cell_and_opening_must_be_observed',
         'test_half_cell_ties_are_rejected_on_both_signed_axes',
         'test_items_caps_scene_state_and_positive_gold_are_independent_requirements',
         'test_legacy_modes_and_policy2_fallback_keep_their_existing_authority',
         'test_mirrored_openings_and_projected_protection_are_preserved',
         'test_partial_body_missing_price_extra_board_and_absent_item_are_held',
         'test_target_between_prices_and_observed_name_veto_are_never_masked',
         'test_unmatched_items_is_preserved_diagnostic_only_under_policy3',
         'test_wider_extra_observed_sign_is_not_discarded_by_selected_face_roi',
     }), True),
    ('tests.test_native_structural_cycle096', 'NativeStructuralCycle096Tests', 'test096-structural-cycle',
     frozenset({
         'test_complete_structural_source_and_generic_bounds_reach_existing_durable_restart',
         'test_nearest_grid_mapping_is_symmetric_and_exact_half_cells_are_ambiguous',
         'test_opening_must_be_observed_floor_or_door_and_unseen_corner_is_not_filled',
         'test_raw_residual_is_bounded_diagnostic_only_for_policy3',
         'test_source_gold_positions_and_offer_cells_are_recomputed_not_inferred_from_count',
         'test_structural_numeric_certificate_still_requires_all_bounds_faces_and_observed_goods',
         'test_target_candidate_or_strong_word_in_any_original_cell_remains_a_veto',
     }), True),
    ('tests.test_native_revealed_gate079', 'NativeRevealedGate079Tests', 'test096-related-gate079',
     frozenset({
         'test_all_nine_translations_include_different_anchor_pair_ambiguity',
         'test_only_old_noncollinear_stone_anchors_count_and_other_losses_are_not_evidence',
         'test_public_four_direction_reveal_is_a_unit_then_nav_approaches_without_entry',
         'test_raw_normal_side_unit_gap_and_known_output_boundaries',
         'test_revealed_gate_requires_old_singleton_exact_pair_and_unknown_projections',
         'test_scope_requires_unknown_candidate_unprotected_item_free_observed_endpoints',
         'test_shared_fixed_axis_strength_bands_and_all73_competitor_rules_remain_required',
         'test_stationary_reverse_two_cells_and_partial_pixels_never_become_a_unit',
     }), True),
    ('tests.test_native_side_gate081', 'NativeSideGate081Tests', 'test096-related-gate081',
     frozenset({
         'test_fixed_axis_strong_52_bands_95_percent_and_all73_15pp_competitor_rules',
         'test_known_phase_requires_same_unit_all_dependencies_bands_finite_scores_and_exact_limits',
         'test_new_gate_requires_unknown_or_dirt_projections_and_orthogonal_two_cell_geometry',
         'test_old_noncollinear_stones_and_all_nine_translations_reject_different_pair_ambiguity',
         'test_public_four_direction_side_gate_unit_keeps_next_navigation_unentered',
         'test_raw_high_finite_unit_gap_all73_and_known_primary_outputs_are_preserved',
         'test_scope_requires_floor_candidate_unknown_goods_no_items_protection_and_old_endpoints',
         'test_stationary_reverse_two_cells_eight_and_half_pixels_never_receive_unit_credit',
     }), True),
    ('tests.test_native_cycle_client095', 'CycleClient095Tests', 'test096-related-client',
     frozenset({
         'test_095_launcher_uses_separate_spool_and_truthful_not_started_message',
         'test_095_zip_prefix_filename_receipt_and_all_registered_bytes',
         'test_existing_094_and_generic_spools_preserve_original_zip_label',
     }), True),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test096-related-cycle',
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
    ('tests.test_native_ring_bank094', 'NativeRingBank094Tests', 'test096-related-bank',
     frozenset({
         'test_broken_frame_wrong_spacing_or_clipped_board_cannot_complete_coverage',
         'test_complete_container_shop_certifies_exposed_scope_without_judging_contents',
         'test_complete_coverage_certificate_joins_the_selected_row',
         'test_confirmed_closed_containers_are_distinct_ignored_evidence',
         'test_different_known_ring_requires_its_own_name_and_does_not_prove_target',
         'test_different_merchant_colours_and_hud_overlap_do_not_authenticate_layout',
         'test_extra_authenticated_shop_board_blocks_complete_coverage',
         'test_gold_continuation_outside_board_roi_is_not_a_closed_frame',
         'test_gold_frame_defines_the_board_when_lower_yellow_pixels_are_gold',
         'test_known_bank_identities_require_independent_same_slot_names_and_icons',
         'test_local_disconnected_foreground_23_is_allowed_and_24_is_held',
         'test_long_product_name_occluding_a_board_edge_keeps_coverage_incomplete',
         'test_missing_or_wrong_slot_name_uncatalogued_object_and_unseen_end_hold',
         'test_nameless_blob_or_damaged_container_shape_is_not_ignored',
         'test_off_row_partial_target_or_candidate_vetoes_complete_main_shop',
         'test_separated_small_foreground_specks_do_not_create_a_fourth_item',
         'test_target_template_and_ringlike_icon_keep_target_or_candidate',
         'test_torch_word_inside_a_longer_name_cannot_identify_the_torch',
         'test_two_complete_named_shop_sets_are_negative',
         'test_two_matching_bank_ids_are_unknown_instead_of_first_id_winning',
     }), True),
    ('tests.test_native_singleton_stationary095', 'NativeSingletonStationary095Tests', 'test096-related-singleton',
     frozenset({
         'test_all_raw_scores_are_finite_zero_ranked_and_inside_fallback_domain',
         'test_blur_zero_absolute_bound_and_all_seventy_two_finite_competitors',
         'test_common_noncollinear_dirt_support_and_unique_nine_placements_are_required',
         'test_exact_old_singleton_is_preserved_and_new_stone_cannot_replace_it',
         'test_full_source_and_projected_hud_sample_rois_are_excluded',
         'test_near_floor_all_protection_gold_goods_invalid_scenes_and_direction_reject',
         'test_single_old_stone_fixed_surface_adds_only_readonly_zero_evidence',
         'test_world_axis_strength_regions_and_last_competitor_lead_boundaries',
     }), True),
    ('tests.test_native_cycle_binary095', 'NativeCycleBinary095Tests', 'test096-related-cycle-binary',
     frozenset({
         'test_all_five_maxima_require_finite_equal_conservative_bounds_below_candidate',
         'test_complete_generic_five_cell_bounds_reach_only_the_existing_durable_restart',
         'test_generic_domain_and_representative_pose_have_exact_finite_geometry',
         'test_missing_cell_partial_source_failure_or_layout_uncertainty_stays_held',
         'test_target_candidate_or_strong_word_anywhere_vetoes_binary_absence',
     }), True),
    ('tests.test_native_target_only095', 'TargetOnly095Tests', 'test096-related-target-only',
     frozenset({
         'test_clipped_or_partial_goods_missing_price_and_extra_object_hold',
         'test_complete_uncatalogued_icons_and_missing_names_are_binary_negative',
         'test_dense_primary_covers_all_template_edge_and_gap_poses',
         'test_every_cell_upper_bound_and_structural_field_is_checked',
         'test_failure_cancel_alpha_and_legacy_modes_keep_their_distinct_semantics',
         'test_full_strip_hud_overlap_cannot_be_a_complete_negative',
         'test_lower_iou_qualified_name_is_not_hidden_by_higher_iou_low_coverage',
         'test_original_partial_qualified_word_survives_its_higher_iou_decoy',
         'test_original_partial_strong_word_is_preserved_before_five_cell_replacement',
         'test_policy2_certificate_accepts_catalog_free_complete_sweep',
         'test_same_probe_target_icon_candidate_and_observed_word_only_veto',
         'test_shop_glyph_and_merchant_are_independent_layout_requirements',
         'test_target_between_prices_is_covered_without_slot_identity',
     }), True),
    ('tests.test_native_partial_continuation095', 'NativePartialContinuation095Tests', 'test096-related-partial',
     frozenset({
         'test_only_remote_unprotected_dirt_to_floor_or_unknown_is_admitted',
         'test_remote_change_cannot_clear_candidate_or_started_unknown',
         'test_remote_change_requires_strict_zero_prefix_stability_and_original_deadline',
         'test_remote_dirt_clearance_after_new_ticket_keeps_its_frozen_qualified_input',
         'test_remote_dirt_clearance_in_first_post_assessment_frame_keeps_new_observation_credit',
     }), True),
)

CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_navigation',
                'tests.test_native_perception', 'tests.test_native_motion067',
                'tests.test_native_blocked067', 'tests.test_native_side_gate081',
                'tests.test_native_ring094', 'tests.test_native_cycle_client094',
                'tests.test_native_beat', 'tests.test_native_recovery',
                'tests.test_native_passage072', 'tests.test_native_passage_unsent076',
                'tests.test_native_stationary_texture085')
DEPENDENCY_FIXTURES = shared.DEPENDENCY_FIXTURES
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,
    'necroprobe/cycle_publication.py', 'necroprobe/test094.py', 'necroprobe/test095.py', 'test_095.sh',
    'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/test_device_ci094.py',
    'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/test_device_ci095.py',
    'patches/loopctrl/check_runtime_target_only095.py', 'patches/loopctrl/ngg2_target_only_runtime_tests.swift')
PRODUCT_PATHS = ('necroprobe/test096.py', 'test_096.sh')
CURRENT_MAC_SOURCES = ('patches/loopctrl/check_runtime_pause096.py',
                       'patches/loopctrl/ngg2_pause_adoption096_tests.swift')


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO096_') for name in os.environ):
        raise ValueError('TEST096 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST096 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST096 scope is empty or duplicated')
    required = {'tests.test_native_revealed_singleton096', 'tests.test_native_structural_shop096',
                'tests.test_native_structural_cycle096'}
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST096 new focused scopes are missing')


native_delta = shared.native_delta


def native_suites(upstream, driver=None):
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
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in CASES]


def runtime_boundary_identity(driver):
    boundary = importlib.import_module('check_runtime_pause096')
    if Path(boundary.__file__).resolve() != driver/CURRENT_MAC_SOURCES[0]:
        raise ValueError('Runtime checker import escaped pinned driver')
    baseline = git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2/NG2Runtime.swift')
    if boundary.BASELINE_CODE != NATIVE_BASELINE or sha(baseline) != boundary.BASELINE_RUNTIME_SHA:
        raise ValueError('Runtime096 baseline identity changed')
    new, related = list(boundary.CASES), list(boundary.RELATED_CASES)
    if len(new) != 4 or len(related) != 8 or len(set(new+related)) != 12:
        raise ValueError('Runtime096 callback inventory changed')
    return dict(baseline_code=NATIVE_BASELINE, baseline_runtime_sha256=sha(baseline),
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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('096')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('096')]
    paths += ['patches/loopctrl/run_test095_host.py', 'patches/loopctrl/test_device_ci095.py']
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
    for module_name in ('necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py',
                      'patches/loopctrl/test_device_ci096.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    current_mac = {path:sha(pinned_bytes(driver,path,code)) for path in CURRENT_MAC_SOURCES}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        current_mac_source_sha256=current_mac,
        runtime_callback_selection=runtime_boundary_identity(driver),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        historical_mac_boundary_proof=dict(code='288e1e7a470a7ac34e90813a763725c51408b07b',run=43409363287,build=168,
            source_reference=NATIVE_BASELINE,executed_this_run=False,
            limitation='Historical TEST095 metadata only. Current TEST096 changes Runtime and C callees; fresh selected Mac boundaries are required. No phone acceptance.'),
        direct_c_compiler_binding='Fixtures use the installed CORE or hash-identical pinned driver Ring/canonical sources; only bounded current native Ring cases are classified')

def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test096-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    binding=source_identity(driver,before)
    suites=native_suites(upstream,driver)
    selected_cases(case for _,cases in suites for case in cases)
    fixture=importlib.import_module('tests.test_native_controller');cycle=importlib.import_module('tests.test_native_cycle094')
    abi={n:ctypes.sizeof(getattr(fixture,n)) for n in ('Scene','Status','Event','MotionWait','RecoveryStatus')}
    abi['Cycle']=ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864,Status=192,Event=128,MotionWait=48,RecoveryStatus=456,Cycle=216):
        raise ValueError('native public or companion ABI changed')
    evidence=dict(scope='TEST096 selected motion, structural shop and cycle repairs',source_identity=before,
        production_source_binding=binding,abi_bytes=abi,device_test='not_run',
        not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                 'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                 'old095 complete host205 scope and separate Runtime095 four-case executable',
                 'iPhone reach rate, rare-target precision and human speed acceptance'])
    for label,cases in suites:run_scope(label,cases,output,evidence)
    selector=importlib.import_module('test_device_ci096')
    run_scope('test096-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection096Tests),output,evidence)
    if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
        raise ValueError('selected tests changed sealed source')
    reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
    evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
    (output/'test096-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST096 selected contracts against exact sealed IPA sources; Mac checks are separate and phone acceptance is not run')


if __name__=='__main__':main()
