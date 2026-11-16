"""TEST108 selected real-failure continuation, offer and motion contracts.

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
_spec = importlib.util.spec_from_file_location('test108_shared_source_utils', HERE/'run_test107_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'c83056fe11827e14d8c121f7e012f306ec3f0a87'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c',
    'LoopCtrlUITests/NG2Ring.c','LoopCtrlUITests/NG2Navigation.c'})
# Exact authored methods are frozen; imports are source-bound dependencies only.
CASES = (
    ('tests.test_native_open_full108', 'NativeOpenFull108Tests', 'test108-open-full', frozenset({
        'test_a_second_unknown_does_not_restore_the_one_step_credit',
        'test_direct_opening_full_unknown_waits_for_independent_zero_then_enters_once',
        'test_new_candidate_after_actual_entry_is_held_without_restarting',
        'test_old_unknown_entry_history_does_not_borrow_the_direct_opening_geometry',
        'test_opening_bracket_positive_floor_and_exact_projection_are_required',
        'test_source_prefix_deadline_cancel_and_unknown_input_do_not_gain_new_authority',
        'test_target_candidate_upper_bound_and_strong_word_precede_new_entry',
    }), True),
    ('tests.test_native_full_wait108', 'NativeFullWait108Tests', 'test108-full-wait', frozenset({
        'test_invalid_stage_two_revokes_phase_preparation_and_proof_without_rebinding',
        'test_known_motion_or_changed_door_permanently_refuses_later_anchor_zero',
        'test_material_or_raw_unknown_waits_then_direct_anchor_zero_creates_a_new_current_model',
        'test_new_goods_gold_protection_and_nonfull_scenes_never_become_wait_credit',
        'test_reserved_stage_three_does_not_gain_a_wait_or_resend',
        'test_two_later_zero_frames_cannot_bridge_unknown_from_the_fixed_anchor',
        'test_wait_original_deadline_expires_with_no_further_capture_or_only_prefix_discards',
    }), True),
    ('tests.test_native_revealed_motion108', 'RevealedMotion108Tests', 'test108-revealed-motion', frozenset({
        'test_all73_pixel_phases_reserve_the_single_expected_unit',
        'test_cached_dependency_mask_matches_the_full_domain_without_overrun',
        'test_flat_repeating_noise_and_moving_text_cannot_supply_a_unit',
        'test_missing_old_world_witnesses_cannot_supply_a_unit',
        'test_sparse_revealed_gate_keeps_unit_credit_in_four_directions',
        'test_supported_world_phase_replaces_unavailable_ordinary_comparisons',
        'test_texture_quality_and_bands_reject_with_every_phase_still_qualified',
        'test_ui_pixel_changes_never_supply_world_dependencies',
        'test_world_mask_closes_all_dependencies_outside_ui',
        'test_world_phase_needs_every_finite_margin_and_the_exact_unit',
        'test_world_scores_do_not_turn_missing_flat_or_aliased_pixels_into_margin',
        'test_zero_opposite_and_tween_pixels_do_not_inherit_the_new_gate_unit',
    }), True),
    ('tests.test_native_single_offer108', 'NativeSingleOffer108Tests', 'test108-single-offer', frozenset({
        'test_each_observed_wall_and_opening_is_required_independently',
        'test_existing_closed_identity_proves_only_its_actual_lower_price',
        'test_mapping_unseen_row_cancel_deadline_and_legacy_modes_are_preserved',
        'test_numeric_validator_rejects_forged_or_incomplete_evidence',
        'test_offset_entry_boundary_single_face_and_full_offers_have_normal_negative_proof',
        'test_one_complete_face_is_positive_evidence_and_not_an_arbitrary_blob',
        'test_raw_prices_caps_and_full_target_domain_are_not_optional',
        'test_relative_boundary_supports_other_rows_and_the_mirrored_opening',
        'test_three_lower_floors_caps_exact_projection_and_no_fourth_offer_remain_required',
    }), True),
    ('tests.test_native_single_offer108', 'NativeSingleOfferController108Tests', 'test108-single-offer-controller', frozenset({
        'test_controller_rechecks_observed_boundary_floor_projection_and_forged_certificate',
        'test_existing_closed_price_certificate_is_independently_adopted',
        'test_normal_producer_joins_durable_pause_intent_restart_ack_and_next_floor',
        'test_target_candidate_and_unobserved_price_never_receive_restart_authority',
    }), True),
    ('tests.test_native_split_roof108', 'NativeSplitRoof108Tests', 'test108-split-roof', frozenset({
        'test_dark_mouth_outside_and_inboard_are_not_inferred_or_walked',
        'test_each_independent_wall_is_required_without_accepting_doors_or_hidden_walls',
        'test_every_observed_floor_and_short_route_is_required',
        'test_observed_flanks_outer_cap_and_both_boundaries_support_only_bit0',
        'test_rotated_reflected_transposed_and_shifted_boundaries_are_not_the_same_witness',
        'test_weaker_near_roof_or_single_boundary_does_not_replace_independent_support',
        'test_wrong_state_gold_goods_any_protection_and_items_cannot_gain_authority',
    }), True),
    ('tests.test_native_vantage_replan108', 'NativeVantageReplan108Tests', 'test108-vantage-replan', frozenset({
        'test_cancellation_owner_foreground_phase_and_hud_revoke_permission',
        'test_frozen_original_deadlines_are_not_extended',
        'test_independent_prefix_and_nonoverlap_are_required',
        'test_later_mode3_anchor_cannot_accept_even_a_remote_material_update',
        'test_new_ack_unknown_has_no_resend_or_movement_credit',
        'test_nontransitive_zero_keeps_the_frozen_anchor',
        'test_old_full_decision_progress_once_and_session_count_cannot_be_bypassed',
        'test_only_one_remote_stone_loss_and_positive_route_opening_are_eligible',
        'test_strict_zero_and_started_or_unknown_input_rejections',
        'test_unsent_route_is_retired_then_independent_zero_issues_only_a_new_future_ticket',
    }), True),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test101-full-framing', frozenset({
        'test_candidate_target_upper_bound_or_strong_word_is_held_before_observation_input',
        'test_fresh_partial_after_local_move_is_classified_truthfully_but_never_navigates',
        'test_full_unknown_later_static_fresh_ticket_actual_moved_then_new_candidate',
        'test_later_static_requires_immutable_goods_materials_protection_and_zero',
        'test_new_full_negative_counts_once_and_uses_only_its_new_durable_source',
        'test_new_move_visual_unknown_keeps_bounded_wait_without_full_shortcut_or_resend',
        'test_original_horizon_prefix_cancel_and_input_unknown_never_remint_a_move',
        'test_real_opening_axis_known_floor_protection_and_safe_potential_roi_are_required',
        'test_second_unknown_in_same_level_does_not_restore_framing',
    }), True),
    ('tests.test_native_motion067', 'NativeMotion067Tests', 'test067-motion', frozenset({
        'test_existing_normal_moves_blocks_openings_and_unexpected_are_preserved',
        'test_extra_evidence_requires_exact_closed_gold_bracket',
        'test_extra_evidence_requires_floor_unknown_goods_and_no_protection',
        'test_stationary_reverse_partial_and_two_tiles_are_not_one_move',
        'test_strong_gate_detail_confirms_one_move_with_transient_overlay',
        'test_weak_flat_and_ambiguous_repeating_texture_stays_unknown',
    }), True),
    ('tests.test_native_revealed_gate079', 'NativeRevealedGate079Tests', 'test079-revealed-gate', frozenset({
        'test_all_nine_translations_include_different_anchor_pair_ambiguity',
        'test_only_old_noncollinear_stone_anchors_count_and_other_losses_are_not_evidence',
        'test_public_four_direction_reveal_is_a_unit_then_nav_approaches_without_entry',
        'test_raw_normal_side_unit_gap_and_known_output_boundaries',
        'test_revealed_gate_requires_old_singleton_exact_pair_and_unknown_projections',
        'test_scope_requires_unknown_candidate_unprotected_item_free_observed_endpoints',
        'test_shared_fixed_axis_strength_bands_and_all73_competitor_rules_remain_required',
        'test_stationary_reverse_two_cells_and_partial_pixels_never_become_a_unit',
    }), True),
    ('tests.test_native_revealed_singleton096', 'NativeRevealedSingleton096Tests', 'test096-revealed-singleton', frozenset({
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
    ('tests.test_native_preserved_sparse097', 'NativePreservedSparse097Tests', 'test097-preserved-sparse', frozenset({
        'test_complete_witness_rois_and_observed_endpoints_are_required',
        'test_exact_old_gold_stones_and_unique_projection_are_required',
        'test_finite_rank_and_independent_sparse_axis_planes_are_required',
        'test_four_directions_need_only_the_arrival_floor',
        'test_known_results_and_input_scenes_remain_unchanged',
        'test_old_dirt_support_and_noncollinearity_are_required',
        'test_other_displacements_and_scene_scope_do_not_credit_a_unit',
        'test_public_sparse_known_one_cell_is_not_lost',
    }), True),
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
    ('tests.test_native_closed_offer105', 'NativeClosedOffer105Tests', 'test105-closed-offer', frozenset({
        'test_positive_closed_red_identity_alone_explains_its_unknown_lower_cell',
    }), False),
    ('tests.test_native_split_shadow095', 'NativeSplitShadow095Tests', 'test095-split-shadow', frozenset({
        'test_all_six_dark_cells_remain_unknown_and_are_required',
        'test_both_roof_sides_and_lower_left_wall_need_observed_support',
        'test_fixed_world_mouth_uses_three_actual_floor_steps_then_holds',
        'test_marked_split_roof_adds_only_fixed_upper_left_hypothesis',
        'test_observed_approach_floor_shortest_path_and_all_protections_are_required',
        'test_old_candidates_and_invalid_gold_goods_other_corners_are_preserved',
    }), True),
    ('tests.test_native_occluded_corner097', 'NativeOccludedCorner097Tests', 'test097-occluded-corner', frozenset({
        'test_elbow_requires_each_observed_turn_wall_floor_and_unknown_direct_outside',
        'test_fixed_world_chooser_advances_only_existing_floor_and_holds_before_unknown',
        'test_left_elbow_uses_diagonal_outside_floor_without_inventing_direct_outside_floor',
        'test_old_mouths_shadows_corners_and_unrelated_sides_keep_original_masks',
        'test_scene_central_floor_goods_gold_all_protection_and_abi_guards_are_preserved',
        'test_upper_dark_portal_and_inside_materials_do_not_authorize_walls_doors_or_hidden_floor',
        'test_upper_requires_independent_outer_roof_and_left_boundary_positive_walls',
        'test_upper_shadow_retains_floor_or_unknown_inside_and_mixed_opaque_wall_support',
    }), True),
    ('tests.test_native_observed_mouth104', 'NativeObservedMouth104Tests', 'test104-observed-mouth', frozenset({
        'test_every_independent_wall_and_opposite_roof_support_is_required',
        'test_fixed_mouth_chooser_walks_only_three_observed_floors_then_holds',
        'test_mouth_outside_and_inside_reject_materials_without_relabelling',
        'test_observed_mouth_with_supported_walls_adds_only_upper_bit',
        'test_observed_three_step_vantage_and_protection_are_required',
        'test_old_dark_mouth_floor_rejection_and_other_sides_keep_their_meaning',
        'test_scene_goods_gold_abi_and_invalid_cells_reject',
    }), True),
    ('tests.test_native_left_observation106', 'NativeLeftObservation106Tests', 'test106-left-observation', frozenset({
        'test_dark_left_gap_with_pillar_and_both_boundary_ends_adds_only_bit8',
        'test_each_positive_wall_floor_and_dark_gap_is_independent',
        'test_fixed_world_chooser_uses_only_three_observed_floors_then_holds',
        'test_observed_left_floor_mouth_with_independent_long_wall_adds_only_bit5',
        'test_state_gold_goods_protection_and_other_sides_cannot_gain_authority',
    }), True),
    ('tests.test_native_observation072', 'NativeObservation072Tests', 'test072-observation', frozenset({
        'test_current_floor_refresh_rejects_changed_action_protection_and_old_input_authority',
        'test_current_hud_fifty_ms_preparation_and_original_budgets_remain_required',
        'test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket',
        'test_goods_cancellation_phase_and_owner_guards_preempt_observing_or_issued_refresh',
        'test_independent_floor_proof_and_published_ticket_keep_full_current_permission',
        'test_protected_gold_wall_does_not_block_the_same_observed_entry',
        'test_refresh_limit_is_once_per_verified_progress_and_eight_per_session',
        'test_unknown_goods_observed_vantage_keeps_original_beat_for_irrelevant_drift',
    }), True),
    ('tests.test_native_side_opening098', 'NativeSideOpening098Tests', 'test098-side-opening', frozenset({
        'test_eight_side_turns_retire_old_ticket_and_prepare_new_direction_without_credit',
        'test_fixed_new_anchor_cannot_be_replaced_by_transitive_zero_frames',
        'test_goods_cancel_owner_phase_and_current_hud_revoke_new_permission',
        'test_later_proof_requires_independent_current_prefix_capture',
        'test_new_ack_unknown_remains_unresolved_without_resend',
        'test_original_ticket_and_recovery_horizons_cannot_be_extended',
        'test_trigger_rejects_extra_material_changes_gold_protection_goods_and_unsafe_floor',
        'test_trigger_requires_strict_zero_and_cannot_reuse_started_or_unknown_input',
    }), True),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_full_wait108',
    'tests.test_native_open_full108',
    'tests.test_native_revealed_motion108',
    'tests.test_native_single_offer108',
    'tests.test_native_split_roof108',
    'tests.test_native_vantage_replan108',
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
    'tests.test_native_full_framing101',
    'tests.test_native_full_wait108',
    'tests.test_native_handoff099',
    'tests.test_native_left_observation106',
    'tests.test_native_motion067',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_observed_mouth104',
    'tests.test_native_observed_shop_controller104',
    'tests.test_native_occluded_corner097',
    'tests.test_native_offer_controller105',
    'tests.test_native_offer_coverage104',
    'tests.test_native_open_full108',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial_entry097',
    'tests.test_native_passage072',
    'tests.test_native_passage_navigation072',
    'tests.test_native_perception',
    'tests.test_native_preserved_sparse097',
    'tests.test_native_recovery',
    'tests.test_native_revealed_gate079',
    'tests.test_native_revealed_motion108',
    'tests.test_native_revealed_singleton096',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_shadow_passage094',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_gate081',
    'tests.test_native_side_opening098',
    'tests.test_native_side_shop100',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_split_roof108',
    'tests.test_native_split_shadow095',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_supported_mouth084',
    'tests.test_native_vantage_replan108',
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
PRODUCT_PATHS = ('necroprobe/test108.py','test_108.sh')
LEGACY_FIXTURE_EXCEPTION = None
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,*shared.PRODUCT_PATHS,*PRESERVED_LOCAL_PYTHON,
    'patches/loopctrl/run_test107_host.py','patches/loopctrl/test_device_ci107.py',
    'tools/ring_native/generate_non_target094.py',
    'necroprobe/closed_container_features105.json','tools/ring_native/generate_closed105.py',
    *(name.replace('.', '/')+'.py' for name in shared.CORE_MODULES))
RUNTIME_PROOF_POLICY = 'historical_only_unchanged_runtime'
UNCHANGED_RUNTIME_SHA256 = '42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8'
BASELINE_CONTROLLER_SHA256 = 'fdbc142cb7366c686e16296168a668eb80e432467526817c7d8ce92395e78822'
HISTORICAL_CONTROLLER_SHA256 = '4101c6e4fa06d488aead1bad01b338f30afee328e99d66281c997ad643a8c63e'

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO108_') for name in os.environ):
        raise ValueError('TEST108 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST108 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST108 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST108 new focused scopes are missing')


native_delta = shared.native_delta

def preserved_fixture_identity(path, current, original):
    """Preserve every old byte except a separately approved, source-bound method."""
    exception=LEGACY_FIXTURE_EXCEPTION
    if exception is None or path!=exception['path']:
        return retained_identity(current,original)
    if sha(original)!=exception['baseline_sha256'] or sha(current)!=exception['approved_sha256']:
        raise ValueError('TEST108 unreviewed legacy fixture revision')
    trees=[ast.parse(raw.decode()) for raw in (original,current)]
    classes=[next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==exception['klass']) for tree in trees]
    methods=[[n for n in klass.body if isinstance(n,ast.FunctionDef)] for klass in classes]
    if [n.name for n in methods[0]]!=[n.name for n in methods[1]]:
        raise ValueError('TEST108 legacy method markers changed')
    selected=[next(n for n in group if n.name==exception['method']) for group in methods]
    old,new=selected
    if old.decorator_list or new.decorator_list or ast.dump(old.args)!=ast.dump(new.args):
        raise ValueError('TEST108 legacy method interface changed')
    old_lines,new_lines=[raw.decode().splitlines(keepends=True) for raw in (original,current)]
    if old_lines[:old.lineno-1]!=new_lines[:new.lineno-1] or old_lines[old.end_lineno:]!=new_lines[new.end_lineno:]:
        raise ValueError('TEST108 bytes outside the approved legacy method changed')
    other=[[ast.dump(n,include_attributes=False) for n in group if n.name!=exception['method']] for group in methods]
    if other[0]!=other[1]:
        raise ValueError('TEST108 other legacy methods changed')
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
        raise ValueError('TEST108 historical-only Runtime scope/source identity changed')
    return dict(policy=RUNTIME_PROOF_POLICY,runtime_sha256=UNCHANGED_RUNTIME_SHA256,
        executed_this_run=False,current_controller_execution=False,
        baseline_controller_sha256=BASELINE_CONTROLLER_SHA256,
        historical_controller_sha256=HISTORICAL_CONTROLLER_SHA256,
        current_controller_sha256=current[controller],source_reference=NATIVE_BASELINE,
        historical_mac=dict(code='2c5afa96caa3944dc376ece148d274f913880500',run=43663964487,build=191,
            executed_this_run=False,controller_sha256=HISTORICAL_CONTROLLER_SHA256,
            runtime_sha256=UNCHANGED_RUNTIME_SHA256),
        limitation='Mac191 used old101 Controller4101 with Runtime42f2. Runtime bytes remain unchanged, but this is not fresh TEST108 Controller/Navigation/Runtime execution or game acceptance.')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('108')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('108')]
    paths += ['patches/loopctrl/run_test107_host.py', 'patches/loopctrl/test_device_ci107.py']
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101','necroprobe.test102','necroprobe.test103','necroprobe.test104','necroprobe.test105','necroprobe.test106','necroprobe.test107','necroprobe.test108'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py', 'patches/loopctrl/run_test102_host.py', 'patches/loopctrl/run_test103_host.py', 'patches/loopctrl/run_test104_host.py', 'patches/loopctrl/run_test105_host.py', 'patches/loopctrl/run_test106_host.py', 'patches/loopctrl/run_test107_host.py', 'patches/loopctrl/run_test108_host.py',
                      'patches/loopctrl/test_device_ci108.py']
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
    (output/'test108-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test108-nav086-current-') as temporary:
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
            raise ValueError('TEST108 read-only companion ABI changed')
        evidence=dict(scope='TEST108 selected actual-failure continuation, offer coverage and motion contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'Historical086/091 current eight-source snapshots are created only if an explicit related scope requires them',
                     'old095/096/097/098/099/100/101/102/103/104/105/106/107 complete host suites and Runtime/Mac callbacks; historical Mac191 is not current Controller proof',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci108')
        run_scope('test108-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection108Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test108-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST108 selected native contracts against exact sealed IPA sources; unchanged Runtime proof is historical and phone acceptance is not run')


if __name__=='__main__':main()
