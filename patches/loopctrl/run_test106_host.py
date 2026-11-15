"""TEST106 selected continuation, closed-price and passage contracts.

Current selected native units check software contracts, not phone/game acceptance.
Runtime42f2/Mac191 old-Controller4101 remains historical metadata only.
No current callback, game or iPhone acceptance proof is claimed.
"""
import argparse
import ast
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
_spec = importlib.util.spec_from_file_location('test106_shared_source_utils', HERE/'run_test105_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '4d084b55c43e5e0095662be11e6eb8d3f86427a4'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c',
    'LoopCtrlUITests/NG2Ring.c','LoopCtrlUITests/NG2Navigation.c'})
# Three native sources and exact author inventories are frozen; imports add no test scopes.
CASES = (
    ('tests.test_native_bottom_shop103', 'NativeBottomShop103Tests', 'test103-bottom-shop', frozenset({
        'test_every_fixed_gold_center_floor_item_cap_and_gate_is_required',
        'test_full_strip_target_and_strong_word_remain_held',
        'test_mapping_state_deadline_cancel_and_legacy_modes_keep_old_rules',
        'test_numeric_certificate_rejects_forgery_with_same_old_binary_guards',
        'test_ten_fixed_gold_bottom_entry_and_two_full_faces_have_separate_proof',
        'test_two_complete_faces_not_partial_missing_shifted_or_extra_are_required',
    }), False),
    ('tests.test_native_closed_offer105', 'NativeClosedOffer105Tests', 'test105-closed-offer', frozenset({
        'test_damaged_recolored_or_displaced_closed_structure_is_not_excluded',
        'test_numeric_closed_identity_and_binary_target_domain_are_both_required',
        'test_positive_closed_red_identity_alone_explains_its_unknown_lower_cell',
        'test_target_or_candidate_has_priority_over_closed_identity',
    }), False),
    ('tests.test_native_closed_price106', 'NativeClosedPrice106Tests', 'test106-closed-price', frozenset({
        'test_already_registered_gray_and_purple_closed_bodies_share_the_price_proof',
        'test_each_existing_shop_shape_uses_the_same_closed_price_adapter',
        'test_integer_support_boundaries_are_exact_for_both_masks_and_all_existing_identities',
        'test_observed_closed_price_and_background_variation_have_separate_positive_proof',
        'test_price_complete_unknown_lower_cell_uses_the_same_versioned_identity',
        'test_target_missing_extra_price_and_damaged_closed_identity_are_held',
        'test_version_two_closed_identity_and_actual_price_pose_cannot_be_forged',
    }), True),
    ('tests.test_native_closed_price_controller106', 'NativeClosedPriceController106Tests', 'test106-closed-price-controller', frozenset({
        'test_c_independently_checks_integer_coverage_boundaries_and_lattice_for_every_identity',
        'test_canonical_closed_identities_reach_durable_restart_in_each_offer_slot',
        'test_complete_prices_and_unknown_closed_lower_cell_keep_version_two_identity',
        'test_normal_closed_price_reaches_durable_intent_restart_ack_and_next_floor',
        'test_target_candidate_and_forged_closed_price_never_restart',
    }), True),
    ('tests.test_native_left_observation106', 'NativeLeftObservation106Tests', 'test106-left-observation', frozenset({
        'test_dark_left_gap_with_pillar_and_both_boundary_ends_adds_only_bit8',
        'test_each_positive_wall_floor_and_dark_gap_is_independent',
        'test_fixed_world_chooser_uses_only_three_observed_floors_then_holds',
        'test_observed_left_floor_mouth_with_independent_long_wall_adds_only_bit5',
        'test_state_gold_goods_protection_and_other_sides_cannot_gain_authority',
    }), True),
    ('tests.test_native_lower_fringe100', 'NativeLowerFringe100Tests', 'test100-lower-fringe', frozenset({
        'test_every_positive_wall_and_floor_witness_is_required',
        'test_existing_mouth_corner_and_shadow_masks_are_preserved',
        'test_fixed_world_chooser_uses_four_observed_floor_steps_then_holds_at_wall',
        'test_observed_lower_exterior_floor_retains_only_fixed_left_bit9',
        'test_short_current_floor_vantage_and_disconnected_exterior_are_required',
        'test_state_goods_gold_item_protection_and_fixed_coordinates_keep_scope',
    }), False),
    ('tests.test_native_observed_mouth104', 'NativeObservedMouth104Tests', 'test104-observed-mouth', frozenset({
        'test_every_independent_wall_and_opposite_roof_support_is_required',
        'test_fixed_mouth_chooser_walks_only_three_observed_floors_then_holds',
        'test_mouth_outside_and_inside_reject_materials_without_relabelling',
        'test_observed_mouth_with_supported_walls_adds_only_upper_bit',
        'test_observed_three_step_vantage_and_protection_are_required',
        'test_old_dark_mouth_floor_rejection_and_other_sides_keep_their_meaning',
        'test_scene_goods_gold_abi_and_invalid_cells_reject',
    }), False),
    ('tests.test_native_observed_shop_controller104', 'NativeObservedShopController104Tests', 'test104-offer-controller', frozenset({
        'test_central_nonhud_band_and_cell_mapping_are_independent',
        'test_common_certificate_faces_prices_target_and_source_count_remain_strict',
        'test_normal_policy9_producer_reaches_durable_intent_restart_ack_and_next_floor',
        'test_normal_target_and_incomplete_results_never_acquire_restart_authority',
        'test_observed_items_floor_caps_gold_and_exact_protection_are_all_independent',
        'test_three_observed_floor_cells_under_offers_and_two_full_faces_have_independent_authority',
    }), False),
    ('tests.test_native_occluded_corner097', 'NativeOccludedCorner097Tests', 'test097-occluded-corner', frozenset({
        'test_elbow_requires_each_observed_turn_wall_floor_and_unknown_direct_outside',
        'test_fixed_world_chooser_advances_only_existing_floor_and_holds_before_unknown',
        'test_left_elbow_uses_diagonal_outside_floor_without_inventing_direct_outside_floor',
        'test_old_mouths_shadows_corners_and_unrelated_sides_keep_original_masks',
        'test_scene_central_floor_goods_gold_all_protection_and_abi_guards_are_preserved',
        'test_upper_dark_portal_and_inside_materials_do_not_authorize_walls_doors_or_hidden_floor',
        'test_upper_requires_independent_outer_roof_and_left_boundary_positive_walls',
        'test_upper_shadow_retains_floor_or_unknown_inside_and_mixed_opaque_wall_support',
    }), False),
    ('tests.test_native_offer_controller105', 'NativeOfferController105Tests', 'test105-offer-controller', frozenset({
        'test_c_independently_rejects_shifted_fragment_subminimum_and_counterfeit_absence',
        'test_closed_offer_metrics_ordinary_price_floor_and_target_absence_are_independent',
        'test_normal_closed_offer_reaches_durable_intent_restart_ack_and_new_floor',
        'test_normal_target_candidate_and_unobserved_price_never_restart',
        'test_normal_top_anchored_fragment_reaches_durable_intent_restart_ack_and_new_floor',
    }), False),
    ('tests.test_native_offer_coverage104', 'NativeOfferCoverage104Tests', 'test104-offer-coverage', frozenset({
        'test_all_strip_templates_and_strong_name_keep_target_priority',
        'test_every_positive_support_floor_item_cap_and_gold_context_is_required',
        'test_legacy_wall_mutations_do_not_gain_missing_positive_price_floors',
        'test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards',
        'test_observed_price_floor_footprint_certifies_without_outside_wall_shape',
        'test_raw_caps_prices_extra_groups_and_lower_container_price_remain_observed',
        'test_state_mapping_bounds_deadline_cancel_and_legacy_modes_are_preserved',
        'test_two_real_full_faces_and_no_extra_component_remain_required',
    }), False),
    ('tests.test_native_offer_geometry105', 'NativeOfferGeometry105Tests', 'test105-offer-geometry', frozenset({
        'test_numeric_certificate_requires_same_top_anchor_and_target_absence',
        'test_same_top_observed_fragment_uses_full_face_row_and_preserves_target_priority',
        'test_unanchored_shifted_missing_or_subminimum_fragments_remain_unknown',
    }), False),
    ('tests.test_native_opened_entry093', 'NativeOpenedEntry093Tests', 'test093-opened-entry', frozenset({
        'test_expired_partial_entry_reacquires_independent_future_permission',
        'test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative',
        'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
        'test_original_ticket_windows_epochs_and_actual_begin_boundaries_are_frozen',
        'test_projected_top_goods_growth_and_shrink_use_latest_separate_ticket',
        'test_projection_surface_gold_and_motion_counterexamples_reject_revalidation',
    }), False),
    ('tests.test_native_opened_fade100', 'NativeOpenedFade100Tests', 'test100-opened-fade', frozenset({
        'test_cycle_remote_bracketed_door_to_gold_keeps_fresh_frozen_entry',
        'test_legacy_profile_does_not_gain_remote_door_relabel_permission',
        'test_nearby_material_or_old_gold_item_loss_are_not_remote_permission',
        'test_other_direction_opening_does_not_authorize_this_entry',
        'test_prefix_deadline_and_cancel_do_not_create_new_entry_authority',
        'test_remote_relabel_requires_observed_gold_bracket_and_no_protection',
        'test_remote_relabel_requires_real_same_direction_opening',
    }), False),
    ('tests.test_native_opened_growth106', 'NativeOpenedGrowth106Tests', 'test106-opened-growth', frozenset({
        'test_each_input_axis_uses_observed_adjacent_gold_without_extending_the_window',
        'test_foreign_prefix_expired_window_and_cancellation_never_replace_the_old_ticket',
        'test_missing_opening_neighbor_protection_and_nonzero_motion_do_not_gain_fresh_authority',
        'test_observed_wall_extension_keeps_the_unsent_opened_floor_action_and_original_window',
    }), True),
    ('tests.test_native_partial_refresh104', 'NativePartialRefresh104Tests', 'test104-partial-refresh', frozenset({
        'test_far_floor_to_dirt_rebinds_observe_more_before_fresh_result_and_new_static',
        'test_far_refresh_does_not_consume_or_restore_old_exposed_item_once_allowance',
        'test_left_opening_two_real_left_moves_then_down_uses_current_normal_jobs',
        'test_new_candidate_target_or_unsafe_unknown_holds_and_pending_source_never_refreshes',
        'test_new_far_gold_and_material_refresh_withdraw_credit_and_reserved_ticket',
        'test_refresh_rejects_lost_gold_item_protection_near_material_and_nonzero_motion',
        'test_refresh_requires_fresh_stable_prefix_original_parent_and_control_owner',
        'test_repeated_same_prefix_refresh_keeps_first_parent_and_requires_each_new_result',
    }), False),
    ('tests.test_native_partial_wall_refresh105', 'NativePartialWallRefresh105Tests', 'test105-partial-wall-refresh', frozenset({
        'test_latest_positive_candidate_and_unproved_zero_never_resume_old_move',
        'test_new_protected_wall_withdraws_credit_and_any_definitely_unsent_ticket',
        'test_remote_observed_gold_retires_job_and_waits_for_latest_result_and_independent_zero',
        'test_wall_refresh_rejects_other_protected_changes_and_missing_original_authority',
    }), False),
    ('tests.test_native_shop_coverage102', 'NativeShopCoverage102Tests', 'test102-shop-coverage', frozenset({
        'test_bottom_alignment_selects_one_canonical_row_without_deleting_evidence',
        'test_bottom_door_and_top_prefix_have_independent_complete_proof',
        'test_cancel_deadline_and_legacy_modes_keep_original_authority',
        'test_certificate6_rechecks_every_existing_numeric_and_binary_guard',
        'test_complete_prices_caps_and_extra_boards_are_independent',
        'test_each_twelve_fixed_gold_and_door_is_required_despite_remote_count',
        'test_existing_size_count_thresholds_are_not_lowered',
        'test_mirrors_interior_doors_and_observed_side_openings',
        'test_prefix_faces_preserve_anchor_width_bottom_and_unique_components',
        'test_scene_items_caps_states_and_half_cell_mapping_are_required',
        'test_target_icon_and_strong_word_keep_positive_priority',
        'test_two_independently_complete_rows_are_not_unique_coverage',
    }), False),
    ('tests.test_native_shop_geometry101', 'NativeShopGeometry101Tests', 'test101-shop-geometry', frozenset({
        'test_caps_items_state_and_mapping_keep_original_shadowed_view_unknown',
        'test_complete_pixels_prices_and_unique_faces_are_independent_requirements',
        'test_each_positive_wall_and_opening_is_required_despite_equal_gold_count',
        'test_full_strip_target_and_strong_word_keep_positive_priority',
        'test_numeric_certificate_and_old_policies_remain_distinct',
        'test_observed_twelve_cell_lower_opening_authorizes_only_complete_strip',
    }), False),
    ('tests.test_native_side_shop100', 'NativeSideShop100Tests', 'test100-side-shop', frozenset({
        'test_each_side_support_and_observed_opening_is_required_despite_same_gold_count',
        'test_full_sweep_holds_each_target_template_between_nominal_price_centres',
        'test_isolated_item_edge_is_not_a_price_but_fourth_supported_group_anywhere_is_held',
        'test_item_cap_scene_ties_and_clipped_support_are_held',
        'test_mirror_opening_material_and_source_protection_are_preserved',
        'test_missing_shifted_price_extra_board_item_or_endcap_are_held',
        'test_policy4_numeric_certificate_rejects_forgery_and_old_policy3_stays_distinct',
        'test_seven_observed_side_supports_authorize_complete_target_only_strip',
        'test_target_icon_candidate_and_strong_name_keep_positive_priority',
    }), False),
    ('tests.test_native_single_sign_shop103', 'NativeSingleSignShop103Tests', 'test103-single-sign-shop', frozenset({
        'test_each_fixed_gold_item_cap_and_observed_doorway_is_independent',
        'test_full_face_size_count_roi_and_no_extra_component_remain_required',
        'test_merchant_is_real_strong_bounded_evidence_not_an_optional_field',
        'test_numeric_certificate_rejects_missing_face_fake_merchant_and_old_binary_mutations',
        'test_one_real_full_face_and_strong_merchant_certify_only_complete_strip',
        'test_raw_endcaps_prices_extra_groups_and_missing_items_are_held',
        'test_state_mapping_deadline_cancel_and_legacy_modes_preserve_old_authority',
        'test_target_full_strip_and_strong_name_keep_positive_priority',
    }), False),
    ('tests.test_native_structural_shop096', 'NativeStructuralShop096Tests', 'test096-structural-shop', frozenset({
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
    }), False),
    ('tests.test_native_top_projection106', 'NativeTopProjection106Tests', 'test106-top-projection', frozenset({
        'test_new_target_candidate_and_missing_independent_zero_hold_after_the_new_job',
        'test_new_top_projection_retires_reserved_credit_and_classifies_latest_before_up',
        'test_projection_does_not_restore_the_one_use_exposed_item_allowance',
        'test_projection_requires_the_unchanged_supported_lower_row_and_explained_halo',
    }), True),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_closed_price106',
    'tests.test_native_closed_price_controller106',
    'tests.test_native_left_observation106',
    'tests.test_native_opened_growth106',
    'tests.test_native_top_projection106',
})
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_closed_offer105',
    'tests.test_native_closed_price106',
    'tests.test_native_closed_price_controller106',
    'tests.test_native_controller',
    'tests.test_native_corner_vantage086',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_left_observation106',
    'tests.test_native_lower_fringe100',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_observed_mouth104',
    'tests.test_native_observed_shop_controller104',
    'tests.test_native_occluded_corner097',
    'tests.test_native_offer_controller105',
    'tests.test_native_offer_coverage104',
    'tests.test_native_offer_geometry105',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_opened_growth106',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_refresh104',
    'tests.test_native_partial_wall_refresh105',
    'tests.test_native_passage_navigation072',
    'tests.test_native_perception',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_shadow_passage094',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_solid_corner098',
    'tests.test_native_split_shadow095',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_supported_mouth084',
    'tests.test_native_top_projection106',
    'tests.test_target_assessment087',
)
DEPENDENCY_FIXTURES = ()
PRESERVED_LOCAL_PYTHON = (
    'necroprobe/__init__.py',
    'necroprobe/beat_sync.py',
    'necroprobe/crypto.py',
    'necroprobe/deadlines.py',
    'necroprobe/gold_scan.py',
    'necroprobe/motion_stats.py',
    'necroprobe/native_scan.py',
    'necroprobe/native_walk.py',
    'necroprobe/navigation_stats.py',
    'necroprobe/protocol.py',
    'necroprobe/ring_native.py',
    'necroprobe/rpc_diagnostics.py',
    'necroprobe/shop_navigation.py',
    'necroprobe/target_assessment.py',
    'necroprobe/validation.py',
)
PRODUCT_PATHS = ('necroprobe/test106.py','test_106.sh')
LEGACY_FIXTURE_EXCEPTION = dict(path='tests/test_native_offer_coverage104.py',
    klass='NativeOfferCoverage104Tests',
    method='test_raw_caps_prices_extra_groups_and_lower_container_price_remain_observed',
    baseline_sha256='2f9e38bc3a26905aeb7f148c261c5562ebc78b04c33d5ff2cbe3939250ba8507',
    approved_sha256='9b19a606cdbcfe68f5abbe7bbee90634d50ddcc24f627cab744fcf2b43a151a4')
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,*shared.PRODUCT_PATHS,*PRESERVED_LOCAL_PYTHON,
    'patches/loopctrl/run_test105_host.py','patches/loopctrl/test_device_ci105.py',
    'tools/ring_native/generate_non_target094.py',
    'necroprobe/closed_container_features105.json','tools/ring_native/generate_closed105.py',
    *(name.replace('.', '/')+'.py' for name in shared.CORE_MODULES))
RUNTIME_PROOF_POLICY = 'historical_only_unchanged_runtime'
UNCHANGED_RUNTIME_SHA256 = '42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8'
BASELINE_CONTROLLER_SHA256 = '8167bcc7de3fb6350fa2af6677b148348ed467a47a072d2cfcd3107033188bd9'
HISTORICAL_CONTROLLER_SHA256 = '4101c6e4fa06d488aead1bad01b338f30afee328e99d66281c997ad643a8c63e'

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO106_') for name in os.environ):
        raise ValueError('TEST106 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST106 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST106 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST106 new focused scopes are missing')


native_delta = shared.native_delta

def preserved_fixture_identity(path, current, original):
    """Only the reviewed complete-price/v2 assertion replaces one old method."""
    exception=LEGACY_FIXTURE_EXCEPTION
    if path!=exception['path']:
        return retained_identity(current,original)
    if sha(original)!=exception['baseline_sha256'] or sha(current)!=exception['approved_sha256']:
        raise ValueError('TEST106 unreviewed legacy fixture revision')
    trees=[ast.parse(raw.decode()) for raw in (original,current)]
    classes=[next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==exception['klass']) for tree in trees]
    methods=[[n for n in klass.body if isinstance(n,ast.FunctionDef)] for klass in classes]
    if [n.name for n in methods[0]]!=[n.name for n in methods[1]]:
        raise ValueError('TEST106 legacy method markers changed')
    selected=[next(n for n in group if n.name==exception['method']) for group in methods]
    old,new=selected
    if old.decorator_list or new.decorator_list or ast.dump(old.args)!=ast.dump(new.args):
        raise ValueError('TEST106 legacy method interface changed')
    old_lines,new_lines=[raw.decode().splitlines(keepends=True) for raw in (original,current)]
    if old_lines[:old.lineno-1]!=new_lines[:new.lineno-1] or old_lines[old.end_lineno:]!=new_lines[new.end_lineno:]:
        raise ValueError('TEST106 bytes outside the approved legacy method changed')
    other=[[ast.dump(n,include_attributes=False) for n in group if n.name!=exception['method']] for group in methods]
    if other[0]!=other[1]:
        raise ValueError('TEST106 other legacy methods changed')
    return sha(current)

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
    for name in ('tests.test_native_single_gold086', 'tests.test_native_terrain_axis091'):
        if name in modules:
            if nav086_source is None:
                raise ValueError('current eight-file Nav snapshot is required for '+name)
            modules[name].CORE = nav086_source
            alias = sys.modules.get(name.rsplit('.',1)[-1])
            if alias is not None:
                alias.CORE = nav086_source
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in CASES]

def runtime_history_identity(before,current):
    runtime='LoopCtrlUITests/NG2Runtime.swift';controller='LoopCtrlUITests/NG2Controller.c'
    current_controller=current.get(controller)
    if (before.get(runtime)!=UNCHANGED_RUNTIME_SHA256 or current.get(runtime)!=UNCHANGED_RUNTIME_SHA256
            or before.get(controller)!=BASELINE_CONTROLLER_SHA256
            or not isinstance(current_controller,str) or len(current_controller)!=64
            or any(char not in '0123456789abcdef' for char in current_controller)
            or current_controller in (BASELINE_CONTROLLER_SHA256,HISTORICAL_CONTROLLER_SHA256)):
        raise ValueError('TEST106 historical-only Runtime scope/source identity changed')
    return dict(policy=RUNTIME_PROOF_POLICY,runtime_sha256=UNCHANGED_RUNTIME_SHA256,
        executed_this_run=False,current_controller_execution=False,
        baseline_controller_sha256=BASELINE_CONTROLLER_SHA256,
        historical_controller_sha256=HISTORICAL_CONTROLLER_SHA256,
        current_controller_sha256=current[controller],source_reference=NATIVE_BASELINE,
        historical_mac=dict(code='2c5afa96caa3944dc376ece148d274f913880500',run=43663964487,build=191,
            executed_this_run=False,controller_sha256=HISTORICAL_CONTROLLER_SHA256,
            runtime_sha256=UNCHANGED_RUNTIME_SHA256),
        limitation='Mac191 used old101 Controller4101 with Runtime42f2. Runtime bytes remain unchanged, but this is not fresh TEST106 Controller/Navigation/Runtime execution or game acceptance.')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('106')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('106')]
    paths += ['patches/loopctrl/run_test105_host.py', 'patches/loopctrl/test_device_ci105.py']
    paths += [p.decode() for p in git(driver,'ls-tree','-r','--name-only','-z',NATIVE_BASELINE,'legacy/r12').split(b'\0') if p]
    if sum(path.startswith('legacy/r12/') for path in paths) != 40:
        raise ValueError('R12 source inventory changed')
    for path in dict.fromkeys(paths):
        preserved[path] = preserved_fixture_identity(path,pinned_bytes(driver,path,code),git(driver,'show',NATIVE_BASELINE+':'+path))
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101','necroprobe.test102','necroprobe.test103','necroprobe.test104','necroprobe.test105','necroprobe.test106'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py', 'patches/loopctrl/run_test102_host.py', 'patches/loopctrl/run_test103_host.py', 'patches/loopctrl/run_test104_host.py', 'patches/loopctrl/run_test105_host.py', 'patches/loopctrl/run_test106_host.py',
                      'patches/loopctrl/test_device_ci106.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        runtime_proof_policy=runtime_history_identity(old,current),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        legacy_fixture_exception=LEGACY_FIXTURE_EXCEPTION,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        direct_c_compiler_binding='Finalized selected fixtures compile exact source bound to the installed native seal. Compilation scope is frozen with the authored CASES; no original-image Ring replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test106-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test106-nav086-current-') as temporary:
        binding=source_identity(driver,before)
        snapshot_root=Path(temporary)/'single-gold086'
        snapshot=None
        if any(row[0] in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091') for row in CASES):
            snapshot=nav086_snapshot(upstream,snapshot_root,before['native_source_sha256'])
        suites=native_suites(upstream,driver,nav086_source=snapshot_root)
        selected_cases(case for _,cases in suites for case in cases)
        fixture=importlib.import_module('tests.test_native_controller');cycle=importlib.import_module('tests.test_native_cycle094')
        abi={n:ctypes.sizeof(getattr(fixture,n)) for n in ('Scene','Status','Event','MotionWait','RecoveryStatus')}
        abi['Cycle']=ctypes.sizeof(cycle.Cycle)
        if abi != dict(Scene=23864,Status=192,Event=128,MotionWait=48,RecoveryStatus=456,Cycle=216):
            raise ValueError('native public or companion ABI changed')
        stop=importlib.import_module('tests.test_native_stop099')
        handoff=importlib.import_module('tests.test_native_handoff099')
        companion_abi=dict(StopDetail=ctypes.sizeof(stop.StopDetail),Handoff=ctypes.sizeof(handoff.Handoff))
        if companion_abi != dict(StopDetail=120,Handoff=64):
            raise ValueError('TEST106 read-only companion ABI changed')
        evidence=dict(scope='TEST106 selected stationary protected-wall refresh and target coverage contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'Historical086/091 current eight-source snapshots are created only if an explicit related scope requires them',
                     'old095/096/097/098/099/100/101/102 complete host suites and Runtime/Mac callbacks; historical Mac191 is not current Controller proof',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci106')
        run_scope('test106-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection106Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test106-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST106 selected native contracts against exact sealed IPA sources; unchanged Runtime proof is historical and phone acceptance is not run')


if __name__=='__main__':main()
