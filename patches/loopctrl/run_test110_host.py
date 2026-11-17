"""TEST110 selected actual-failure and opt-in irregular native contracts.

Current selected native units check software contracts, not phone/game acceptance.
Current changed Runtime callbacks must be source-bound in the Mac validation artifact.
This host selector does not execute Runtime; current Mac callbacks and iPhone acceptance remain separate scopes.
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
_spec = importlib.util.spec_from_file_location('test110_shared_source_utils', HERE/'run_test109_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'c2f76243c77a51682c24a4e059002cd732fd547d'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Controller.h',
    'LoopCtrlUITests/NG2Core.h', 'LoopCtrlUITests/NG2Perception.c',
    'LoopCtrlUITests/NG2Runtime.swift', 'LoopCtrlUITests/NG2CycleWire.swift',
    'LoopCtrlUITests/NG2CycleSpool.swift', 'LoopCtrlUITests/NG2CycleExport.swift',
    'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlKit/JSONRPCServer.swift',
})
# Exact authored methods are frozen; imports are source-bound dependencies only.
CASES = (
    ('tests.test_native_passage_ack110', 'NativePassageAck110Tests', 'test110-passage_ack110', frozenset({
        'test_ack_gold_unknown_keeps_the_original_visual_budget_then_confirms_a_real_unit',
        'test_actual_gold_releases_only_to_the_normal_shop_route',
        'test_existing_visual_deadline_and_cancel_do_not_gain_extra_observations',
        'test_new_goods_protection_or_nonzero_motion_cannot_release_the_fixed_wait',
        'test_post_move_wait_is_bounded_by_the_original_visual_deadline_without_new_frames',
        'test_rejected_wait_frames_never_replace_the_displacement_anchor',
        'test_sent_unknown_input_cannot_enter_the_ack_visual_or_post_move_wait',
        'test_true_moved_with_uncertain_gold_holds_until_fresh_positive_route_and_new_phase',
        'test_unknown_ack_comparisons_keep_eight_limit_and_never_resend',
        'test_unstable_foreign_prefix_and_early_frame_do_not_supply_motion_credit',
    }), True),
    ('tests.test_native_full_data110', 'NativeFullData110Tests', 'test110-full_data110', frozenset({
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
    ('tests.test_native_diagonal_entry110', 'NativeDiagonalEntry110Tests', 'test110-diagonal_entry110', frozenset({
        'test_actual_origin_destination_and_other_near_material_are_not_the_diagonal',
        'test_bracketed_diagonal_closure_retires_old_ticket_and_enters_on_same_frozen_beat',
        'test_legacy_profile_and_missing_actual_opening_do_not_gain_diagonal_permission',
        'test_nonzero_motion_prefix_deadline_and_cancel_cannot_reissue_entry',
        'test_only_positive_solid_gold_resolution_is_the_new_diagonal_relation',
        'test_source_and_latest_brackets_and_every_protected_role_remain_required',
        'test_unknown_sent_input_remains_frozen_without_another_move',
    }), True),
    ('tests.test_native_rect_icon110', 'NativeRectIcon110Tests', 'test110-rect_icon110', frozenset({
        'test_footer_menu_death_and_invalid_raster_guards_still_precede_floor',
        'test_input_pixels_and_opaque_stride_padding_do_not_change_the_scene',
        'test_intensity_neutrality_and_the_fixed_full_icon_location_are_preserved',
        'test_missing_bar_thin_letters_short_glyphs_and_visible_padding_do_not_pass',
        'test_public_rgba_after_ack_holds_goods_and_requires_an_observed_pause',
        'test_rectangular_opening_is_a_subset_and_does_not_clip_three_pixel_padding',
        'test_thin_letter_strokes_keep_two_independently_observed_pause_bars',
    }), True),
    ('tests.test_native_irregular110', 'NativeIrregular110Tests', 'test110-irregular110', frozenset({
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
        'test_restart_requires_changed_live_floor_and_outcome_before_new_shop',
        'test_restart_ticket_keeps_qualified_ui_type_and_coordinates_at_intent_and_begin',
        'test_restart_initial_sync_epoch_stays_at_first_floor_without_rewinding_current_unknown',
        'test_second_enemy_proof_requires_original_period_and_unchanged_parent',
        'test_started_ui_storage_or_parent_expiry_and_late_begin_cannot_revive_after_ack',
        'test_storage_failure_before_ui_or_after_intent_freezes_without_new_input',
        'test_two_period_separated_enemy_zeros_checkpoint_then_pause_durable_restart',
        'test_ui_begin_still_checks_front_lock_and_owner',
        'test_unknown_tail_cannot_replace_restart_floor_or_goods_target_source_before_durable',
        'test_wrong_episode_prefix_source_and_cancel_never_replay_commits',
    }), True),
    ('tests.test_native_irregular_producer110', 'NativeIrregularProducer110Tests', 'test110-irregular_producer110', frozenset({
        'test_a_complete_half_of_a_fourth_marker_is_ambiguous_instead_of_a_three_bar',
        'test_companion_is_real_native_and_does_not_mutate_pixels_or_scene',
        'test_death_requires_full_text_positive_empty_shapes_and_independent_hud',
        'test_full_death_prompt_and_three_depleted_shapes_are_positive',
        'test_invalid_rasters_and_flags_clear_all_permission_fields',
        'test_maximality_halo_body_and_multiple_bars_fail_closed',
        'test_old_death_veto_support_survives_without_new_ninety_percent_coverage',
        'test_one_two_three_whole_actor_markers_qualify_only_the_observed_direction',
        'test_restart_rejects_partial_colored_flooded_outside_and_present_death',
        'test_restart_scan_is_opt_in_unique_full_word_and_uses_its_actual_box',
        'test_visible_death_text_vetoes_restart_without_a_complete_death_certificate',
    }), True),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test072-passage072', frozenset({
        'test_acknowledged_restart_proves_new_gold_level_before_normal_shop',
        'test_acknowledged_unknown_visual_motion_never_becomes_another_exploration_step',
        'test_cancel_foreground_and_owner_stop_every_exploration_stage',
        'test_final_inspection_discards_old_prefix_unstable_and_overlapping_frames',
        'test_final_vantage_requires_independent_clear_before_restart',
        'test_first_skip_pause_new_gold_starts_walk_once_at_real_device_uptime',
        'test_gold_clear_passage_moves_on_observed_floor_instead_of_restarting',
        'test_gold_reveal_retires_unsent_exploration_before_new_shop_ticket',
        'test_goods_item_and_protection_hold_at_every_exploration_stage',
        'test_moved_gold_reveal_uses_normal_shop_without_restart',
        'test_multiple_fixed_mouths_are_retained_until_both_independent_inspections',
        'test_new_gold_revokes_skip_and_started_pause_holds_candidate',
        'test_new_shop_ticket_requires_hud_at_or_after_independent_geometry_proof',
        'test_one_native_session_restarts_searches_enters_and_completes_only_on_goods',
        'test_partial_or_protected_after_inspection_revokes_pause_and_restart_authority',
        'test_pause_ui_gold_unknown_is_not_uncertain_floor_and_can_restart',
        'test_restart_never_extends_original_walk_equality_deadline',
        'test_restarted_level_retune_and_initial_recovery_use_local_zero',
        'test_shadowed_outer_goal_waits_for_observed_floor_and_never_steps_unknown',
        'test_uncertain_floor_gold_evidence_revokes_local_completion_and_skip',
        'test_unknown_sent_exploration_and_restart_cannot_issue_or_reset',
        'test_walked_restart_uses_endpoint_fingerprint_and_level_local_calibration',
    }), True),
    ('tests.test_native_unlocalized_passage092', 'NativeUnlocalizedPassage092Tests', 'test092-unlocalized_passage092', frozenset({
        'test_first_positive_hint_survives_later_clear_and_local_goal_without_restart',
        'test_gold_stationary_proof_keeps_unsent_ticket_timing_and_credit',
        'test_hint_without_a_supported_mouth_or_safe_surface_never_authorizes_input',
        'test_independent_pair_rejects_crossing_and_changing_hint_classification',
        'test_observed_gold_handoff_releases_the_local_passage_for_shop_navigation',
        'test_positive_clipped_gold_approaches_only_an_independently_supported_passage',
        'test_positive_mode_preserves_cancellation_unknown_ack_and_original_budgets',
    }), True),
    ('tests.test_native_motion_cadence', 'NativeMotionCadenceTests', 'test-native-motion-cadence', frozenset({
        'test_adjacent_unknown_frames_do_not_exhaust_attempts_before_full_period_move',
        'test_eight_scheduled_unknowns_stop_without_ninth_comparison_or_input',
        'test_first_complete_move_is_immediate_without_cadence_delay',
        'test_goods_on_a_skipped_retry_still_latch_and_never_send_another_direction',
        'test_tenth_boundary_uses_capture_start_and_skips_even_a_complete_frame',
        'test_third_comparison_uses_tenth_spacing_then_confirms',
        'test_tween_and_unknown_share_the_same_settling_schedule',
        'test_visual_expiry_is_checked_before_a_retry_would_be_skipped',
    }), True),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test101-full_framing101', frozenset({
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
    ('tests.test_native_full_wait108', 'NativeFullWait108Tests', 'test108-full_wait108', frozenset({
        'test_invalid_stage_two_revokes_phase_preparation_and_proof_without_rebinding',
        'test_known_motion_or_changed_door_permanently_refuses_later_anchor_zero',
        'test_material_or_raw_unknown_waits_then_direct_anchor_zero_creates_a_new_current_model',
        'test_new_goods_gold_protection_and_nonfull_scenes_never_become_wait_credit',
        'test_reserved_stage_three_does_not_gain_a_wait_or_resend',
        'test_two_later_zero_frames_cannot_bridge_unknown_from_the_fixed_anchor',
        'test_wait_original_deadline_expires_with_no_further_capture_or_only_prefix_discards',
    }), True),
    ('tests.test_native_open_full108', 'NativeOpenFull108Tests', 'test108-open_full108', frozenset({
        'test_a_second_unknown_does_not_restore_the_one_step_credit',
        'test_direct_opening_full_unknown_waits_for_independent_zero_then_enters_once',
        'test_new_candidate_after_actual_entry_is_held_without_restarting',
        'test_old_unknown_entry_history_does_not_borrow_the_direct_opening_geometry',
        'test_opening_bracket_positive_floor_and_exact_projection_are_required',
        'test_source_prefix_deadline_cancel_and_unknown_input_do_not_gain_new_authority',
        'test_target_candidate_upper_bound_and_strong_word_precede_new_entry',
    }), True),
    ('tests.test_native_open_edge109', 'NativeOpenEdge109Tests', 'test109-open_edge109', frozenset({
        'test_direct_opening_keeps_visible_outer_domain_and_enters_on_new_proof',
        'test_edge_entry_target_is_held_and_second_unknown_never_repeats_move',
        'test_edge_never_resends_an_unknown_sent_input',
        'test_edge_requires_fresh_current_prefix_and_original_deadline',
        'test_icon_core_and_every_visible_search_pixel_must_remain_central',
        'test_old_unknown_entry_history_does_not_inherit_direct_opening_edge_domain',
        'test_target_upper_bound_or_name_priority_does_not_gain_edge_permission',
    }), True),
    ('tests.test_native_opened_fade100', 'NativeOpenedFade100Tests', 'test100-opened_fade100', frozenset({
        'test_cycle_remote_bracketed_door_to_gold_keeps_fresh_frozen_entry',
        'test_legacy_profile_does_not_gain_remote_door_relabel_permission',
        'test_nearby_material_or_old_gold_item_loss_are_not_remote_permission',
        'test_other_direction_opening_does_not_authorize_this_entry',
        'test_prefix_deadline_and_cancel_do_not_create_new_entry_authority',
        'test_remote_relabel_requires_observed_gold_bracket_and_no_protection',
        'test_remote_relabel_requires_real_same_direction_opening',
    }), True),
    ('tests.test_native_opened_entry093', 'NativeOpenedEntry093Tests', 'test093-opened_entry093', frozenset({
        'test_expired_partial_entry_reacquires_independent_future_permission',
        'test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative',
        'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
        'test_original_ticket_windows_epochs_and_actual_begin_boundaries_are_frozen',
        'test_projected_top_goods_growth_and_shrink_use_latest_separate_ticket',
        'test_projection_surface_gold_and_motion_counterexamples_reject_revalidation',
    }), True),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test097-partial_entry097', frozenset({
        'test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit',
        'test_nearby_or_protected_material_and_other_stone_destinations_are_not_quiet',
        'test_new_ticket_keeps_its_frozen_bounds_and_completed_opening_id_does_not_revive',
        'test_original_prefix_continuation_horizon_and_cancel_remain_required',
        'test_partial_relation_still_requires_same_decision_and_independent_strict_zero',
        'test_remote_stone_to_dirt_keeps_observation_credit',
        'test_shield_permission_requires_actual_same_direction_opening_and_unchanged_gold',
    }), True),
    ('tests.test_native_icon066', 'NativeIcon066Tests', 'test066-icon066', frozenset({
        'test_displaced_bars_remain_rejected_at_the_fixed_hud_location',
        'test_fragmented_icon_does_not_replace_other_hud_or_menu_guards',
        'test_fragmented_icon_keeps_original_intensity_boundary',
        'test_fragmented_two_bar_icon_with_short_label_is_a_floor',
        'test_missing_one_bar_white_region_and_short_glyphs_are_not_floor',
        'test_original_bright_bars_and_long_opening_path_still_classify_floor',
    }), True),
    ('tests.test_native_icon084', 'NativeIcon084Tests', 'test084-icon084', frozenset({
        'test_nine_pixel_bar_fragments_retain_full_reference_floor',
        'test_nine_pixel_path_keeps_hud_menu_and_buffer_guards',
        'test_nine_pixel_path_keeps_intensity_neutrality_and_fixed_roi',
        'test_nine_pixel_path_rejects_missing_bars_white_and_short_glyphs',
        'test_public_rgba_goods_after_move_ack_latches_and_confirms_pause',
    }), True),
)
REQUIRED_NEW_SCOPES = frozenset({'tests.test_native_irregular110', 'tests.test_native_passage_ack110', 'tests.test_native_full_data110', 'tests.test_native_irregular_producer110', 'tests.test_native_diagonal_entry110', 'tests.test_native_rect_icon110'})
CORE_MODULES = (*shared.CORE_MODULES, 'tests.test_native_passage_ack110', 'tests.test_native_full_data110',
    'tests.test_native_diagonal_entry110', 'tests.test_native_rect_icon110',
    'tests.test_native_irregular110', 'tests.test_native_irregular_producer110',
    'tests.test_native_unlocalized_passage092', 'tests.test_native_motion_cadence',
    'tests.test_native_icon066', 'tests.test_native_icon084')
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
PRODUCT_PATHS = ('necroprobe/test110.py', 'test_110.sh', 'necroprobe/irregular.py',
    'necroprobe/native_cycle.py', 'necroprobe/cycle_publication.py', 'necroprobe/campaign099.py',
    'necroprobe/trial_evidence099.py', 'necroprobe/test099.py', 'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/ngg2.patch')
LEGACY_FIXTURE_EXCEPTION = None
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,*shared.PRODUCT_PATHS,*PRESERVED_LOCAL_PYTHON,
    'patches/loopctrl/run_test107_host.py','patches/loopctrl/test_device_ci107.py',
    'patches/loopctrl/run_test108_host.py','patches/loopctrl/test_device_ci108.py',
    'patches/loopctrl/run_test109_host.py','patches/loopctrl/test_device_ci109.py',
    'tools/ring_native/generate_non_target094.py',
    'necroprobe/closed_container_features105.json','tools/ring_native/generate_closed105.py',
    *(name.replace('.', '/')+'.py' for name in shared.CORE_MODULES))
RUNTIME_PROOF_POLICY = 'selected_current_runtime_callbacks_required'
BASELINE_RUNTIME_SHA256 = '42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8'
BASELINE_CONTROLLER_SHA256 = 'fc5ebd16b18a153b92130f395eaf164498903be3362f949a833666860f47e2b2'
EXPECTED_NATIVE_ADDITIONS = frozenset()
APPROVED_CHANGED_REPOSITORY = frozenset({
    'necroprobe/native_cycle.py', 'necroprobe/cycle_publication.py', 'necroprobe/campaign099.py',
    'necroprobe/trial_evidence099.py', 'necroprobe/test099.py', 'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/ngg2_runtime_fakes.swift', 'patches/loopctrl/ngg2_cycle_runtime_tests.swift',
})

APPROVED_CHANGED_FIXTURE_SHA256 = {'patches/loopctrl/ngg2_runtime_fakes.swift': {'baseline_sha256': '447d3b7bc53dce30203b341e9e045edd11f6fdd632950757e8f191a17d9786cd', 'current_sha256': '2ff67987e157314eef4c7ad551d9c48021a0a5caa33051d463b80c37b24465bb'}, 'patches/loopctrl/ngg2_cycle_runtime_tests.swift': {'baseline_sha256': '83ade69b598e2e96ffa47c285c7900884b5dac33dcf610fccee595032e648318', 'current_sha256': '0bc6aa10ae2f1905da95a08066d07c5f7d1cf02b851eb4813f2985ebb38bcea4'}}
IRREGULAR_PROTOCOL_MODULE = 'necroprobe.irregular'
CURRENT_MAC_CASES = ('profile', 'retention', 'candidate', 'prefix', 'negative', 'death_lifecycle', 'death_partial_floor', 'death_later_goods', 'death_third_menu', 'death_unknown_menu', 'death_unknown_continue', 'death_pin24', 'death_cancel_pin24', 'death_cancel_continue', 'death_cancel_restart', 'death_owner_checkpoint', 'death_late_checkpoint', 'death_storage_checkpoint', 'death_recovery_lifecycle', 'death_decode_park', 'death_outcome_storage', 'invalid_companion', 'prompt_only', 'pending_candidate', 'pending_invalid', 'pending_unknown', 'pending_negative', 'enemy_retention', 'recovery_unknown_profile')
RUNTIME_SCOPE_FINALIZED = True

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO110_') for name in os.environ):
        raise ValueError('TEST110 sealed fixture overrides are forbidden')


def ensure_scope():
    if (not SCOPE_FINALIZED or not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES
            or IRREGULAR_PROTOCOL_MODULE is None
            or not EXPECTED_NATIVE_CHANGES or not CASES or not REQUIRED_NEW_SCOPES):
        raise ValueError('TEST110 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST110 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST110 new focused scopes are missing')


def native_delta(before,current,allowed,added=None):
    allowed=set(allowed);added=set(EXPECTED_NATIVE_ADDITIONS if added is None else added)
    if not allowed or set(before)-set(current) or set(current)-set(before)!=added:
        raise ValueError('TEST110 native addition/removal scope differs')
    changed={path for path in current if before.get(path)!=current[path]}
    if changed!=allowed or not added<=changed:
        raise ValueError('TEST110 exact native changed-source set differs')
    return changed

def approved_patch_identity(current,original,manifest,before):
    if (sha(current)!=manifest['patch_sha256'] or sha(original)!=before['patch_sha256']
            or current==original):
        raise ValueError('TEST110 approved G2 patch/manifest source differs')
    return sha(current)

def preserved_fixture_identity(path, current, original):
    """Preserve every old byte except a separately approved, source-bound method."""
    exception=LEGACY_FIXTURE_EXCEPTION
    if exception is None or path!=exception['path']:
        return retained_identity(current,original)
    if sha(original)!=exception['baseline_sha256'] or sha(current)!=exception['approved_sha256']:
        raise ValueError('TEST110 unreviewed legacy fixture revision')
    trees=[ast.parse(raw.decode()) for raw in (original,current)]
    classes=[next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==exception['klass']) for tree in trees]
    methods=[[n for n in klass.body if isinstance(n,ast.FunctionDef)] for klass in classes]
    if [n.name for n in methods[0]]!=[n.name for n in methods[1]]:
        raise ValueError('TEST110 legacy method markers changed')
    selected=[next(n for n in group if n.name==exception['method']) for group in methods]
    old,new=selected
    if old.decorator_list or new.decorator_list or ast.dump(old.args)!=ast.dump(new.args):
        raise ValueError('TEST110 legacy method interface changed')
    old_lines,new_lines=[raw.decode().splitlines(keepends=True) for raw in (original,current)]
    if old_lines[:old.lineno-1]!=new_lines[:new.lineno-1] or old_lines[old.end_lineno:]!=new_lines[new.end_lineno:]:
        raise ValueError('TEST110 bytes outside the approved legacy method changed')
    other=[[ast.dump(n,include_attributes=False) for n in group if n.name!=exception['method']] for group in methods]
    if other[0]!=other[1]:
        raise ValueError('TEST110 other legacy methods changed')
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

def runtime_source_identity(before,current):
    if not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST110 current Runtime callback/source scope is pending')
    runtime='LoopCtrlUITests/NG2Runtime.swift'
    if (before.get(runtime)!=BASELINE_RUNTIME_SHA256 or not isinstance(current.get(runtime), str)
            or len(current[runtime]) != 64 or any(c not in '0123456789abcdef' for c in current[runtime])
            or before[runtime]==current[runtime]):
        raise ValueError('TEST110 current changed Runtime source identity differs')
    return dict(policy=RUNTIME_PROOF_POLICY,source_reference=NATIVE_BASELINE,
        baseline_runtime_sha256=before[runtime],current_runtime_sha256=current[runtime],
        current_controller_sha256=current['LoopCtrlUITests/NG2Controller.c'],
        executed_in_host_selector=False,current_mac_execution_required=True,
        expected_current_mac_cases=list(CURRENT_MAC_CASES),
        limitation='Source binding only in this host report; actual selected Mac callback results must separately match the same CODE/IPA sources.')

def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest = json.loads(pinned_bytes(driver, 'patches/loopctrl/ngg2-manifest.json', code))
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    if len(old) != 36 or len(current) != 36:
        raise ValueError('baseline native inventory is not 36')
    changed = native_delta(old, current, EXPECTED_NATIVE_CHANGES)
    approved_patch_identity(pinned_bytes(driver,'patches/loopctrl/ngg2.patch',code),
        git(driver,'show',NATIVE_BASELINE+':patches/loopctrl/ngg2.patch'),manifest,before)
    expected_meta = {'api_version':'1.98.16-ngg2', 'client_capability':'necrogold_native_v15',
                     'cycle_capability':'necrogold_native_cycle_v1', 'cycle_profile':'normal-1-1-cycle-v1',
                     'compiler_profile_version':3, 'irregular_capability':'necrogold_native_irregular_v1',
                     'irregular_profile':'normal-1-1-irregular-v1'}
    if any(manifest.get(key) != value for key, value in expected_meta.items()):
        raise ValueError('native API/profile/compiler identity changed')
    if (sealed['api_version'],sealed['client_capability']) != ('1.98.16-ngg2','necrogold_native_v15'):
        raise ValueError('installed native API changed')
    preserved = {}
    paths = list(PRESERVED_REPOSITORY)
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('110')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('110')]
    paths += ['patches/loopctrl/run_test109_host.py', 'patches/loopctrl/test_device_ci109.py']
    paths += [p.decode() for p in git(driver,'ls-tree','-r','--name-only','-z',NATIVE_BASELINE,'legacy/r12').split(b'\0') if p]
    if sum(path.startswith('legacy/r12/') for path in paths) != 40:
        raise ValueError('R12 source inventory changed')
    for path in dict.fromkeys(paths):
        if path in APPROVED_CHANGED_REPOSITORY: continue
        preserved[path] = preserved_fixture_identity(path,pinned_bytes(driver,path,code),git(driver,'show',NATIVE_BASELINE+':'+path))
    for path, expected in APPROVED_CHANGED_FIXTURE_SHA256.items():
        if (sha(git(driver,'show',NATIVE_BASELINE+':'+path))!=expected['baseline_sha256']
                or sha(pinned_bytes(driver,path,code))!=expected['current_sha256']):
            raise ValueError('TEST110 approved shared fixture source differs: '+path)
    changed_repository = {}
    for path in sorted(APPROVED_CHANGED_REPOSITORY):
        raw = pinned_bytes(driver,path,code)
        if raw == git(driver,'show',NATIVE_BASELINE+':'+path):
            raise ValueError('approved changed client source did not change: '+path)
        changed_repository[path] = sha(raw)
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101','necroprobe.test102','necroprobe.test103','necroprobe.test104','necroprobe.test105','necroprobe.test106','necroprobe.test107','necroprobe.test108','necroprobe.test109','necroprobe.irregular','necroprobe.test110'):
        module = importlib.import_module(module_name)
        if Path(module.__file__).resolve() != driver/(module_name.replace('.','/')+'.py'):
            raise ValueError('client import escaped pinned driver: '+module_name)
    client = importlib.import_module('necroprobe.native_cycle')
    if (client.REVISION,client.API_VERSION,client.CAPABILITY,client.PROFILE) != (
            'native-cycle-v1','1.98.16-ngg2','necrogold_native_cycle_v1','normal-1-1-cycle-v1'):
        raise ValueError('native cycle protocol identity changed')
    irregular = client.IRREGULAR_PROTOCOL
    if (irregular.revision, irregular.profile, irregular.schema, irregular.capability, irregular.query) != (
            'native-irregular-v1','normal-1-1-irregular-v1','ngg2-irregular-cycle-v1',
            'necrogold_native_irregular_v1','necro_native_irregular'):
        raise ValueError('explicit irregular protocol identity changed')
    fixture_names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES))))
    fixture_paths = [name.replace('.', '/')+'.py' for name in fixture_names]
    fixture_paths += ['tests/test_native_ring094.py', *DEPENDENCY_FIXTURES,
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py', 'patches/loopctrl/run_test102_host.py', 'patches/loopctrl/run_test103_host.py', 'patches/loopctrl/run_test104_host.py', 'patches/loopctrl/run_test105_host.py', 'patches/loopctrl/run_test106_host.py', 'patches/loopctrl/run_test107_host.py', 'patches/loopctrl/run_test108_host.py', 'patches/loopctrl/run_test109_host.py', 'patches/loopctrl/run_test110_host.py',
                      'patches/loopctrl/test_device_ci110.py', 'patches/loopctrl/run_test110_host.py',
                      'patches/loopctrl/run_test110_python39.py', 'patches/loopctrl/check_runtime110.py',
                      'patches/loopctrl/ngg2_runtime110_tests.swift', 'patches/loopctrl/ngg2_runtime110_fixture.c',
                      'patches/loopctrl/ngg2_runtime_irregular110_tests.swift',
                      'patches/loopctrl/ngg2_runtime_fakes.swift', 'patches/loopctrl/ngg2_cycle_runtime_tests.swift',
                      'patches/loopctrl/check_cycle_spool110.py', 'patches/loopctrl/ngg2_cycle_spool110_tests.swift']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        runtime_proof_policy=runtime_source_identity(old,current),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,changed_repository_source_sha256=changed_repository,repository_native_source_sha256=repository,
        legacy_fixture_exception=LEGACY_FIXTURE_EXCEPTION,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        direct_c_compiler_binding='Finalized selected fixtures compile exact source bound to the installed native seal. Compilation scope is frozen with the authored CASES; no original-image Ring replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test110-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test110-nav086-current-') as temporary:
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
            raise ValueError('TEST110 read-only companion ABI changed')
        irregular=importlib.import_module('tests.test_native_irregular110')
        irregular_abi=dict(Observation=ctypes.sizeof(irregular.Observation),Status=ctypes.sizeof(irregular.Irregular))
        if irregular_abi != dict(Observation=288,Status=176):
            raise ValueError('TEST110 separate opt-in companion ABI changed')
        evidence=dict(scope='TEST110 selected actual-failure and opt-in irregular native contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,irregular_abi_bytes=irregular_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'Historical086/091 current eight-source snapshots are created only if an explicit related scope requires them',
                     'old095/096/097/098/099/100/101/102/103/104/105/106/107 complete host suites and Runtime/Mac callbacks; current selected Runtime110/Spool110 execution is required separately',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci110')
        run_scope('test110-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection110Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test110-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST110 selected native contracts against exact sealed IPA sources; selected Mac Runtime callback proof is required separately and phone acceptance is not run')


if __name__=='__main__':main()
