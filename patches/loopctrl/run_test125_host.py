"""TEST125 exact source and boundary selection; pending scopes fail closed."""
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
_spec = importlib.util.spec_from_file_location('test125_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = 'ac6edc8355fc6db82ffa65066dfbd089527a90d6'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
# Final author methods and the root native source seal are fixed for this scope.
# Native37 has Controller/RPC changes, 35 retained sources and no additions; iPhone acceptance is separate.
EXPECTED_SELECTED_METHOD_COUNT = 132
EXPECTED_NATIVE_METHOD_COUNT = 104
EXPECTED_CORE_MODULE_COUNT = 53
PENDING_SCOPE_ITEMS = ()
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift','LoopCtrlUITests/NG2Controller.c'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset(('.github/workflows/loopctrl-geometry.yml',
 'necroprobe/campaign116.py',
 'patches/loopctrl/apply_ngg2.py',
 'patches/loopctrl/ngg2-manifest.json',
 'patches/loopctrl/ngg2.patch',
 'patches/loopctrl/ngg2/NG2Controller.c',
 'patches/loopctrl/verify_package.py',
 'tests/test_continuous_client117.py',
 'tests/test_continuous_client118.py',
 'tests/test_continuous_client119.py',
 'tests/test_continuous_client120.py',
 'tests/test_continuous_client121.py',
 'tests/test_continuous_client122.py',
 'tests/test_continuous_client123.py',
 'tests/test_continuous_client124.py'))
# Final author changed/new inventories and source execution flags match the verified native seal.
NEW_PATHS = frozenset(('necroprobe/test125.py',
 'patches/loopctrl/run_test125_host.py',
 'patches/loopctrl/run_test125_python39.py',
 'patches/loopctrl/test_device_ci125.py',
 'test_125.sh',
 'tests/test_continuous_client125.py',
 'tests/test_native_partial_continuation125.py',
 'tests/test_native_upper_observation125.py',
 'tests/test_native_upper_postunit_material125.py'))
# No old137-method scope is inherited. The final author AST explicitly selects 104 native methods.
CASES = (
    ('tests.test_native_partial_continuation125', 'NativePartialContinuation125Tests', 'test125-native-NativePartialContinuation125Tests', frozenset({
        'test_both_relations_share_observe_search_reserved_and_begin',
        'test_contraction_keeps_support_lower_goods_masks_and_material_boundaries',
        'test_empty_up_framing_remote_unknown_floor_keeps_original_authority',
        'test_normal_unknown_independent_up_unit_and_new_normal_negative_reach_restart',
        'test_release_prefix_candidate_word_deadline_and_owner_still_bound_both',
        'test_remote_permission_does_not_add_unknown_dirt_stone_or_local_floor',
        'test_remote_revealed_floor_is_shared_with_clean_horizontal_partial',
        'test_runtime_profile_preserves_reserved_ticket_and_earned_zero_at_begin',
        'test_supported_contraction_uses_observed_rail_not_the_recorded_column',
        'test_supported_top_gold_contraction_keeps_larger_original_potential',
    }), True),
    ('tests.test_native_upper_observation125', 'NativeUpperObservation125Tests', 'test125-native-NativeUpperObservation125Tests', frozenset({
        'test_earned_H1_rebound_weak_probe_can_keep_observation_without_NEG_or_MOVE',
        'test_malformed_or_positive_probe_never_grants_observation',
        'test_new_current_and_normal_unit_are_still_required_for_H2_then_DOWN',
        'test_normal_producer_packet_reaches_the_earned_same_consumer_without_edits',
        'test_old_strict_exact_packet_is_preserved',
        'test_wrong_job_capture_prefix_cancel_and_late_result_do_not_reuse_probe',
    }), True),
    ('tests.test_native_upper_postunit_material125', 'NativeUpperPostunitMaterial125Tests', 'test125-native-NativeUpperPostunitMaterial125Tests', frozenset({
        'test_actual_H1_known_far_palette_keeps_job_and_earns_independent_current',
        'test_all_six_known_palette_pairs_and_mirror_keep_the_same_job',
        'test_completed_H2_then_DOWN_keep_their_own_sources_until_declared_FULL',
        'test_cross_product_wall_protection_and_unproved_motion_do_not_gain_static_rights',
        'test_expired_parent_cannot_gain_current_or_ticket',
        'test_reserved_H2_begin_revalidates_old_unit_then_only_normal_H2_rebinds',
        'test_started_or_unknown_new_input_never_becomes_the_previous_unit',
        'test_unknown_change_still_requires_a_new_data_job',
    }), True),
    ('tests.test_native_partial_begin120', 'NativePartialBegin120Tests', 'test125-related-NativePartialBegin120Tests', frozenset({
        'test_candidate_job_owner_cancel_and_original_deadline_preempt_begin',
        'test_each_identity_full_scene_and_epoch_mismatch_uses_fallback_or_refuses',
        'test_new_static_or_nonzero_observation_cannot_use_the_previous_fact',
        'test_reserved_partial_new_current_reuses_zero_without_changing_the_move',
        'test_stale_id_is_inert_true_begin_consumes_and_post_getter_does_not_recalculate',
        'test_unproved_or_discarded_current_keeps_the_old_normal_motion',
    }), False),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test125-related-NativePartialEntry097Tests', frozenset({
        'test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit',
        'test_nearby_or_protected_material_and_other_stone_destinations_are_not_quiet',
        'test_new_ticket_keeps_its_frozen_bounds_and_completed_opening_id_does_not_revive',
        'test_original_prefix_continuation_horizon_and_cancel_remain_required',
        'test_partial_relation_still_requires_same_decision_and_independent_strict_zero',
        'test_remote_stone_to_dirt_keeps_observation_credit',
        'test_shield_permission_requires_actual_same_direction_opening_and_unchanged_gold',
    }), False),
    ('tests.test_native_partial_framing097', 'NativePartialFraming097Tests', 'test125-related-NativePartialFraming097Tests', frozenset({
        'test_empty_unknown_keeps_result_and_waits_for_independent_up_framing',
        'test_exactly_one_move_requires_new_assessment_and_cannot_reuse_old_ticket',
        'test_framing_requires_actual_up_opening_and_correct_result_domain',
        'test_hypothetical_fringe_item_bounds_and_new_hud_occlusion_are_conservative',
        'test_independent_frame_needs_original_item_protection_choice_and_zero',
        'test_new_full_observation_before_framing_move_gets_new_normal_job',
        'test_original_horizon_cancel_and_foreground_guards_never_renew_framing',
        'test_same_or_pre_release_frame_wrong_prefix_and_unstable_cannot_release_credit',
        'test_top_item_and_protection_are_positive_complete_footprint_witnesses',
    }), False),
    ('tests.test_native_partial_refresh104', 'NativePartialRefresh104Tests', 'test125-related-NativePartialRefresh104Tests', frozenset({
        'test_far_floor_to_dirt_rebinds_observe_more_before_fresh_result_and_new_static',
        'test_far_refresh_does_not_consume_or_restore_old_exposed_item_once_allowance',
        'test_left_opening_two_real_left_moves_then_down_uses_current_normal_jobs',
        'test_new_candidate_target_or_unsafe_unknown_holds_and_pending_source_never_refreshes',
        'test_new_far_gold_and_material_refresh_withdraw_credit_and_reserved_ticket',
        'test_refresh_rejects_lost_gold_item_protection_near_material_and_nonzero_motion',
        'test_refresh_requires_fresh_stable_prefix_original_parent_and_control_owner',
        'test_repeated_same_prefix_refresh_keeps_first_parent_and_requires_each_new_result',
    }), False),
    ('tests.test_native_partial_remote109', 'NativePartialRemote109Tests', 'test125-related-NativePartialRemote109Tests', frozenset({
        'test_actual_opening_exact_mask_and_binary_safe_result_are_required',
        'test_each_independent_outer_wall_cell_and_horizontal_opening_are_required',
        'test_nearby_material_and_each_protected_role_cannot_use_remote_palette',
        'test_original_deadline_and_cancel_bound_remote_palette_credit',
        'test_remote_palette_keeps_classified_anchor_then_future_entry_ack',
        'test_reserved_palette_observation_keeps_original_ticket_and_deadline',
        'test_target_candidate_or_invalid_frame_never_create_observation_credit',
        'test_unknown_intermediate_pair_never_bridges_the_frozen_motion_proof',
    }), False),
    ('tests.test_native_partial_roles107', 'NativePartialRoles107Tests', 'test125-related-NativePartialRoles107Tests', frozenset({
        'test_growth_over_supported_top_gold_composes_with_far_palette_before_new_job_and_move',
        'test_mixed_refresh_real_up_and_current_normal_producer_reach_durable_restart',
        'test_new_job_target_candidate_and_missing_independent_zero_hold',
        'test_remote_protected_non_item_top_exposure_reclassifies_once_without_old_credit',
        'test_role_support_geometry_authority_and_original_deadline_are_required',
        'test_supported_roles_translate_to_the_other_observed_top_columns',
        'test_top_alias_reduction_and_old_shielded_palette_share_one_static_proof',
    }), False),
    ('tests.test_native_partial_top_wall123', 'NativePartialTopWall123Tests', 'test125-related-NativePartialTopWall123Tests', frozenset({
        'test_actual_commit_parent_before_equal_after_is_independent_of_capture_analysis',
        'test_both_rails_bind_new_source_with_frozen_parent_and_no_move_credit',
        'test_current_metadata_release_source_age_and_owner_are_not_borrowed',
        'test_existing_credit_and_reserved_move_are_never_rescued_by_new_data',
        'test_immutable_hud_history_is_retained_but_old_model_slot_and_epoch_are_revoked',
        'test_new_candidate_or_unproved_current_keeps_data_and_never_resends',
        'test_new_safe_unknown_needs_independent_current_and_fit_before_up_actual_unit',
        'test_original_geometry_support_and_five_cell_crosses_remain_required',
        'test_original_phase_budget_with_new_worker100_and_current31ms_reaches_up_unit',
        'test_retained_hud_history_cannot_replace_current_freshness_prefix_or_owner',
        'test_second_projection_job_cannot_rearm_one_use_or_refund_shared_data',
    }), False),
    ('tests.test_native_upper_material122', 'NativeUpperMaterial122Tests', 'test125-related-NativeUpperMaterial122Tests', frozenset({
        'test_after_first_unit_material_keeps_the_old_postunit_bridge',
        'test_before_first_unit_stone_material_keeps_the_same_static_job',
        'test_begin_reuses_only_the_current_normal_zero_and_keeps_same_command',
        'test_changed_current_and_discarded_capture_cannot_borrow_the_old_fact',
        'test_consumed_not_sent_or_unknown_command_never_rearms_the_fact',
        'test_material_does_not_rearm_an_existing_geometry_rebound',
        'test_original_parent_and_commit_clock_still_bound_material_observation',
        'test_same_job_material_can_frame_all_five_steps_without_new_data_or_parent',
        'test_step_cross_special_tiles_masks_and_unproved_motion_never_gain_input',
    }), False),
    ('tests.test_native_upper_projection124', 'NativeUpperProjection124Tests', 'test125-related-NativeUpperProjection124Tests', frozenset({
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
    }), False),
    ('tests.test_native_upper_snapshot118', 'NativeUpperSnapshot118Tests', 'test125-related-NativeUpperSnapshot118Tests', frozenset({
        'test_feature_off_and_bad_metadata_or_positive_floor_cannot_use_the_exception',
        'test_postunit_crossing_snapshot_qualifies_each_new_job_without_renewing_cap',
        'test_same_job_result_and_bridge_rebind_do_not_rearm_early_qualification',
    }), False),
    ('patches.loopctrl.test_device_ci125', 'DeviceImplementationCapability125Tests', 'test125-capability', frozenset({
        'test_125_cannot_bypass_the_existing_124_package_binding',
        'test_current_patch_adds_125_without_replacing_118_119_120_or_121_or_122_or_123_or_124',
        'test_historical_124_manifest_gets_no_unrequested_125_field',
        'test_package_has_separate_125_field_and_unchanged_prior_API_and_profile',
        'test_resealed_mismatched_125_metadata_patch_or_rpc_is_rejected',
        'test_sealing_requires_one_real_uncommented_125_array_entry',
    }), True),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test125-package-related', frozenset({
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
# Final author AST import closure; these modules are bound but only explicit CASES execute.
CORE_MODULES = ('tests.test_beat_sync',
 'tests.test_native_beat',
 'tests.test_native_blocked067',
 'tests.test_native_bottom_shop103',
 'tests.test_native_classification111',
 'tests.test_native_closed_offer105',
 'tests.test_native_controller',
 'tests.test_native_current_view114',
 'tests.test_native_cycle094',
 'tests.test_native_cycle_binary095',
 'tests.test_native_entry_corridor102',
 'tests.test_native_entry_episode102',
 'tests.test_native_full_framing101',
 'tests.test_native_goods113',
 'tests.test_native_irregular110',
 'tests.test_native_motion067',
 'tests.test_native_motion075',
 'tests.test_native_navigation',
 'tests.test_native_observation072',
 'tests.test_native_observed_shop_controller104',
 'tests.test_native_offer_controller105',
 'tests.test_native_offer_coverage104',
 'tests.test_native_opened_entry093',
 'tests.test_native_opened_fade100',
 'tests.test_native_partial_begin120',
 'tests.test_native_partial_continuation125',
 'tests.test_native_partial_entry097',
 'tests.test_native_partial_framing097',
 'tests.test_native_partial_refresh104',
 'tests.test_native_partial_remote109',
 'tests.test_native_partial_roles107',
 'tests.test_native_partial_top_wall123',
 'tests.test_native_perception',
 'tests.test_native_recovery',
 'tests.test_native_ring094',
 'tests.test_native_ring_bank094',
 'tests.test_native_shop_coverage102',
 'tests.test_native_shop_geometry101',
 'tests.test_native_side_shop100',
 'tests.test_native_single_offer108',
 'tests.test_native_single_sign_shop103',
 'tests.test_native_static075',
 'tests.test_native_structural_cycle096',
 'tests.test_native_structural_shop096',
 'tests.test_native_upper118',
 'tests.test_native_upper_begin118',
 'tests.test_native_upper_entry112',
 'tests.test_native_upper_material122',
 'tests.test_native_upper_observation125',
 'tests.test_native_upper_postunit_material125',
 'tests.test_native_upper_projection124',
 'tests.test_native_upper_snapshot118',
 'tests.test_target_assessment087')
# TEST120 recorded the unchanged pre117 SCREEN assertion failing on119/120.
# Keep those historical exclusions; this125 scope will select its own direct methods.
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
EXTRA_FILE_CORES = {}
EXTRA_DIRECTORY_CORES = {}
MAC_CASE_GROUPS = ()
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh',
    'necroprobe/test119.py', 'test_119.sh', 'necroprobe/test120.py', 'test_120.sh',
    'necroprobe/test121.py', 'test_121.sh', 'necroprobe/test122.py', 'test_122.sh',
    'necroprobe/test123.py', 'test_123.sh', 'necroprobe/test124.py', 'test_124.sh', 'necroprobe/test125.py', 'test_125.sh')
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
    'patches/loopctrl/test_device_ci123.py',
    'patches/loopctrl/run_test124_host.py',
    'patches/loopctrl/run_test124_python39.py',
    'patches/loopctrl/test_device_ci124.py',
    'patches/loopctrl/ngg2/NG2Ring.c')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    device_fixes119_capability='necrogold_native_device_fixes119_v1',
    device_fixes120_capability='necrogold_native_device_fixes120_v1',
    device_fixes121_capability='necrogold_native_device_fixes121_v1',
    device_fixes122_capability='necrogold_native_device_fixes122_v1',
    device_fixes123_capability='necrogold_native_device_fixes123_v1',
    device_fixes124_capability='necrogold_native_device_fixes124_v1',
    device_fixes125_capability='necrogold_native_device_fixes125_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith(('NECRO_TEST', 'NECRO_NAV', 'NG2_TEST'))
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST125 sealed fixture overrides are forbidden')


def ensure_scope():
    if (not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED or PENDING_SCOPE_ITEMS
            or any(type(value) is not int or value <= 0 for value in (EXPECTED_SELECTED_METHOD_COUNT,
                EXPECTED_NATIVE_METHOD_COUNT, EXPECTED_CORE_MODULE_COUNT))):
        raise ValueError('TEST125 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES)):
        raise ValueError('TEST125 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST125 empty or duplicate selected native scope')
    if MAC_CASE_GROUPS != ():
        raise ValueError('TEST125 declares no new Runtime/Mac boundary cases')


def native_inventory(old, current):
    """Check the complete sealed inventory before any selected C tests run."""
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST125 exact native changed/added inventory differs')
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
        raise ValueError('TEST125 installed source/API/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test125_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST125 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST125 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_118.sh', 'test_119.sh', 'test_120.sh', 'test_121.sh', 'test_122.sh', 'test_123.sh', 'test_124.sh', 'test_125.sh').strip():
        raise ValueError('TEST125 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST125 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST125 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST125 preserved source changed: '+name)
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


def run_scope(name, cases, output, evidence, *, receipt_name='test125-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test125-host-scope.json', 'test125-python39-scope.json'):
        raise ValueError('TEST125 scope receipt name is not permitted')
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
        raise ValueError('TEST125 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST125 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        excluded_legacy_methods=EXCLUDED_LEGACY_METHODS,
        not_run=['old Runtime/fault/world collections: not replayed; no new Runtime boundary changed',
            'old072 two methods/seven same-baseline assertion failures: explicitly excluded/not_run, no assertion edits',
            'old076 one method/two same-baseline subassert failures: explicitly excluded/not_run; prior25 not all Green',
            'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci125')
    run_scope('test125-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection125Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST125 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test125-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST125 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
