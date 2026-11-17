"""TEST112 source-bound selected contracts. No device traffic or phone acceptance.

Selected native/method and eight focused Mac boundary scopes are authored;
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
_spec = importlib.util.spec_from_file_location('test112_shared_source_utils', HERE/'run_test111_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '08d6ce9a8d329e114740b2a5d67618d7f37dc3ae'
SCOPE_FINALIZED = True  # Closed author inventories; actual execution is separate.
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlUITests/NG2Controller.c',
    'LoopCtrlUITests/NG2Controller.h', 'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Runtime.swift'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
CASES = (
    ('tests.test_native_restart_yield112', 'NativeRestartYield112Tests', 'test112-NativeRestartYield112Tests', frozenset({
        'test_death_retires_budget_into_existing_irregular_owner_after_worker_settles',
        'test_durable_first_newfloor_survives_unknown_tail_without_rewinding_ui',
        'test_enable_is_immutable_and_old_walking_restart_still_continues',
        'test_first_goods_is_data_only_and_partial_then_full_each_requires_positive_veto',
        'test_full_then_partial_sources_are_serial_once_and_pause_has_no_restart',
        'test_irregular_ui_companion_vetoes_floor_permit_and_pause_confirmation',
        'test_late_worker_hint_survives_frozen_data_timeout_without_handoff',
        'test_later_floor_observation_revokes_permit_without_renewing_parent',
        'test_old_negative_or_uncommitted_restart_is_not_a_yield_basis',
        'test_optin_after_durable_restart_never_enters_another_level_with_spent_budget',
        'test_optin_initial_floor_or_other_ui_is_input_free_but_old_start_is_unchanged',
        'test_original_budgets_cancellation_and_started_or_unknown_pause_cannot_mint_handoff',
        'test_positive_invalid_yield_cleanup_pause_ack_is_observed_without_handoff_or_resend',
        'test_retained_goods_cannot_replace_current_ui_scene_or_expired_prefix_source',
        'test_source_bound_permit_requires_live_current_floor_and_real_pause_confirmation',
        'test_stale_first_pause_or_invalid_pause_companion_never_opens_floor_start',
        'test_target_candidate_late_hint_and_malformed_results_never_allow_next_start',
    }), True),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test112-NativeCycle094Tests', frozenset({
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
    ('tests.test_native_handoff099', 'NativeHandoff099Tests', 'test112-NativeHandoff099Tests', frozenset({
        'test_changed_uncertain_gold_goods_candidate_or_protection_never_requalifies_clear_handoff',
        'test_clear_cutoff_requalifies_and_freezes_a_new_clear_pause_source',
        'test_clear_search_twelve_needs_actual_cleanup_pause_before_allowed',
        'test_earlier_durable_negative_history_needs_a_new_clear_level_and_explicit_search_cutoff',
        'test_only_fourth_durable_negative_limit_mints_classified_source_handoff',
        'test_read_only_handoff_companion_has_separate_abi_and_inert_missing_controller',
        'test_residual_negative_does_not_turn_generic_walk_or_session_limit_into_handoff',
        'test_target_candidate_unknown_and_unknown_pause_cannot_handoff',
    }), True),
    ('tests.test_native_irregular110', 'NativeIrregular110Tests', 'test112-NativeIrregular110Tests', frozenset({
        'test_continue_outcome_is_saved_before_restart_even_after_two_menu_images',
        'test_continue_started_unknown_never_resends_or_advances_restart_credit',
        'test_death_continue_menu_restart_outcome_uses_each_durable_gate_once',
        'test_death_requires_positive_full_prompt_hearts_and_prior_live_baseline',
        'test_death_trigger_requires_fresh_stable_prefix_and_no_reserved_or_started_input',
        'test_durable_unreserved_stalled_episode_upgrades_on_fresh_strong_death_without_new_budget',
        'test_eighth_attempt_and_expired_visual_parent_cannot_create_enemy_retry',
        'test_enemy_occluded_destination_is_data_only_while_origin_and_other_masks_stay_fixed',
        'test_first_positive_enemy_zero_waits_for_original_period_without_finishing_or_resending',
        'test_first_restart_full_or_partial_goods_becomes_bound_job_only_after_durable_outcome',
        'test_goods_after_restart_floor_uses_one_first_source_hint_until_outcome_is_durable',
        'test_intervening_moved_or_nonzero_motion_never_becomes_stalled',
        'test_malformed_same_capture_companion_cannot_qualify_live_ui_or_restart_outcome',
        'test_menu_requires_unique_two_current_boxes_and_never_reuses_pause_coordinates',
        'test_missing_wrong_direction_or_malformed_enemy_never_creates_episode',
        'test_next_death_uses_durable_restart_floor_baseline_without_rewriting_previous_episode',
        'test_none_full_death_glyph_vetoes_live_baseline_menu_and_changed_floor_without_continue',
        'test_old_profile_and_late_or_duplicate_opt_in_preserve_existing_authority',
        'test_pending_ring_result_quiesces_then_candidate_or_failure_holds_before_ui',
        'test_reserved_started_or_ack_waiting_pause_never_upgrades_to_continue',
        'test_restart_initial_sync_epoch_stays_at_first_floor_without_rewinding_current_unknown',
        'test_restart_requires_changed_live_floor_and_outcome_before_new_shop',
        'test_restart_ticket_keeps_qualified_ui_type_and_coordinates_at_intent_and_begin',
        'test_second_enemy_proof_requires_original_period_and_unchanged_parent',
        'test_started_ui_storage_or_parent_expiry_and_late_begin_cannot_revive_after_ack',
        'test_storage_failure_before_ui_or_after_intent_freezes_without_new_input',
        'test_two_period_separated_enemy_zeros_checkpoint_then_pause_durable_restart',
        'test_ui_begin_still_checks_front_lock_and_owner',
        'test_unknown_tail_cannot_replace_restart_floor_or_goods_target_source_before_durable',
        'test_wrong_episode_prefix_source_and_cancel_never_replay_commits',
    }), True),
    ('tests.test_native_upper_entry112', 'NativeUpperEntry112Tests', 'test112-NativeUpperEntry112Tests', frozenset({
        'test_each_safe_step_tracks_live_model_until_all_goods_then_durable_restart',
        'test_empty_lower_opening_observes_only_the_fresh_safe_entry_step',
        'test_extra_world_item_or_lost_gold_invalidates_movement_stickily',
        'test_four_started_inputs_exhaust_observation_without_general_navigation',
        'test_fresh_queued_full_after_fourth_input_or_move_parent_expiry_still_keeps_candidate',
        'test_geometry_projection_and_first_safe_floor_are_independent_requirements',
        'test_initial_partial_counterexamples_do_not_gain_the_frozen_upper_route',
        'test_initial_partial_positive_hints_preempt_any_upper_input',
        'test_normal_producer_partial_probes_complete_public_c_hhdd_and_single_negative',
        'test_normal_nonempty_partial_potential_may_still_extend_into_hud_before_down',
        'test_other_normally_certified_shop_row_is_not_the_original_merchandise',
        'test_prefix_cancel_root_and_live_phase_revoke_new_permission',
        'test_remaining_live_schedule_budget_never_renews_the_fixed_parent',
        'test_seven_partial_aliases_remain_until_first_down_reveals_the_real_full_row',
        'test_started_unknown_move_never_resends_or_credits_a_new_step',
        'test_target_candidate_and_late_hint_preempt_later_negative',
        'test_unobserved_second_floor_waits_without_guessing_or_restoring_root',
    }), True),
    ('tests.test_native_entered112', 'NativeEntered112Tests', 'test112-NativeEntered112Tests', frozenset({
        'test_candidate_target_and_strong_word_keep_priority_over_late_moved',
        'test_changed_items_projection_gold_or_local_floor_never_gain_refresh',
        'test_late_original_moved_updates_once_and_binds_only_fresh_full_data',
        'test_original_unknown_blocked_tween_and_expired_visual_proof_cannot_refresh',
        'test_refreshed_unknown_requires_independent_zero_then_only_one_future_observation',
        'test_unknown_input_cannot_use_late_moved_as_a_known_ack',
        'test_worker_prefix_unstable_and_cancel_cannot_reanchor',
    }), True),
    ('tests.test_native_singleton_phase112', 'NativeSingletonPhase112Tests', 'test112-NativeSingletonPhase112Tests', frozenset({
        'test_each_lighting_phase_and_action_adds_only_read_only_zero_qualification',
        'test_known_zero_translated_texture_and_missing_independent_bands_do_not_qualify',
        'test_null_and_out_of_range_direction_are_rejected',
        'test_old_landmark_two_dimensional_dirt_and_near_floor_are_required',
    }), True),
    ('tests.test_native_singleton_phase112', 'NativeSingletonPhaseWait112Tests', 'test112-NativeSingletonPhaseWait112Tests', frozenset({
        'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
        'test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero',
        'test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back',
        'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
        'test_plural_proof_needs_independent_stable_current_prefix_capture',
        'test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket',
    }), True),
    ('tests.test_native_entry_episode102', 'NativeEntryEpisode102Tests', 'test112-NativeEntryEpisode102Tests', frozenset({
        'test_ack_unknown_visual_wait_and_unknown_synth_do_not_create_second_step',
        'test_full_rebind_before_first_input_withdraws_unsent_ticket_without_resetting_parent',
        'test_full_unknown_after_first_move_requalifies_up_from_its_exact_latest_job',
        'test_old_top_and_horizontal_one_shots_cannot_acquire_entry_episode',
        'test_parent_and_current_roi_masks_floor_or_static_changes_reject_authority',
        'test_parent_horizon_input_budget_cancel_level_and_prefix_cannot_be_refreshed',
        'test_partial_unknown_after_first_move_needs_new_assessment_static_and_second_move',
        'test_pending_full_preserves_hold_assess_and_old_candidate_target_before_fifo_rebind',
        'test_pending_full_requires_safe_old_unknown_before_latest_full_second_step',
        'test_pending_worker_keeps_its_original_budget_after_observation_parent_expires',
        'test_second_observation_normal_complete_negative_preserves_durable_restart_protocol',
        'test_second_unknown_and_goods_unknown_hold_without_generic_credit_or_third_input',
    }), True),
    ('tests.test_native_lower_observation104', 'NativeLowerObservation104Tests', 'test112-NativeLowerObservation104Tests', frozenset({
        'test_candidate_target_upper_word_and_unfit_union_do_not_gain_local_down',
        'test_current_prefix_independent_capture_and_control_guards_do_not_reuse_tickets',
        'test_far_refresh_and_expiry_preserve_first_parent_and_never_reset_spent_count',
        'test_full_unknown_and_authenticated_hud_coverage_need_the_local_down',
        'test_pending_full_fifo_preserves_old_candidate_before_latest_source',
        'test_safe_partial_after_first_down_requires_second_down_before_whole_lower_band',
        'test_seven_item_projection_requires_geometric_two_downs_and_fresh_refinement',
        'test_static_floor_exact_projection_and_motion_rejections_have_frozen_diagnostics',
        'test_unproved_direct_or_queued_full_bridge_never_mints_down_from_later_self_zero',
    }), True),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test112-NativeFullFraming101Tests', frozenset({
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
    ('tests.test_native_entry_corridor102', 'NativeEntryCorridor102Tests', 'test112-NativeEntryCorridor102Tests', frozenset({
        'test_actual_up_opening_and_completed_unknown_domain_remain_required',
        'test_item_projection_must_explain_all_protection_without_loss',
        'test_missing_dirt_or_stone_rail_never_grants_a_framing_step',
        'test_observed_row4_corridor_gets_one_future_input_then_new_candidate_job',
        'test_old097_row4_without_positive_gold_rail_still_holds',
        'test_origin_destination_and_axis_floor_are_not_inferred',
        'test_original_horizon_prefix_static_zero_and_cancel_are_never_refreshed',
        'test_source_roi_cannot_lose_potential_goods_to_viewport_or_hud',
    }), True),
    ('tests.test_native_open_full108', 'NativeOpenFull108Tests', 'test112-NativeOpenFull108Tests', frozenset({
        'test_a_second_unknown_does_not_restore_the_one_step_credit',
        'test_direct_opening_full_unknown_waits_for_independent_zero_then_enters_once',
        'test_new_candidate_after_actual_entry_is_held_without_restarting',
        'test_old_unknown_entry_history_does_not_borrow_the_direct_opening_geometry',
        'test_opening_bracket_positive_floor_and_exact_projection_are_required',
        'test_source_prefix_deadline_cancel_and_unknown_input_do_not_gain_new_authority',
        'test_target_candidate_upper_bound_and_strong_word_precede_new_entry',
    }), True),
    ('tests.test_native_singleton_stationary095', 'NativeSingletonStationary095Tests', 'test112-NativeSingletonStationary095Tests', frozenset({
        'test_all_raw_scores_are_finite_zero_ranked_and_inside_fallback_domain',
        'test_blur_zero_absolute_bound_and_all_seventy_two_finite_competitors',
        'test_common_noncollinear_dirt_support_and_unique_nine_placements_are_required',
        'test_exact_old_singleton_is_preserved_and_new_stone_cannot_replace_it',
        'test_full_source_and_projected_hud_sample_rois_are_excluded',
        'test_near_floor_all_protection_gold_goods_invalid_scenes_and_direction_reject',
        'test_single_old_stone_fixed_surface_adds_only_readonly_zero_evidence',
        'test_world_axis_strength_regions_and_last_competitor_lead_boundaries',
    }), True),
    ('tests.test_native_plural_stationary103', 'NativePluralStationary103Tests', 'test112-NativePluralStationary103Tests', frozenset({
        'test_all_blur_finite_absolute_bound_and_all_raw_competitors',
        'test_both_scenes_near_floor_protection_gold_goods_and_invalid_reject',
        'test_exact_old_plural_stones_and_old_dirt_cannot_be_replaced',
        'test_exactly_one_cardinal_unit_phase_and_supported_unit_axis',
        'test_fixed_world_unit_lighting_phase_adds_only_zero_qualification',
        'test_noncollinear_unique_nine_placements_and_full_hud_rois',
        'test_real_translated_procedural_world_never_qualifies_zero',
        'test_world_axis_strength_regions_and_last_lead_boundaries',
    }), True),
    ('tests.test_native_clear_stationary095', 'NativeClearStationary095Tests', 'test112-NativeClearStationary095Tests', frozenset({
        'test_actual_gold_unknown_uses_the_original_strict_handoff_only',
        'test_cancel_or_started_unknown_cannot_reuse_the_zero_wait',
        'test_independent_clear_singleton_zero_rearms_only_a_new_future_ticket',
        'test_known_motion_or_failed_decode_cannot_fall_back_at_observation_or_begin',
        'test_original_wait_and_parent_equalities_cannot_be_renewed_by_zero_proof',
        'test_zero_proof_needs_independent_stable_current_prefix_capture',
    }), True),
    ('tests.test_native_plural_wait103', 'NativePluralWait103Tests', 'test112-NativePluralWait103Tests', frozenset({
        'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
        'test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero',
        'test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back',
        'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
        'test_plural_proof_needs_independent_stable_current_prefix_capture',
        'test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket',
    }), True),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test112-NativeStationaryWait076Tests', frozenset({
        'test_adjacent_blocked_frames_cannot_replace_the_original_anchor',
        'test_goods_priority_and_unproven_new_gold_hold_without_moving',
        'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority',
        'test_proof_requires_independent_current_prefix_and_increasing_capture',
        'test_ready_or_issued_unknown_does_not_reopen_the_same_wait',
        'test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit',
        'test_unsafe_changed_scene_and_unproven_or_expired_ticket_cannot_start_wait',
        'test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it',
    }), True),
    ('tests.test_native_full_data110', 'NativeFullData110Tests', 'test112-NativeFullData110Tests', frozenset({
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
    ('tests.test_native_classification111', 'NativeClassification111Tests', 'test112-NativeClassification111Tests', frozenset({
        'test_each_bridge_guard_or_original_source_deadline_falls_back_to_new_full',
        'test_latest_full_is_data_only_after_independent_move_and_keeps_original_clocks',
        'test_normal_complete_negative_is_bound_to_retained_pixels_and_current_pause',
        'test_original_worker_limit_and_cancel_cannot_reuse_retained_source',
        'test_target_candidate_remain_latched_and_never_restore_move',
        'test_unstable_or_other_prefix_never_replaces_the_data_pixel_lease',
    }), True),
    ('tests.test_native_classification111', 'NativeClassificationRetry111Tests', 'test112-NativeClassificationRetry111Tests', frozenset({
        'test_deadline_waits_for_actual_worker_then_fresh_full_owns_normal_negative',
        'test_late_slot_or_global_positive_hints_veto_fresh_negative',
        'test_latest_unsafe_frame_blocks_retry_without_rewinding_to_earlier_safe_pixels',
        'test_malformed_or_missing_deadline_report_never_starts_retry',
        'test_prefix_cancel_parent_expiration_and_late_root_positive_preserve_freeze',
        'test_retry_unknown_has_no_movement_credit_and_at_most_two_new_jobs',
        'test_source_149_150_ms_worker_begin_and_expired_before_start_keep_root_bound',
        'test_terminal_drain_can_retain_a_late_candidate_without_reopening',
    }), True),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_singleton_phase112', 'tests.test_native_entered112',
    'tests.test_native_upper_entry112', 'tests.test_native_restart_yield112',
})
CORE_MODULES = shared.CORE_MODULES
DEPENDENCY_FIXTURES = ()
PRODUCT_PATHS = ('necroprobe/native_cycle.py', 'necroprobe/trial_evidence099.py', 'necroprobe/campaign099.py', 'necroprobe/test099.py',
    'necroprobe/test112.py', 'test_112.sh', 'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/apply_ngg2.py')
APPROVED_CHANGED_REPOSITORY = frozenset({
    'necroprobe/native_cycle.py', 'necroprobe/trial_evidence099.py', 'necroprobe/campaign099.py',
    'patches/loopctrl/ngg2.patch', 'patches/loopctrl/apply_ngg2.py',
})
# All baseline tests/client/Ring/R12 sources are retained except the exact
# one expired-worker expectation method in this checked-in hash-bound manifest.
LEGACY_FIXTURE_EXCEPTIONS_PATH = 'patches/loopctrl/test112-fixture-exceptions.json'
LEGACY_FIXTURE_EXCEPTIONS = json.loads((HERE/'test112-fixture-exceptions.json').read_text())['files']
PRESERVED_REPOSITORY = tuple(dict.fromkeys((*shared.PRESERVED_REPOSITORY,
    *shared.PRODUCT_PATHS, 'necroprobe/test110.py', 'test_110.sh', 'necroprobe/test111.py', 'test_111.sh',
    'patches/loopctrl/run_test111_host.py', 'patches/loopctrl/run_test111_python39.py',
    'patches/loopctrl/test_device_ci111.py')))
RUNTIME_PROOF_POLICY = 'selected_current_runtime_boundaries_required'
BASELINE_RUNTIME_SHA256 = '37c079fdbf7c3f93ab17c49802b562b8923858ef3da8a6ca7b5a972fce1336a1'
CURRENT_MAC_CASES = ('legacy', 'yield', 'first_partial', 'first_full', 'producer_return', 'commit_return', 'capture_drain', 'upper_entry')
RUNTIME_SCOPE_FINALIZED = True
NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith(('NECRO112_', 'NECRO_TEST112_')) for name in os.environ):
        raise ValueError('TEST112 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST112 native/method/current Mac author inventories are pending')
    labels = [row[2] for row in CASES]
    if not CASES or len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST112 scope is empty or duplicated')
    if not REQUIRED_NEW_SCOPES <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST112 new focused scopes are missing')


def native_delta(before, current, allowed, added=None):
    added = set(EXPECTED_NATIVE_ADDITIONS if added is None else added)
    if set(before)-set(current) or set(current)-set(before) != added:
        raise ValueError('TEST112 native addition/removal scope differs')
    changed = {p for p in current if before.get(p) != current[p]}
    if not allowed or changed != set(allowed) or not added <= changed:
        raise ValueError('TEST112 exact native changed-source set differs')
    return changed


def approved_patch_identity(current, original, manifest, before):
    if sha(current) != manifest['patch_sha256'] or sha(original) != before['patch_sha256'] or current == original:
        raise ValueError('TEST112 approved G2 patch/manifest source differs')
    return sha(current)


def preserved_fixture_identity(path, current, original):
    matches = [row for row in LEGACY_FIXTURE_EXCEPTIONS if row['path'] == path]
    if not matches:
        return retained_identity(current, original)
    if len(matches) != 1:
        raise ValueError('TEST112 duplicate fixture exception')
    spec = matches[0]
    if sha(original) != spec['old_file_sha256'] or sha(current) != spec['new_file_sha256']:
        raise ValueError('TEST112 unreviewed historical fixture revision: '+path)
    scrubbed = []
    for raw, key in ((original, 'old_sha256'), (current, 'new_sha256')):
        text = raw.decode(); tree = ast.parse(text); lines = text.splitlines(keepends=True); replacements = []
        for method in spec['methods']:
            klass, name = method['name'].split('.')
            target = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == klass)
            selected = next(n for n in target.body if isinstance(n, ast.FunctionDef) and n.name == name)
            if selected.decorator_list or sha(ast.get_source_segment(text, selected).encode()) != method[key]:
                raise ValueError('TEST112 approved method hash differs: '+method['name'])
            replacements.append((selected.lineno-1, selected.end_lineno, '    # APPROVED TEST112 METHOD '+method['name']+'\n'))
        for start, end, marker in sorted(replacements, reverse=True):
            lines[start:end] = [marker]
        scrubbed.append(''.join(lines))
    if scrubbed[0] != scrubbed[1]:
        raise ValueError('TEST112 bytes outside approved methods changed: '+path)
    return sha(current)


def runtime_source_identity(before, current):
    if not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST112 focused current Runtime boundary scope is pending')
    runtime = 'LoopCtrlUITests/NG2Runtime.swift'
    if (before.get(runtime) != BASELINE_RUNTIME_SHA256 or not isinstance(current.get(runtime),str)
            or len(current[runtime]) != 64 or any(c not in '0123456789abcdef' for c in current[runtime])
            or current[runtime] == BASELINE_RUNTIME_SHA256):
        raise ValueError('TEST112 changed Runtime source identity differs')
    return dict(policy=RUNTIME_PROOF_POLICY, source_reference=NATIVE_BASELINE,
        baseline_runtime_sha256=before[runtime], current_runtime_sha256=current[runtime],
        current_controller_sha256=current['LoopCtrlUITests/NG2Controller.c'],
        executed_in_host_selector=False, current_mac_execution_required=True,
        expected_current_mac_cases=list(CURRENT_MAC_CASES),
        before_runtime_api_assertion_required=True,expected_before_runtime_case='optin_red',
        limitation='Before-source37c API assertion Red is separate from required current8 Runtime callbacks; old217/219 Runtime history is not current execution.')


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest = json.loads(pinned_bytes(driver, 'patches/loopctrl/ngg2-manifest.json', code))
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name:row['patched_sha256'] for name,row in before['files'].items()}
    old.update({name:row['sha256'] for name,row in before['additions'].items()})
    current = sealed['native_source_sha256']
    if len(old) != 36 or len(current) != 36:
        raise ValueError('TEST112 native inventory is not 36')
    changed = native_delta(old,current,EXPECTED_NATIVE_CHANGES)
    approved_patch_identity(pinned_bytes(driver,'patches/loopctrl/ngg2.patch',code),
        git(driver,'show',NATIVE_BASELINE+':patches/loopctrl/ngg2.patch'),manifest,before)
    expected = {'api_version':'1.98.16-ngg2','client_capability':'necrogold_native_v15',
        'cycle_capability':'necrogold_native_cycle_v1','cycle_profile':'normal-1-1-cycle-v1',
        'irregular_capability':'necrogold_native_irregular_v1','irregular_profile':'normal-1-1-irregular-v1',
        'image_price_capability':'necrogold_native_image_price_v1','compiler_profile_version':3,
        'restart_yield_capability':'necrogold_native_restart_yield_v1','restart_yield_start_flag':'yield_after_restart'}
    if any(manifest.get(k) != v for k,v in expected.items()):
        raise ValueError('TEST112 native API/profile/cap/compiler identity differs')
    if (sealed['api_version'],sealed['client_capability']) != ('1.98.16-ngg2','necrogold_native_v15'):
        raise ValueError('TEST112 installed native API changed')
    baseline_paths = [p.decode() for p in git(driver,'ls-tree','-r','--name-only','-z',NATIVE_BASELINE).split(b'\0') if p]
    paths = list(PRESERVED_REPOSITORY)
    ring_raw=pinned_bytes(driver,'necroprobe/ring_native_manifest.json',code)
    retained_identity(ring_raw,git(driver,'show',NATIVE_BASELINE+':necroprobe/ring_native_manifest.json'))
    ring=json.loads(ring_raw)
    if len(ring['sources'])!=15:raise ValueError('TEST112 canonical inventory differs')
    paths.extend(ring['sources'])
    paths.extend(p for p in baseline_paths if p.startswith(('tests/','necroprobe/','tools/ring_native/','legacy/r12/')))
    preserved = {}
    for path in dict.fromkeys(paths):
        if path in APPROVED_CHANGED_REPOSITORY:
            continue
        preserved[path] = preserved_fixture_identity(path,pinned_bytes(driver,path,code),git(driver,'show',NATIVE_BASELINE+':'+path))
    if sum(p.startswith('legacy/r12/') for p in preserved) != 40:
        raise ValueError('TEST112 R12 source inventory differs')
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
            raise ValueError('TEST112 repository/installed native source differs: '+name)
        repository[name] = digest
    products = {p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS}
    fixtures = set(p for p in baseline_paths if Path(p).parent.as_posix()=='patches/loopctrl' and p.endswith(('.py','.swift','.c')))
    fixtures.update(name.replace('.','/')+'.py' for name in (*CORE_MODULES,*(row[0] for row in CASES)))
    fixtures.update(('patches/loopctrl/run_test112_host.py','patches/loopctrl/test_device_ci112.py',
        'patches/loopctrl/run_test112_python39.py',LEGACY_FIXTURE_EXCEPTIONS_PATH,
        'patches/loopctrl/check_runtime112.py','patches/loopctrl/ngg2_runtime112_tests.swift',
        'patches/loopctrl/generate_upper112_pixels.py','patches/loopctrl/ngg2_runtime112_upper_fixture.c',
        'tests/test_native_ring_bank094.py','tests/test_native_shop_coverage102.py',
        'tests/test_native_offer_coverage104.py','necroprobe/non_target_features094.json'))
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
    (output/'test112-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
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
        raise ValueError('TEST112 public ABI changed')
    evidence=dict(scope='TEST112 selected device-failure contracts',source_identity=sealed,
        production_source_binding=binding,abi_bytes=abi,device_test='not_run',
        not_run=['old110 complete29 Runtime faults','historical whole host suites',
                 'iPhone reach rate, rare-target precision and human speed acceptance'])
    for label,cases in suites: run_scope(label,cases,output,evidence)
    selector=importlib.import_module('test_device_ci112')
    run_scope('test112-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection112Tests),output,evidence)
    if verifier.inspect_native_sources(upstream,driver) != sealed or source_identity(driver,sealed) != binding:
        raise ValueError('TEST112 selected tests changed sealed source')
    reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
    evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
    (output/'test112-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST112 selected source-bound contracts; actual selected Mac boundaries and phone acceptance are separate')


if __name__=='__main__': main()
