"""TEST124 exact source and boundary selection; pending scopes fail closed."""
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
_spec = importlib.util.spec_from_file_location('test124_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = 'fd5901d84145c0dcfebfa1c60607a80f3c8f82a5'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
# Final author AST selects host137/native109/selector14 and actualPy39108.
# Root verified37-source seal: changed3/retained34/noadd; CODE pinning precedes CI execution.
EXPECTED_SELECTED_METHOD_COUNT = 137
EXPECTED_NATIVE_METHOD_COUNT = 109
EXPECTED_CORE_MODULE_COUNT = 66
PENDING_SCOPE_ITEMS = ()
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Ring.c'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset(('.github/workflows/loopctrl-geometry.yml',
 'necroprobe/campaign116.py',
 'patches/loopctrl/apply_ngg2.py',
 'patches/loopctrl/ngg2-manifest.json',
 'patches/loopctrl/ngg2.patch',
 'patches/loopctrl/ngg2/NG2Controller.c',
 'patches/loopctrl/ngg2/NG2Ring.c',
 'patches/loopctrl/verify_package.py',
 'tests/test_continuous_client117.py',
 'tests/test_continuous_client118.py',
 'tests/test_continuous_client119.py',
 'tests/test_continuous_client120.py',
 'tests/test_continuous_client121.py',
 'tests/test_continuous_client122.py',
 'tests/test_continuous_client123.py',
 'tests/test_native_full_halo_data122.py'))
# Final changed/new non-doc paths compared with the raw verified shipped123 baseline.
NEW_PATHS = frozenset(('necroprobe/test124.py',
 'patches/loopctrl/run_test124_host.py',
 'patches/loopctrl/run_test124_python39.py',
 'patches/loopctrl/test_device_ci124.py',
 'test_124.sh',
 'tests/test_continuous_client124.py',
 'tests/test_native_opened_gold_quiet124.py',
 'tests/test_native_partial_positive124.py',
 'tests/test_native_refined_data124.py',
 'tests/test_native_transferred_view124.py',
 'tests/test_native_upper_projection124.py'))
# Final five-root methods and directly related retained cuts; oldhost83 is not inherited.
CASES = (
    ('tests.test_native_opened_gold_quiet124', 'NativeOpenedGoldQuiet124Tests', 'test124-native-NativeOpenedGoldQuiet124Tests', frozenset({
        'test_accepted_wall_cannot_return_to_source_or_shift_through_any_old_quiet_path',
        'test_actual_commit_deadline_equality_and_plus_one_keep_original_window',
        'test_bad_prefix_and_unstable_image_cannot_replace_current_authority',
        'test_earned_run_eight_keeps_same_UNKNOWN_opening_ticket_and_normal_unit',
        'test_extra_material_wall_support_and_local_protection_do_not_bypass_run_eight',
        'test_goods_and_owner_cancel_preempt_the_same_ID',
        'test_started_and_unknown_synth_do_not_gain_quiet_or_resend',
        'test_supported_reveal_keeps_original_ID_without_spending_unused_budget',
    }), True),
    ('tests.test_native_upper_projection124', 'NativeUpperProjection124Tests', 'test124-native-NativeUpperProjection124Tests', frozenset({
        'test_actual_V2_H1_seven_potential_cells_wait_for_safe_current_without_losing_parent',
        'test_bad_prefix_and_unstable_current_cannot_replace_the_pending_DATA_source',
        'test_changed_next_surface_can_wait_but_never_supplies_a_MOVE',
        'test_hard_pending_world_failure_is_sticky_and_safe_result_cannot_restore_it',
        'test_independent_current_then_each_unit_rechecks_floor_and_resolves_to_FULL',
        'test_mirrored_H1_uses_the_same_bounded_potential_and_safe_worker_path',
        'test_new_potential_keeps_the_original_postunit_crossing_snapshot_bounds',
        'test_parent_checks_actual_current_commit_and_never_extends_the_cap',
        'test_started_and_unknown_H1_cannot_arm_potential_or_resend',
        'test_target_and_candidate_preempt_pending_projection_before_any_future_MOVE',
        'test_unchanged_five_cell_world_uses_only_legacy_V2_without_a_token',
        'test_unresolved_seven_cell_halo_never_grants_the_last_DOWN',
    }), True),
    ('tests.test_native_partial_positive124', 'NativePartialPositive124Tests', 'test124-native-NativePartialPositive124Tests', frozenset({
        'test_candidate_without_name_or_price_and_with_other_observed_items',
        'test_existing_row_partial_sign_and_positive_paths_take_precedence',
        'test_expiration_during_added_positive_work_cannot_restore_old_ok',
        'test_high_confidence_icon_and_price_still_grant_candidate_only',
        'test_mode_scene_and_item_eligibility_remain_narrow',
        'test_no_hit_preserves_original_unknown_and_never_grants_safe_partial',
        'test_non_ok_cancel_and_original_deadline_are_propagated',
        'test_original_hud_crossing_and_complete_kernel_envelope_are_required',
        'test_stronger_hud_maximum_does_not_hide_safe_second_best',
    }), True),
    ('tests.test_native_refined_data124', 'NativeRefinedData124Tests', 'test124-native-NativeRefinedData124Tests', frozenset({
        'test_A_only_old_prefix_unstable_and_pre_retirement_frames_do_not_replace_pair',
        'test_C_entry_time_cannot_admit_parallel_capture_before_guarded_return_tick',
        'test_gold_handoff_keeps_normal_adjacent_door_and_dirt_openings_at_zero_steps',
        'test_gold_handoff_requires_its_own_fixed_pair_and_never_rearms_issued_or_late_authority',
        'test_goods_candidate_and_cancel_revoke_DATA_before_any_future_move_or_durability',
        'test_mixed_witness_cannot_erase_protected_roles_near_floor_or_known_stone',
        'test_new_actual_gold_revokes_clear_DATA_then_independent_gold_proofs_use_normal_shop_route',
        'test_new_fit_that_misses_fifty_ms_preparation_cannot_extend_original_schedule',
        'test_new_input_cannot_credit_unit_when_capture_ends_before_P_but_actual_commit_is_late',
        'test_new_ticket_owner_foreground_lock_and_unknown_synth_keep_no_resend',
        'test_one_level_allowance_is_not_recreated_by_new_source_model_or_real_unit',
        'test_post_retirement_pair_new_fit_and_next_physical_ticket_confirm_one_normal_unit',
        'test_repeated_unknown_cannot_replace_anchor_or_renew_original_bound',
        'test_same_direction_mixed_material_retires_ticket_before_independent_DATA',
    }), True),
    ('tests.test_native_transferred_view124', 'NativeTransferredView124Tests', 'test124-native-NativeTransferredView124Tests', frozenset({
        'test_a_and_b_two_new_zeros_new_fit_unit_and_normal_negative_restart',
        'test_candidate_and_word_veto_win_before_transferred_observation',
        'test_consumed_reservation_and_changed_begin_never_issue_a_second_view',
        'test_earned_unissued_arm_keeps_same_oneview_after_current_data_unknown',
        'test_item_halo_and_local_floor_changes_reject_the_current_proof',
        'test_original_parent_and_cancel_do_not_reopen_the_transferred_view',
        'test_prepared_pause_current_data_has_no_unissued_transfer_provenance',
        'test_two_later_mutual_zeros_cannot_replace_direct_new_source_zeros',
        'test_unarmed_old_normal_qualified_view_transfers_before_current_data_bind',
    }), True),
    ('tests.test_native_current_data118', 'NativeCurrentData118Tests', 'test124-related-NativeCurrentData118Tests', frozenset({
        'test_data_downgrade_unknown_stays_held_without_observation_move',
        'test_pending_full_keeps_normal_negative_without_reviving_observation_move',
    }), False),
    ('tests.test_native_current_view114', 'NativeCurrentView114Tests', 'test124-related-NativeCurrentView114Tests', frozenset({
        'test_current_normal_job_two_direct_proofs_new_fit_then_one_up_and_normal_restart',
    }), False),
    ('tests.test_native_full_data110', 'NativeFullData110Tests', 'test124-related-NativeFullData110Tests', frozenset({
        'test_data_unknown_keeps_original_unissued_step_and_never_restores_consumed_step',
    }), False),
    ('tests.test_native_full_halo_data122', 'NativeFullHaloData122Tests', 'test124-related-NativeFullHaloData122Tests', frozenset({
        'test_exact_halo_exposure_queues_mode2_then_normal_negative_durable_restart',
        'test_legacy_published_framing_move_started_or_ack_never_becomes_new_data',
        'test_new_normal_target_wins_without_move_or_restart',
        'test_new_unknown_is_held_and_cannot_remint_current_data_or_observation_move',
    }), False),
    ('tests.test_native_observation072', 'NativeObservation072Tests', 'test124-related-NativeObservation072Tests', frozenset({
        'test_unknown_goods_observed_vantage_keeps_original_beat_for_irrelevant_drift',
    }), False),
    ('tests.test_native_open_entry077', 'NativeOpenEntry077Tests', 'test124-related-NativeOpenEntry077Tests', frozenset({
        'test_accepted_new_gold_cannot_disappear_or_shift_within_same_ticket',
        'test_no_open_ack_or_partial_entrance_permission_is_created_by_new_gold',
        'test_opened_entry_reveal_preserves_ticket_then_enters_on_original_beat',
    }), False),
    ('tests.test_native_passage115', 'NativePassageSource115Tests', 'test124-related-NativePassageSource115Tests', frozenset({
        'test_clear_passage_presend_refresh_reissues_same_physical_ticket_and_epoch',
        'test_only_one_refinement_per_physical_ticket_and_repetitions_keep_its_source',
        'test_refinement_rejects_wrong_prefix_protection_local_material_choice_and_expiry',
        'test_started_ack_or_unknown_input_never_refreshes_or_resends',
    }), False),
    ('tests.test_native_passage_source119', 'NativePassageSource119Tests', 'test124-related-NativePassageSource119Tests', frozenset({
        'test_begun_ACK_and_unknown_inputs_do_not_become_route_retries',
        'test_changed_goods_protection_next_floor_or_unproved_motion_cannot_use_wait_downgrade',
        'test_refined_unsent_route_change_waits_then_independent_proof_uses_new_physical_beat',
        'test_route_wait_repeated_unknown_proof_does_not_renew_W_or_credit',
        'test_wait_cancel_and_replacement_owner_guard_preserve_zero_additional_inputs',
        'test_wrong_prefix_or_unstable_capture_cannot_retire_or_replace_the_live_ticket',
    }), False),
    ('tests.test_native_passage_unsent076', 'NativePassageUnsent076Tests', 'test124-related-NativePassageUnsent076Tests', frozenset({
        'test_deadline_equality_in_time_failure_and_unproven_first_step_do_not_recover',
        'test_future_passage_ticket_and_stale_callbacks_never_reuse_old_authority',
        'test_late_live_passage_complete_begin_and_tick_preserve_verified_pose',
        'test_passage_recovery_never_extends_proof_walk_or_session_budgets',
        'test_repeated_passage_misses_keep_one_original_episode_and_deadline',
        'test_started_unknown_authority_and_changed_evidence_cannot_gain_passage_recovery',
    }), False),
    ('tests.test_native_preinput_refresh118', 'NativePreinputRefresh118Tests', 'test124-related-NativePreinputRefresh118Tests', frozenset({
        'test_chain_and_run_budget_exhaustion_are_optional_noops',
        'test_clear_passage_same_tiles_uses_new_primary_with_original_epoch',
        'test_first_step_and_started_ACK_UNKNOWN_do_not_refresh',
        'test_once_is_keyed_by_logical_epoch_not_reissued_command_ID',
        'test_same_tiles_independent_preinput_source_reissues_same_logical_MOVE_once',
    }), False),
    ('tests.test_native_ring094', 'NativeRing094Tests', 'test124-related-NativeRing094Tests', frozenset({
        'test_fast_upper_bounds_preserve_positive_and_explicitly_qualify_pruned_scores',
        'test_only_completed_observed_partial_without_a_positive_may_continue',
        'test_partial_icon_above_hud_is_retained_when_only_price_overlaps_hud',
        'test_partial_pixels_keep_single_icon_name_even_without_a_complete_row',
        'test_partial_visible_target_is_retained_when_price_ink_is_occluded',
    }), False),
    ('tests.test_native_shop071', 'NativeShop071Tests', 'test124-related-NativeShop071Tests', frozenset({
        'test_goods_cancel_and_control_guards_preempt_preserved_entry',
        'test_original_actual_deadline_and_matching_stable_prefix_remain_required',
        'test_unknown_entry_synth_never_reuses_the_quiet_permission',
        'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker',
    }), False),
    ('tests.test_native_upper_begin118', 'NativeUpperBegin118Tests', 'test124-related-NativeUpperBegin118Tests', frozenset({
        'test_V1_retains_its_normal_begin_motion_call',
        'test_candidate_target_and_new_job_preempt_the_old_cached_command',
        'test_exact_V2_pair_reuses_normal_zero_at_begin_with_newer_current',
        'test_owner_cancel_and_original_deadline_still_revoke_begin',
    }), False),
    ('tests.test_native_upper_entry112', 'NativeUpperEntry112Tests', 'test124-related-NativeUpperEntry112Tests', frozenset({
        'test_extra_world_item_or_lost_gold_invalidates_movement_stickily',
    }), False),
    ('tests.test_native_upper_material122', 'NativeUpperMaterial122Tests', 'test124-related-NativeUpperMaterial122Tests', frozenset({
        'test_after_first_unit_material_keeps_the_old_postunit_bridge',
        'test_begin_reuses_only_the_current_normal_zero_and_keeps_same_command',
        'test_original_parent_and_commit_clock_still_bound_material_observation',
        'test_same_job_material_can_frame_all_five_steps_without_new_data_or_parent',
    }), False),
    ('tests.test_native_upper_postunit118', 'NativeUpperPostunit118Tests', 'test124-related-NativeUpperPostunit118Tests', frozenset({
        'test_a_new_postunit_ticket_never_reissues_after_publication_not_sent_or_unknown',
        'test_each_postunit_shape_preserves_the_unissued_next_beat_with_observed_need',
        'test_viable_default_and_invalid_current_proofs_do_not_spend_a_short_window',
    }), False),
    ('tests.test_native_upper_snapshot118', 'NativeUpperSnapshot118Tests', 'test124-related-NativeUpperSnapshot118Tests', frozenset({
        'test_feature_off_and_bad_metadata_or_positive_floor_cannot_use_the_exception',
        'test_postunit_crossing_snapshot_qualifies_each_new_job_without_renewing_cap',
        'test_same_job_result_and_bridge_rebind_do_not_rearm_early_qualification',
    }), False),
    ('patches.loopctrl.test_device_ci124', 'DeviceImplementationCapability124Tests', 'test124-capability', frozenset({
        'test_124_cannot_bypass_the_existing_123_package_binding',
        'test_current_patch_adds_124_without_replacing_118_119_120_or_121_or_122_or_123',
        'test_historical_123_manifest_gets_no_unrequested_124_field',
        'test_package_has_separate_124_field_and_unchanged_prior_API_and_profile',
        'test_resealed_mismatched_124_metadata_patch_or_rpc_is_rejected',
        'test_sealing_requires_one_real_uncommented_124_array_entry',
    }), True),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test124-package-related', frozenset({
        'test_changed_and_new_source_install_together',
        'test_native_cycle_requires_strict_ring_profile_three_without_changing_legacy_cap',
        'test_native_v14_package_requires_actual_api16_and_strict_profile_v2',
        'test_native_v15_evidence_package_keeps_api16_and_strict_profile_v2',
        'test_package_provenance_rejects_changed_native_source',
        'test_package_provenance_rejects_even_resealed_stale_runtime_envelope_api',
        'test_seal_pins_each_canonical_shared_source_without_repository_copies',
        'test_seal_still_rejects_empty_native_assets_despite_shared_kernel',
    }), False),
)
# Import/source binding only; execute only the explicit CASES.
# Exact66-module import closure from the final selected native fixture AST.
CORE_MODULES = ('tests.test_beat_sync',
 'tests.test_native_beat',
 'tests.test_native_blocked067',
 'tests.test_native_bottom_shop103',
 'tests.test_native_classification111',
 'tests.test_native_clear_stationary095',
 'tests.test_native_controller',
 'tests.test_native_current_data118',
 'tests.test_native_current_view114',
 'tests.test_native_cycle094',
 'tests.test_native_cycle_binary095',
 'tests.test_native_entry_corridor102',
 'tests.test_native_entry_episode102',
 'tests.test_native_full_data110',
 'tests.test_native_full_framing101',
 'tests.test_native_full_halo_data122',
 'tests.test_native_goods113',
 'tests.test_native_irregular110',
 'tests.test_native_motion067',
 'tests.test_native_motion075',
 'tests.test_native_navigation',
 'tests.test_native_observation072',
 'tests.test_native_offer_coverage104',
 'tests.test_native_open_entry077',
 'tests.test_native_opened_entry093',
 'tests.test_native_opened_fade100',
 'tests.test_native_opened_gold_quiet124',
 'tests.test_native_partial_entry097',
 'tests.test_native_partial_framing097',
 'tests.test_native_partial_positive124',
 'tests.test_native_passage072',
 'tests.test_native_passage115',
 'tests.test_native_passage_navigation072',
 'tests.test_native_passage_palette077',
 'tests.test_native_passage_source119',
 'tests.test_native_passage_unsent076',
 'tests.test_native_perception',
 'tests.test_native_plural_stationary103',
 'tests.test_native_plural_wait103',
 'tests.test_native_preinput_refresh118',
 'tests.test_native_recovery',
 'tests.test_native_refined_data124',
 'tests.test_native_ring094',
 'tests.test_native_ring_bank094',
 'tests.test_native_shop071',
 'tests.test_native_shop_coverage102',
 'tests.test_native_shop_geometry101',
 'tests.test_native_side_shop100',
 'tests.test_native_single_offer108',
 'tests.test_native_single_sign_shop103',
 'tests.test_native_singleton_stationary095',
 'tests.test_native_static075',
 'tests.test_native_stationary_texture085',
 'tests.test_native_stationary_wait076',
 'tests.test_native_stop099',
 'tests.test_native_structural_cycle096',
 'tests.test_native_structural_shop096',
 'tests.test_native_transferred_view124',
 'tests.test_native_upper118',
 'tests.test_native_upper_begin118',
 'tests.test_native_upper_entry112',
 'tests.test_native_upper_material122',
 'tests.test_native_upper_postunit118',
 'tests.test_native_upper_projection124',
 'tests.test_native_upper_snapshot118',
 'tests.test_target_assessment087')
# TEST120 recorded the unchanged pre117 SCREEN assertion failing on119/120.
# Keep that historical exclusion; this124 scope selects its own direct methods.
EXCLUDED_LEGACY_METHODS = {'tests.test_native_observation072.NativeObservation072Tests.test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket': 'TEST124 '
                                                                                                                                     'root1 '
                                                                                                                                     'original15 '
                                                                                                                                     'run '
                                                                                                                                     'has '
                                                                                                                                     'two '
                                                                                                                                     'old072 '
                                                                                                                                     'methods/seven '
                                                                                                                                     'assertion '
                                                                                                                                     'failures; '
                                                                                                                                     'exact123 '
                                                                                                                                     'baseline '
                                                                                                                                     'has '
                                                                                                                                     'the '
                                                                                                                                     'same '
                                                                                                                                     'seven. '
                                                                                                                                     'Original '
                                                                                                                                     'assertions '
                                                                                                                                     'retained, '
                                                                                                                                     'not '
                                                                                                                                     'selected/not_run; '
                                                                                                                                     'select '
                                                                                                                                     'the13 '
                                                                                                                                     'other '
                                                                                                                                     'direct '
                                                                                                                                     'methods '
                                                                                                                                     'only.',
 'tests.test_native_observation072.NativeObservation072Tests.test_current_hud_fifty_ms_preparation_and_original_budgets_remain_required': 'TEST124 '
                                                                                                                                          'root1 '
                                                                                                                                          'original15 '
                                                                                                                                          'run '
                                                                                                                                          'has '
                                                                                                                                          'two '
                                                                                                                                          'old072 '
                                                                                                                                          'methods/seven '
                                                                                                                                          'assertion '
                                                                                                                                          'failures; '
                                                                                                                                          'exact123 '
                                                                                                                                          'baseline '
                                                                                                                                          'has '
                                                                                                                                          'the '
                                                                                                                                          'same '
                                                                                                                                          'seven. '
                                                                                                                                          'Original '
                                                                                                                                          'assertions '
                                                                                                                                          'retained, '
                                                                                                                                          'not '
                                                                                                                                          'selected/not_run; '
                                                                                                                                          'select '
                                                                                                                                          'the13 '
                                                                                                                                          'other '
                                                                                                                                          'direct '
                                                                                                                                          'methods '
                                                                                                                                          'only.',
 'tests.test_native_stationary_wait076.NativeStationaryWait076Tests.test_ready_or_issued_unknown_does_not_reopen_the_same_wait': 'Prior '
                                                                                                                                 'TEST120 '
                                                                                                                                 'evidence '
                                                                                                                                 'already '
                                                                                                                                 'recorded '
                                                                                                                                 'this '
                                                                                                                                 'pre117 '
                                                                                                                                 'SCREEN '
                                                                                                                                 'expectation '
                                                                                                                                 'mismatch. '
                                                                                                                                 'TEST124 '
                                                                                                                                 'root4 '
                                                                                                                                 'prior25 '
                                                                                                                                 'had24 '
                                                                                                                                 'passed '
                                                                                                                                 'methods '
                                                                                                                                 'and '
                                                                                                                                 'this '
                                                                                                                                 'one '
                                                                                                                                 'method/two '
                                                                                                                                 'issued '
                                                                                                                                 'False/True '
                                                                                                                                 'assertion '
                                                                                                                                 'failures; '
                                                                                                                                 'exact123 '
                                                                                                                                 'has '
                                                                                                                                 'the '
                                                                                                                                 'same '
                                                                                                                                 'two. '
                                                                                                                                 'Original '
                                                                                                                                 'assertions '
                                                                                                                                 'retained, '
                                                                                                                                 'not '
                                                                                                                                 'selected/not_run. '
                                                                                                                                 'Latest '
                                                                                                                                 'frozen '
                                                                                                                                 'related '
                                                                                                                                 'scope '
                                                                                                                                 'is16, '
                                                                                                                                 'not '
                                                                                                                                 'all25 '
                                                                                                                                 'Green.'}
FILE_CORE_SOURCES = {}
EXTRA_FILE_CORES = {'tests.test_native_partial_positive124': {'RING': 'NG2Ring.c'}}
EXTRA_DIRECTORY_CORES = {'tests.test_native_controller': ('CORE',), 'tests.test_native_transferred_view124': ('CORE',)}
MAC_CASE_GROUPS = ()
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh',
    'necroprobe/test119.py', 'test_119.sh', 'necroprobe/test120.py', 'test_120.sh',
    'necroprobe/test121.py', 'test_121.sh', 'necroprobe/test122.py', 'test_122.sh',
    'necroprobe/test123.py', 'test_123.sh', 'necroprobe/test124.py', 'test_124.sh')
PRESERVED_PATHS = (*shared.UNCHANGED_CONTINUATION_PATHS,
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2Raster.swift', 'patches/loopctrl/ngg1.patch',
    'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py',
    'patches/loopctrl/ngg2/NG2Perception.c', 'patches/loopctrl/ngg2/NG2Navigation.c',
    'patches/loopctrl/run_test119_host.py', 'patches/loopctrl/run_test119_python39.py',
    'patches/loopctrl/run_test120_host.py', 'patches/loopctrl/run_test120_python39.py',
    'patches/loopctrl/run_test121_host.py', 'patches/loopctrl/run_test121_python39.py',
    'patches/loopctrl/test_device_ci121.py',
    'patches/loopctrl/run_test122_host.py', 'patches/loopctrl/run_test122_python39.py',
    'patches/loopctrl/test_device_ci122.py',
    'patches/loopctrl/ngg2/NG2Ring.h',
    'patches/loopctrl/run_test094_host.py',
    'patches/loopctrl/test_device_ci094.py',
    'patches/loopctrl/run_test095_host.py',
    'patches/loopctrl/test_device_ci095.py',
    'patches/loopctrl/run_test096_host.py',
    'patches/loopctrl/test_device_ci096.py',
    'patches/loopctrl/run_test097_host.py',
    'patches/loopctrl/test_device_ci097.py',
    'patches/loopctrl/run_test098_host.py',
    'patches/loopctrl/test_device_ci098.py',
    'patches/loopctrl/run_test099_host.py',
    'patches/loopctrl/test_device_ci099.py',
    'patches/loopctrl/run_test100_host.py',
    'patches/loopctrl/test_device_ci100.py',
    'patches/loopctrl/run_test101_host.py',
    'patches/loopctrl/test_device_ci101.py',
    'patches/loopctrl/run_test102_host.py',
    'patches/loopctrl/test_device_ci102.py',
    'patches/loopctrl/run_test103_host.py',
    'patches/loopctrl/test_device_ci103.py',
    'patches/loopctrl/run_test104_host.py',
    'patches/loopctrl/test_device_ci104.py',
    'patches/loopctrl/run_test105_host.py',
    'patches/loopctrl/test_device_ci105.py',
    'patches/loopctrl/run_test106_host.py',
    'patches/loopctrl/test_device_ci106.py',
    'patches/loopctrl/run_test107_host.py',
    'patches/loopctrl/test_device_ci107.py',
    'patches/loopctrl/run_test108_host.py',
    'patches/loopctrl/test_device_ci108.py',
    'patches/loopctrl/run_test109_host.py',
    'patches/loopctrl/test_device_ci109.py',
    'patches/loopctrl/run_test110_host.py',
    'patches/loopctrl/run_test110_python39.py',
    'patches/loopctrl/test_device_ci110.py',
    'patches/loopctrl/run_test111_host.py',
    'patches/loopctrl/run_test111_python39.py',
    'patches/loopctrl/test_device_ci111.py',
    'patches/loopctrl/run_test112_host.py',
    'patches/loopctrl/run_test112_python39.py',
    'patches/loopctrl/test_device_ci112.py',
    'patches/loopctrl/run_test113_host.py',
    'patches/loopctrl/run_test113_python39.py',
    'patches/loopctrl/test_device_ci113.py',
    'patches/loopctrl/run_test114_host.py',
    'patches/loopctrl/run_test114_python39.py',
    'patches/loopctrl/test_device_ci114.py',
    'patches/loopctrl/run_test115_host.py',
    'patches/loopctrl/run_test115_python39.py',
    'patches/loopctrl/test_device_ci115.py',
    'patches/loopctrl/run_test116_host.py',
    'patches/loopctrl/run_test116_python39.py',
    'patches/loopctrl/test_device_ci116.py',
    'patches/loopctrl/run_test117_host.py',
    'patches/loopctrl/run_test117_python39.py',
    'patches/loopctrl/test_device_ci117.py',
    'patches/loopctrl/run_test118_host.py',
    'patches/loopctrl/run_test118_python39.py',
    'patches/loopctrl/test_device_ci118.py',
    'patches/loopctrl/test_device_ci119.py',
    'patches/loopctrl/test_device_ci120.py',
    'patches/loopctrl/run_test123_host.py',
    'patches/loopctrl/run_test123_python39.py',
    'patches/loopctrl/test_device_ci123.py')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    device_fixes119_capability='necrogold_native_device_fixes119_v1',
    device_fixes120_capability='necrogold_native_device_fixes120_v1',
    device_fixes121_capability='necrogold_native_device_fixes121_v1',
    device_fixes122_capability='necrogold_native_device_fixes122_v1',
    device_fixes123_capability='necrogold_native_device_fixes123_v1',
    device_fixes124_capability='necrogold_native_device_fixes124_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith(('NECRO_TEST', 'NECRO_NAV', 'NG2_TEST'))
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST124 sealed fixture overrides are forbidden')


def ensure_scope():
    if (not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED or PENDING_SCOPE_ITEMS
            or any(type(value) is not int or value <= 0 for value in (EXPECTED_SELECTED_METHOD_COUNT,
                EXPECTED_NATIVE_METHOD_COUNT, EXPECTED_CORE_MODULE_COUNT))):
        raise ValueError('TEST124 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES)):
        raise ValueError('TEST124 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST124 empty or duplicate selected native scope')
    if MAC_CASE_GROUPS != ():
        raise ValueError('TEST124 declares no new Runtime/Mac boundary cases')


def native_inventory(old, current):
    """Check the complete sealed inventory before any selected C tests run."""
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST124 exact native changed/added inventory differs')
    return changed, added


def source_identity(driver, sealed, upstream):
    ensure_scope(); reject_fixture_overrides()
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    path = 'patches/loopctrl/ngg2-manifest.json'; raw = pinned_bytes(driver, path, code)
    manifest = json.loads(raw)
    old = manifest_sources(json.loads(git(driver, 'show', NATIVE_BASELINE+':'+path)))
    current = sealed['native_source_sha256']
    changed, added = native_inventory(old, current)
    if manifest_sources(manifest) != current or any(manifest.get(k) != v for k, v in EXPECTED_API.items()):
        raise ValueError('TEST124 installed source/API/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test124_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST124 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST124 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_118.sh', 'test_119.sh', 'test_120.sh', 'test_121.sh', 'test_122.sh', 'test_123.sh', 'test_124.sh').strip():
        raise ValueError('TEST124 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST124 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST124 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST124 preserved source changed: '+name)
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
    suites = shared.native_suites(upstream, driver)
    for name, source in FILE_CORE_SOURCES.items():
        if name in sys.modules:
            sys.modules[name].CORE = upstream/'LoopCtrlUITests'/source
            alias = sys.modules.get(name.rsplit('.', 1)[-1])
            if alias is not None:
                alias.CORE = upstream/'LoopCtrlUITests'/source
    for name, fields in EXTRA_FILE_CORES.items():
        for module_name in (name, name.rsplit('.', 1)[-1]):
            module = sys.modules.get(module_name)
            if module is not None:
                for field, source in fields.items():
                    setattr(module, field, upstream/'LoopCtrlUITests'/source)
    for name, fields in EXTRA_DIRECTORY_CORES.items():
        for module_name in (name, name.rsplit('.', 1)[-1]):
            module = sys.modules.get(module_name)
            if module is not None:
                for field in fields:
                    setattr(module, field, upstream/'LoopCtrlUITests')
    return suites


def run_scope(name, cases, output, evidence, *, receipt_name='test124-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test124-host-scope.json', 'test124-python39-scope.json'):
        raise ValueError('TEST124 scope receipt name is not permitted')
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
        raise ValueError('TEST124 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST124 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        excluded_legacy_methods=EXCLUDED_LEGACY_METHODS,
        not_run=['old Runtime/fault/world collections: not replayed; no new Runtime boundary changed',
            'old072 two methods/seven same-baseline assertion failures: explicitly excluded/not_run, no assertion edits',
            'old076 one method/two same-baseline subassert failures: explicitly excluded/not_run; prior25 not all Green',
            'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci124')
    run_scope('test124-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection124Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST124 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test124-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST124 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
