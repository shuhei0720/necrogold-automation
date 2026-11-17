"""TEST111 source-bound selected contracts. No device traffic or phone acceptance.

Authored native/method and four focused Mac boundary scopes are closed;
historical Runtime110 fault cases are not selected.
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
_spec = importlib.util.spec_from_file_location('test111_shared_source_utils', HERE/'run_test110_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'd169d5bbdb4c73b01e6764f8d6a628766da7684c'
SCOPE_FINALIZED = True  # Final authored new44 and directly related method inventories.
EXPECTED_NATIVE_CHANGES = frozenset({
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Ring.c',
    'LoopCtrlUITests/NG2Ring.h', 'LoopCtrlKit/RPCMethod.swift',
})
EXPECTED_NATIVE_ADDITIONS = frozenset()
CASES = (
    ('tests.test_native_goods111', 'NativeGoods111Tests', 'test111-NativeGoods111Tests', frozenset({
        'test_cancellation_or_deadline_during_independent_fallback_is_not_unknown_success',
        'test_each_raw_price_cap_extra_board_and_extra_object_remains_a_hold',
        'test_exact_projection_and_lower_price_floors_are_required',
        'test_first_incomplete_proof_is_kept_when_no_independent_proof_completes',
        'test_incomplete_earlier_side_does_not_hide_independent_complete_footprint',
        'test_observed_high_side_opening_certifies_full_three_offer_strip',
        'test_target_and_candidate_priority_and_failed_jobs_are_preserved',
        'test_upper_entire_strip_preserves_each_target_between_nominal_prices',
        'test_upper_numeric_certificate_rejects_forged_fields',
        'test_upper_opening_is_mirrored_and_keeps_each_support',
    }), True),
    ('tests.test_native_image_price111', 'NativeImagePrice111Tests', 'test111-NativeImagePrice111Tests', frozenset({
        'test_ambiguous_image_remains_candidate_despite_valid_price',
        'test_canonical_mode0_still_requires_the_target_name',
        'test_clipped_scattered_or_insufficient_own_price_keeps_candidate',
        'test_old_name_positive_survives_missing_price',
        'test_price_value_is_not_fixed_to_one_calibration_number',
        'test_same_image_without_its_price_is_retained_as_candidate',
        'test_strong_target_image_and_observed_price_needs_no_target_name',
    }), True),
    ('tests.test_native_upper_adoption111', 'NativeUpperAdoption111Tests', 'test111-NativeUpperAdoption111Tests', frozenset({
        'test_controller_rechecks_every_upper_wall_and_exact_offer_projection',
        'test_controller_rejects_forged_upper_numeric_faces_prices_and_binary_absence',
        'test_normal_upper_producer_requires_durable_pause_intent_and_real_restart_outcome',
    }), True),
    ('tests.test_native_target_only095', 'TargetOnly095Tests', 'test111-TargetOnly095Tests', frozenset({
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
    ('tests.test_native_structural_shop096', 'NativeStructuralShop096Tests', 'test111-NativeStructuralShop096Tests', frozenset({
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
    ('tests.test_native_side_shop100', 'NativeSideShop100Tests', 'test111-NativeSideShop100Tests', frozenset({
        'test_each_side_support_and_observed_opening_is_required_despite_same_gold_count',
        'test_full_sweep_holds_each_target_template_between_nominal_price_centres',
        'test_isolated_item_edge_is_not_a_price_but_fourth_supported_group_anywhere_is_held',
        'test_item_cap_scene_ties_and_clipped_support_are_held',
        'test_mirror_opening_material_and_source_protection_are_preserved',
        'test_missing_shifted_price_extra_board_item_or_endcap_are_held',
        'test_policy4_numeric_certificate_rejects_forgery_and_old_policy3_stays_distinct',
        'test_seven_observed_side_supports_authorize_complete_target_only_strip',
        'test_target_icon_candidate_and_strong_name_keep_positive_priority',
    }), True),
    ('tests.test_native_shop_geometry101', 'NativeShopGeometry101Tests', 'test111-NativeShopGeometry101Tests', frozenset({
        'test_caps_items_state_and_mapping_keep_original_shadowed_view_unknown',
        'test_complete_pixels_prices_and_unique_faces_are_independent_requirements',
        'test_each_positive_wall_and_opening_is_required_despite_equal_gold_count',
        'test_full_strip_target_and_strong_word_keep_positive_priority',
        'test_numeric_certificate_and_old_policies_remain_distinct',
        'test_observed_twelve_cell_lower_opening_authorizes_only_complete_strip',
    }), True),
    ('tests.test_native_shop_coverage102', 'NativeShopCoverage102Tests', 'test111-NativeShopCoverage102Tests', frozenset({
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
    }), True),
    ('tests.test_native_single_sign_shop103', 'NativeSingleSignShop103Tests', 'test111-NativeSingleSignShop103Tests', frozenset({
        'test_each_fixed_gold_item_cap_and_observed_doorway_is_independent',
        'test_full_face_size_count_roi_and_no_extra_component_remain_required',
        'test_merchant_is_real_strong_bounded_evidence_not_an_optional_field',
        'test_numeric_certificate_rejects_missing_face_fake_merchant_and_old_binary_mutations',
        'test_one_real_full_face_and_strong_merchant_certify_only_complete_strip',
        'test_raw_endcaps_prices_extra_groups_and_missing_items_are_held',
        'test_state_mapping_deadline_cancel_and_legacy_modes_preserve_old_authority',
        'test_target_full_strip_and_strong_name_keep_positive_priority',
    }), True),
    ('tests.test_native_bottom_shop103', 'NativeBottomShop103Tests', 'test111-NativeBottomShop103Tests', frozenset({
        'test_every_fixed_gold_center_floor_item_cap_and_gate_is_required',
        'test_full_strip_target_and_strong_word_remain_held',
        'test_mapping_state_deadline_cancel_and_legacy_modes_keep_old_rules',
        'test_numeric_certificate_rejects_forgery_with_same_old_binary_guards',
        'test_ten_fixed_gold_bottom_entry_and_two_full_faces_have_separate_proof',
        'test_two_complete_faces_not_partial_missing_shifted_or_extra_are_required',
    }), True),
    ('tests.test_native_offer_coverage104', 'NativeOfferCoverage104Tests', 'test111-NativeOfferCoverage104Tests', frozenset({
        'test_all_strip_templates_and_strong_name_keep_target_priority',
        'test_every_positive_support_floor_item_cap_and_gold_context_is_required',
        'test_legacy_wall_mutations_do_not_gain_missing_positive_price_floors',
        'test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards',
        'test_observed_price_floor_footprint_certifies_without_outside_wall_shape',
        'test_raw_caps_prices_extra_groups_and_lower_container_price_remain_observed',
        'test_state_mapping_bounds_deadline_cancel_and_legacy_modes_are_preserved',
        'test_two_real_full_faces_and_no_extra_component_remain_required',
    }), True),
    ('tests.test_native_side_opening098', 'NativeSideOpening098Tests', 'test111-NativeSideOpening098Tests', frozenset({
        'test_eight_side_turns_retire_old_ticket_and_prepare_new_direction_without_credit',
        'test_fixed_new_anchor_cannot_be_replaced_by_transitive_zero_frames',
        'test_goods_cancel_owner_phase_and_current_hud_revoke_new_permission',
        'test_later_proof_requires_independent_current_prefix_capture',
        'test_new_ack_unknown_remains_unresolved_without_resend',
        'test_original_ticket_and_recovery_horizons_cannot_be_extended',
        'test_trigger_rejects_extra_material_changes_gold_protection_goods_and_unsafe_floor',
        'test_trigger_requires_strict_zero_and_cannot_reuse_started_or_unknown_input',
    }), True),
    ('tests.test_native_vantage_replan108', 'NativeVantageReplan108Tests', 'test111-NativeVantageReplan108Tests', frozenset({
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
    ('tests.test_native_observation072', 'NativeObservation072Tests', 'test111-NativeObservation072Tests', frozenset({
        'test_current_floor_refresh_rejects_changed_action_protection_and_old_input_authority',
        'test_current_hud_fifty_ms_preparation_and_original_budgets_remain_required',
        'test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket',
        'test_goods_cancellation_phase_and_owner_guards_preempt_observing_or_issued_refresh',
        'test_independent_floor_proof_and_published_ticket_keep_full_current_permission',
        'test_protected_gold_wall_does_not_block_the_same_observed_entry',
        'test_refresh_limit_is_once_per_verified_progress_and_eight_per_session',
        'test_unknown_goods_observed_vantage_keeps_original_beat_for_irrelevant_drift',
    }), True),
    ('tests.test_native_dirt_ticket079', 'NativeDirtTicket079Tests', 'test111-NativeDirtTicket079Tests', frozenset({
        'test_closed_gate_unit_target_unknown_goods_and_verified_lead_are_required',
        'test_goods_cancel_owner_and_started_or_unknown_input_never_gain_another_send',
        'test_local_gold_protected_material_item_and_nonpalette_changes_are_rejected',
        'test_original_actual_deadline_and_stable_current_prefix_are_kept',
        'test_unknown_tween_or_nonzero_motion_cannot_preserve_dig_authority',
        'test_verified_four_direction_dig_keeps_ticket_then_counts_only_terrain_opening',
    }), True),
    ('tests.test_native_unsent_continuous', 'NativeUnsentContinuousTests', 'test111-NativeUnsentContinuousTests', frozenset({
        'test_complete_zero_late_retires_known_unsent_ticket_and_restarts_from_verified_pose',
        'test_direct_begin_and_tick_late_share_definite_unsent_retirement',
        'test_expired_old_callbacks_cannot_advance_recovery_state_or_clock',
        'test_in_time_complete_zero_does_not_recover_and_deadline_equality_can_begin',
        'test_live_authority_failures_prioritize_cancellation_over_recovery',
        'test_new_slot_is_future_and_prepared_without_extra_input',
        'test_only_new_verified_motion_can_start_new_recovery_budget',
        'test_proof_budget_uses_actual_commit_and_global_budgets_do_not_reopen',
        'test_proof_twelve_second_equality_and_late_stop_without_new_episode',
        'test_repeated_unsent_recovery_keeps_original_episode_and_deadline',
        'test_same_and_fresh_reissues_retire_without_mutating_old_fields',
        'test_started_ack_unknown_cancel_and_goods_never_use_unsent_recovery',
    }), True),
    ('tests.test_native_device065', 'NativeDevice065Tests', 'test111-NativeDevice065Tests', frozenset({
        'test_pending_expiry_cannot_reopen_sync_walk_or_session_budget',
        'test_pending_expiry_retains_authority_goods_and_latest_visual_guards',
        'test_pending_old_callbacks_and_backdated_clocks_cannot_trigger_recovery',
        'test_pending_original_deadline_equality_still_reissues_only_the_same_beat',
        'test_pending_same_and_fresh_expiry_reacquire_without_rewriting_retired_ticket',
        'test_repeated_pending_expiry_preserves_verified_progress_budget_and_episode',
    }), True),
    ('tests.test_native_unissued111', 'NativeCompositeUnissued111Tests', 'test111-NativeCompositeUnissued111Tests', frozenset({
        'test_composite_admission_rejects_other_material_changes_and_protected_or_goods',
        'test_composite_independent_current_prefix_proof',
        'test_composite_later_proof_preserves_all_tiles_of_the_fixed_new_anchor',
        'test_composite_new_ack_unknown_never_resends',
        'test_composite_original_ticket_and_parent_deadlines',
        'test_composite_side_opening_retires_without_credit_then_requires_independent_fixed_goal',
        'test_composite_strict_zero_and_started_unknown_input',
    }), True),
    ('tests.test_native_unissued111', 'NativeRemoteLate111Tests', 'test111-NativeRemoteLate111Tests', frozenset({
        'test_remote_palette_late_zero_retires_old_window_and_obtains_new_prepared_id',
        'test_remote_palette_preserves_local_protection_gold_full_choice_and_strict_zero_vetoes',
        'test_remote_palette_requires_expired_unstarted_known_input',
    }), True),
    ('tests.test_native_observed_shop_controller104', 'NativeObservedShopController104Tests', 'test111-NativeObservedShopController104Tests', frozenset({
        'test_central_nonhud_band_and_cell_mapping_are_independent',
        'test_common_certificate_faces_prices_target_and_source_count_remain_strict',
        'test_normal_policy9_producer_reaches_durable_intent_restart_ack_and_next_floor',
        'test_normal_target_and_incomplete_results_never_acquire_restart_authority',
        'test_observed_items_floor_caps_gold_and_exact_protection_are_all_independent',
        'test_three_observed_floor_cells_under_offers_and_two_full_faces_have_independent_authority',
    }), True),
    ('tests.test_native_offer_controller105', 'NativeOfferController105Tests', 'test111-NativeOfferController105Tests', frozenset({
        'test_c_independently_rejects_shifted_fragment_subminimum_and_counterfeit_absence',
        'test_closed_offer_metrics_ordinary_price_floor_and_target_absence_are_independent',
        'test_normal_closed_offer_reaches_durable_intent_restart_ack_and_new_floor',
        'test_normal_target_candidate_and_unobserved_price_never_restart',
        'test_normal_top_anchored_fragment_reaches_durable_intent_restart_ack_and_new_floor',
    }), True),
    ('tests.test_native_single_offer108', 'NativeSingleOfferController108Tests', 'test111-NativeSingleOfferController108Tests', frozenset({
        'test_controller_rechecks_observed_boundary_floor_projection_and_forged_certificate',
        'test_existing_closed_price_certificate_is_independently_adopted',
        'test_normal_producer_joins_durable_pause_intent_restart_ack_and_next_floor',
        'test_target_candidate_and_unobserved_price_never_receive_restart_authority',
    }), True),
    ('tests.test_native_offer_geometry105', 'NativeOfferGeometry105Tests', 'test111-NativeOfferGeometry105Tests', frozenset({
        'test_same_top_observed_fragment_uses_full_face_row_and_preserves_target_priority',
    }), False),
    ('tests.test_native_closed_offer105', 'NativeClosedOffer105Tests', 'test111-NativeClosedOffer105Tests', frozenset({
        'test_target_or_candidate_has_priority_over_closed_identity',
    }), False),
    ('tests.test_native_full_data110', 'NativeFullData110Tests', 'test111-NativeFullData110Tests', frozenset({
        'test_current_classifier_scene_does_not_replace_original_motion_anchor',
        'test_data_unknown_keeps_original_unissued_step_and_never_restores_consumed_step',
        'test_first_eligible_queued_source_survives_faster_captures_and_worker_latency',
        'test_near_material_new_item_gold_protection_state_or_motion_cannot_start_data_refresh',
        'test_normal_producer_data_negative_uses_new_source_then_durable_restart_chain',
        'test_normal_target_candidate_win_over_queued_negative_or_later_unsafe_scene',
        'test_pending_unsafe_frame_blocks_negative_without_changing_bound_worker_identity',
        'test_queued_source_capture_budget_worker_budget_cancel_and_stale_result',
        'test_remote_material_stationary_full_starts_only_a_data_job',
        'test_unstable_prefix_frames_reserved_or_unknown_input_never_gain_data_rights',
    }), True),
    ('tests.test_native_classification111', 'NativeClassification111Tests', 'test111-NativeClassification111Tests', frozenset({
        'test_each_bridge_guard_or_original_source_deadline_falls_back_to_new_full',
        'test_latest_full_is_data_only_after_independent_move_and_keeps_original_clocks',
        'test_normal_complete_negative_is_bound_to_retained_pixels_and_current_pause',
        'test_original_worker_limit_and_cancel_cannot_reuse_retained_source',
        'test_target_candidate_remain_latched_and_never_restore_move',
        'test_unstable_or_other_prefix_never_replaces_the_data_pixel_lease',
    }), True),
    ('tests.test_native_classification111', 'NativeClassificationRetry111Tests', 'test111-NativeClassificationRetry111Tests', frozenset({
        'test_deadline_waits_for_actual_worker_then_fresh_full_owns_normal_negative',
        'test_late_slot_or_global_positive_hints_veto_fresh_negative',
        'test_latest_unsafe_frame_blocks_retry_without_rewinding_to_earlier_safe_pixels',
        'test_malformed_or_missing_deadline_report_never_starts_retry',
        'test_prefix_cancel_parent_expiration_and_late_root_positive_preserve_freeze',
        'test_retry_unknown_has_no_movement_credit_and_at_most_two_new_jobs',
        'test_source_149_150_ms_worker_begin_and_expired_before_start_keep_root_bound',
        'test_terminal_drain_can_retain_a_late_candidate_without_reopening',
    }), True),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test111-NativeFullFraming101Tests', frozenset({
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
    ('tests.test_native_open_full108', 'NativeOpenFull108Tests', 'test111-NativeOpenFull108Tests', frozenset({
        'test_a_second_unknown_does_not_restore_the_one_step_credit',
        'test_direct_opening_full_unknown_waits_for_independent_zero_then_enters_once',
        'test_new_candidate_after_actual_entry_is_held_without_restarting',
        'test_old_unknown_entry_history_does_not_borrow_the_direct_opening_geometry',
        'test_opening_bracket_positive_floor_and_exact_projection_are_required',
        'test_source_prefix_deadline_cancel_and_unknown_input_do_not_gain_new_authority',
        'test_target_candidate_upper_bound_and_strong_word_precede_new_entry',
    }), True),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test111-NativeCycle094Tests', frozenset({
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
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_unissued111', 'tests.test_native_goods111',
    'tests.test_native_image_price111', 'tests.test_native_upper_adoption111',
    'tests.test_native_classification111',
})
CORE_MODULES = shared.CORE_MODULES
DEPENDENCY_FIXTURES = ()
PRODUCT_PATHS = ('necroprobe/native_cycle.py', 'necroprobe/test099.py',
    'necroprobe/test111.py', 'test_111.sh', 'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/apply_ngg2.py')
APPROVED_CHANGED_REPOSITORY = frozenset({
    'necroprobe/native_cycle.py', 'necroprobe/test099.py',
    'patches/loopctrl/ngg2.patch', 'patches/loopctrl/apply_ngg2.py',
})
# All baseline tests/client/Ring/R12 sources are retained except the exact
# image-price expectation methods in this checked-in hash-bound manifest.
LEGACY_FIXTURE_EXCEPTIONS_PATH = 'patches/loopctrl/test111-fixture-exceptions.json'
LEGACY_FIXTURE_EXCEPTIONS = json.loads((HERE/'test111-fixture-exceptions.json').read_text())['files']
PRESERVED_REPOSITORY = tuple(dict.fromkeys((*shared.PRESERVED_REPOSITORY,
    *shared.PRODUCT_PATHS, 'necroprobe/test110.py', 'test_110.sh',
    'patches/loopctrl/run_test110_host.py', 'patches/loopctrl/run_test110_python39.py',
    'patches/loopctrl/test_device_ci110.py')))
RUNTIME_PROOF_POLICY = 'selected_current_runtime_boundaries_required'
BASELINE_RUNTIME_SHA256 = '37c079fdbf7c3f93ab17c49802b562b8923858ef3da8a6ca7b5a972fce1336a1'
CURRENT_MAC_CASES = ('negative', 'retention', 'candidate', 'fresh_deadline')
RUNTIME_SCOPE_FINALIZED = True
NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith(('NECRO111_', 'NECRO_TEST111_')) for name in os.environ):
        raise ValueError('TEST111 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST111 native/method/current Mac author inventories are pending')
    labels = [row[2] for row in CASES]
    if not CASES or len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST111 scope is empty or duplicated')
    if not REQUIRED_NEW_SCOPES <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST111 new focused scopes are missing')


def native_delta(before, current, allowed, added=None):
    added = set(EXPECTED_NATIVE_ADDITIONS if added is None else added)
    if set(before)-set(current) or set(current)-set(before) != added:
        raise ValueError('TEST111 native addition/removal scope differs')
    changed = {p for p in current if before.get(p) != current[p]}
    if not allowed or changed != set(allowed) or not added <= changed:
        raise ValueError('TEST111 exact native changed-source set differs')
    return changed


def approved_patch_identity(current, original, manifest, before):
    if sha(current) != manifest['patch_sha256'] or sha(original) != before['patch_sha256'] or current == original:
        raise ValueError('TEST111 approved G2 patch/manifest source differs')
    return sha(current)


def preserved_fixture_identity(path, current, original):
    matches = [row for row in LEGACY_FIXTURE_EXCEPTIONS if row['path'] == path]
    if not matches:
        return retained_identity(current, original)
    if len(matches) != 1:
        raise ValueError('TEST111 duplicate fixture exception')
    spec = matches[0]
    if sha(original) != spec['old_file_sha256'] or sha(current) != spec['new_file_sha256']:
        raise ValueError('TEST111 unreviewed historical fixture revision: '+path)
    scrubbed = []
    for raw, key in ((original, 'old_sha256'), (current, 'new_sha256')):
        text = raw.decode(); tree = ast.parse(text); lines = text.splitlines(keepends=True); replacements = []
        for method in spec['methods']:
            klass, name = method['name'].split('.')
            target = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == klass)
            selected = next(n for n in target.body if isinstance(n, ast.FunctionDef) and n.name == name)
            if selected.decorator_list or sha(ast.get_source_segment(text, selected).encode()) != method[key]:
                raise ValueError('TEST111 approved method hash differs: '+method['name'])
            replacements.append((selected.lineno-1, selected.end_lineno, '    # APPROVED TEST111 METHOD '+method['name']+'\n'))
        for start, end, marker in sorted(replacements, reverse=True):
            lines[start:end] = [marker]
        scrubbed.append(''.join(lines))
    if scrubbed[0] != scrubbed[1]:
        raise ValueError('TEST111 bytes outside approved methods changed: '+path)
    return sha(current)


def runtime_source_identity(before, current):
    if not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST111 focused current Runtime boundary scope is pending')
    runtime = 'LoopCtrlUITests/NG2Runtime.swift'
    if before.get(runtime) != BASELINE_RUNTIME_SHA256 or current.get(runtime) != BASELINE_RUNTIME_SHA256:
        raise ValueError('TEST111 unchanged Runtime source identity differs')
    return dict(policy=RUNTIME_PROOF_POLICY, source_reference=NATIVE_BASELINE,
        baseline_runtime_sha256=before[runtime], current_runtime_sha256=current[runtime],
        current_controller_sha256=current['LoopCtrlUITests/NG2Controller.c'],
        executed_in_host_selector=False, current_mac_execution_required=True,
        expected_current_mac_cases=list(CURRENT_MAC_CASES),
        limitation='Historical build217 is preservation evidence only; current C classification source boundaries require selected actual Mac callbacks.')


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest = json.loads(pinned_bytes(driver, 'patches/loopctrl/ngg2-manifest.json', code))
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name:row['patched_sha256'] for name,row in before['files'].items()}
    old.update({name:row['sha256'] for name,row in before['additions'].items()})
    current = sealed['native_source_sha256']
    if len(old) != 36 or len(current) != 36:
        raise ValueError('TEST111 native inventory is not 36')
    changed = native_delta(old,current,EXPECTED_NATIVE_CHANGES)
    approved_patch_identity(pinned_bytes(driver,'patches/loopctrl/ngg2.patch',code),
        git(driver,'show',NATIVE_BASELINE+':patches/loopctrl/ngg2.patch'),manifest,before)
    expected = {'api_version':'1.98.16-ngg2','client_capability':'necrogold_native_v15',
        'cycle_capability':'necrogold_native_cycle_v1','cycle_profile':'normal-1-1-cycle-v1',
        'irregular_capability':'necrogold_native_irregular_v1','irregular_profile':'normal-1-1-irregular-v1',
        'image_price_capability':'necrogold_native_image_price_v1','compiler_profile_version':3}
    if any(manifest.get(k) != v for k,v in expected.items()):
        raise ValueError('TEST111 native API/profile/cap/compiler identity differs')
    if (sealed['api_version'],sealed['client_capability']) != ('1.98.16-ngg2','necrogold_native_v15'):
        raise ValueError('TEST111 installed native API changed')
    baseline_paths = [p.decode() for p in git(driver,'ls-tree','-r','--name-only','-z',NATIVE_BASELINE).split(b'\0') if p]
    paths = list(PRESERVED_REPOSITORY)
    paths.extend(p for p in baseline_paths if p.startswith(('tests/','necroprobe/','tools/ring_native/','legacy/r12/')))
    preserved = {}
    for path in dict.fromkeys(paths):
        if path in APPROVED_CHANGED_REPOSITORY:
            continue
        preserved[path] = preserved_fixture_identity(path,pinned_bytes(driver,path,code),git(driver,'show',NATIVE_BASELINE+':'+path))
    if sum(p.startswith('legacy/r12/') for p in preserved) != 40:
        raise ValueError('TEST111 R12 source inventory differs')
    revised = {}
    for path in APPROVED_CHANGED_REPOSITORY:
        raw = pinned_bytes(driver,path,code)
        if raw == git(driver,'show',NATIVE_BASELINE+':'+path):
            raise ValueError('approved changed source is unchanged: '+path)
        revised[path] = sha(raw)
    repository = {}
    for name,spec in manifest['additions'].items():
        digest = addition_identity(driver,name,spec)
        directory = 'tools/ring_native/' if spec.get('source_root') == 'ring_native' else 'patches/loopctrl/ngg2/'
        pinned_bytes(driver,directory+spec['source'],code)
        if current[name] != digest:
            raise ValueError('TEST111 repository/installed native source differs: '+name)
        repository[name] = digest
    products = {p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS}
    fixtures = set(p for p in baseline_paths if p.startswith('patches/loopctrl/') and p.endswith(('.py','.swift','.c')))
    fixtures.update(name.replace('.','/')+'.py' for name in (*CORE_MODULES,*(row[0] for row in CASES)))
    fixtures.update(('patches/loopctrl/run_test111_host.py','patches/loopctrl/test_device_ci111.py',
        'patches/loopctrl/run_test111_python39.py',LEGACY_FIXTURE_EXCEPTIONS_PATH,
        'patches/loopctrl/check_runtime111.py','patches/loopctrl/ngg2_runtime111_tests.swift'))
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,
        fixture_source_sha256={p:sha(pinned_bytes(driver,p,code)) for p in sorted(fixtures)},
        runtime_proof_policy=runtime_source_identity(old,current), changed_native_sources=sorted(changed),
        preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,changed_repository_source_sha256=revised,
        repository_native_source_sha256=repository,product_sha256=products,
        legacy_fixture_exceptions=LEGACY_FIXTURE_EXCEPTIONS,
        direct_c_compiler_binding='Selected fixtures compile exact installed sealed native sources; original-image calibration is separate.')

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

def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test111-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'): parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(HERE)]
    verifier=importlib.import_module('verify_package');sealed=verifier.inspect_native_sources(upstream,driver)
    binding=source_identity(driver,sealed)
    suites=native_suites(upstream,driver)
    selected_cases(case for _,cases in suites for case in cases)
    fixture=importlib.import_module('tests.test_native_controller');cycle=importlib.import_module('tests.test_native_cycle094')
    abi={n:ctypes.sizeof(getattr(fixture,n)) for n in ('Scene','Status','Event','MotionWait','RecoveryStatus')}
    abi['Cycle']=ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864,Status=192,Event=128,MotionWait=48,RecoveryStatus=456,Cycle=216):
        raise ValueError('TEST111 public ABI changed')
    evidence=dict(scope='TEST111 selected device-failure contracts',source_identity=sealed,
        production_source_binding=binding,abi_bytes=abi,device_test='not_run',
        not_run=['old110 complete29 Runtime faults','historical whole host suites',
                 'iPhone reach rate, rare-target precision and human speed acceptance'])
    for label,cases in suites: run_scope(label,cases,output,evidence)
    selector=importlib.import_module('test_device_ci111')
    run_scope('test111-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection111Tests),output,evidence)
    if verifier.inspect_native_sources(upstream,driver) != sealed or source_identity(driver,sealed) != binding:
        raise ValueError('TEST111 selected tests changed sealed source')
    reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
    evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
    (output/'test111-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST111 selected source-bound contracts; actual selected Mac boundaries and phone acceptance are separate')


if __name__=='__main__': main()
