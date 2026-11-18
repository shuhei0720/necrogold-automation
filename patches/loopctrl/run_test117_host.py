"""TEST117 exact native boundary selection; unresolved author scope fails closed.

Selection/import/byte helpers are shared with TEST116.  Its Runtime 36-case
runner and spool proof are deliberately outside this source-change boundary.
"""
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
_spec = importlib.util.spec_from_file_location('test117_host_shared116', HERE/'run_test116_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases = shared.selected_cases, shared.method_cases
manifest_sources = shared.manifest_sources
NATIVE_BASELINE = 'ad32e35d22f6764e4550bc8eea65ae0ae68d2934'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({
    'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c',
    'LoopCtrlUITests/NG2Controller.h',
    'LoopCtrlUITests/NG2Core.h',
    'LoopCtrlUITests/NG2Navigation.c',
    'LoopCtrlUITests/NG2Perception.c',
    'LoopCtrlUITests/NG2Ring.c',
    'LoopCtrlUITests/NG2Ring.h',
    'LoopCtrlUITests/NG2Runtime.swift',
})
EXPECTED_NATIVE_ADDITIONS = frozenset({
    'LoopCtrlUITests/NG2ShopPriceGeometry.h',
})
EXPECTED_REPOSITORY_CHANGES = frozenset({
    '.github/workflows/loopctrl-geometry.yml',
    'AGENTS.md',
    'necroprobe/campaign116.py',
    'necroprobe/native_cycle.py',
    'necroprobe/test116.py',
    'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/check_ngg2.py',
    'patches/loopctrl/ngg2-manifest.json',
    'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/ngg2/NG2Controller.c',
    'patches/loopctrl/ngg2/NG2Controller.h',
    'patches/loopctrl/ngg2/NG2Core.h',
    'patches/loopctrl/ngg2/NG2Navigation.c',
    'patches/loopctrl/ngg2/NG2Perception.c',
    'patches/loopctrl/ngg2/NG2Ring.c',
    'patches/loopctrl/ngg2/NG2Ring.h',
    'patches/loopctrl/ngg2/NG2Runtime.swift',
    'patches/loopctrl/test_apply_ngg2.py',
    'patches/loopctrl/verify_package.py',
    'tests/test_native_closed_price106.py',
    'tests/test_native_current_view114.py',
    'tests/test_native_plural_wait103.py',
    'tests/test_native_single_offer108.py',
})
NEW_PATHS = frozenset({
    'necroprobe/test117.py',
    'patches/loopctrl/check_runtime117.py',
    'patches/loopctrl/generate_shop117_pixels.py',
    'patches/loopctrl/ngg2/NG2ShopPriceGeometry.h',
    'patches/loopctrl/ngg2_runtime117_fixture.c',
    'patches/loopctrl/ngg2_runtime117_tests.swift',
    'patches/loopctrl/run_test117_host.py',
    'patches/loopctrl/run_test117_python39.py',
    'patches/loopctrl/test_device_ci117.py',
    'test_117.sh',
    'tests/test_continuous_client117.py',
    'tests/test_initial_restart117.py',
    'tests/test_native_initial_restart_controller117.py',
    'tests/test_native_navigation117.py',
    'tests/test_native_price_geometry117.py',
    'tests/test_native_ring117.py',
    'tests/test_native_shop117.py',
    'tests/test_native_single_gold117.py',
    'tests/test_native_stationary117.py',
    'tests/test_native_stationary_qualification117.py',
    'tests/test_native_stationary_support117.py',
})
CASES = (
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test117-native-NGG2ApplyTests', frozenset({
        'test_native_v14_package_requires_actual_api16_and_strict_profile_v2',
        'test_native_v15_evidence_package_keeps_api16_and_strict_profile_v2',
        'test_package_provenance_rejects_even_resealed_stale_runtime_envelope_api',
    }), False),
    ('patches.loopctrl.test_apply_ngg2', 'RuntimeResponseSignature117Tests', 'test117-native-RuntimeResponseSignature117Tests', frozenset({
        'test_reviewed_optional_signature_keeps_the_same_actual_api_boundary',
        'test_signatures_versions_duplicates_comments_and_historical_bounds_stay_closed',
    }), True),
    ('patches.loopctrl.test_check_ngg2', 'Test061PublicSelectionTests', 'test117-native-Test061PublicSelectionTests', frozenset({
        'test_old_response_API_is_rejected_before_any_TEST061_native_compile',
    }), False),
    ('tests.test_native_closed_price106', 'NativeClosedPrice106Tests', 'test117-native-NativeClosedPrice106Tests', frozenset({
        'test_already_registered_gray_and_purple_closed_bodies_share_the_price_proof',
        'test_each_existing_shop_shape_uses_the_same_closed_price_adapter',
        'test_integer_support_boundaries_are_exact_for_both_masks_and_all_existing_identities',
        'test_observed_closed_price_and_background_variation_have_separate_positive_proof',
        'test_price_complete_unknown_lower_cell_uses_the_same_versioned_identity',
        'test_target_missing_extra_price_and_damaged_closed_identity_are_held',
        'test_version_two_closed_identity_and_actual_price_pose_cannot_be_forged',
    }), True),
    ('tests.test_native_current_view114', 'NativeCurrentView114Tests', 'test117-native-NativeCurrentView114Tests', frozenset({
        'test_begun_acknowledged_or_unknown_pause_is_never_retired_for_current_data',
        'test_candidate_from_old_or_new_normal_pixels_has_priority_over_view',
        'test_current_geometry_and_own_normal_result_need_no_relabelled_old_history',
        'test_current_normal_job_two_direct_proofs_new_fit_then_one_up_and_normal_restart',
        'test_current_unknown_motion_or_changed_material_is_sticky_and_cannot_migrate',
        'test_later_static_frame_after_reservation_preserves_the_frozen_current_ticket',
        'test_missing_positive_current_floor_projection_and_expired_parent_do_not_rebind',
        'test_one_direct_proof_and_old_fit_cannot_authorize_current_up',
        'test_only_exact_unbegun_pause_can_withdraw_before_current_bind',
        'test_post_up_unknown_never_restores_current_epoch_or_single_view',
        'test_profile_without_runtime_return_drain_fences_cannot_requalify_current_view',
        'test_two_pairwise_zeros_do_not_bridge_the_immutable_current_anchor',
    }), True),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test117-native-NativeCycle094Tests', frozenset({
        'test_ack_and_real_changed_floor_wait_for_linked_outcome_durability',
        'test_restart_begin_requires_exact_durable_intent_and_fresh_pause',
        'test_search_restart_first_visible_goods_drains_and_binds_new_level',
    }), False),
    ('tests.test_native_gold_stationary092', 'NativeGoldStationary092Tests', 'test117-native-NativeGoldStationary092Tests', frozenset({
        'test_complete_nonhud_old_terrain_gold_and_safe_floor_are_required',
        'test_known_motion_and_nonzero_surfaces_cannot_be_overwritten',
        'test_lighting_drift_with_stable_gold_confirms_only_zero',
        'test_raw_finite_zero_and_independent_texture_competition_are_required',
    }), True),
    ('tests.test_native_image_price111', 'NativeImagePrice111Tests', 'test117-native-NativeImagePrice111Tests', frozenset({
        'test_ambiguous_image_remains_candidate_despite_valid_price',
        'test_canonical_mode0_still_requires_the_target_name',
        'test_clipped_scattered_or_insufficient_own_price_keeps_candidate',
        'test_old_name_positive_survives_missing_price',
        'test_price_value_is_not_fixed_to_one_calibration_number',
        'test_same_image_without_its_price_is_retained_as_candidate',
        'test_strong_target_image_and_observed_price_needs_no_target_name',
    }), True),
    ('tests.test_native_initial_gold107', 'NativeInitialGold107Tests', 'test117-native-NativeInitialGold107Tests', frozenset({
        'test_post_restart_first_fade_gold_uses_only_latest_pair_for_its_first_move',
    }), False),
    ('tests.test_native_initial_restart_controller117', 'NativeInitialRestartController117Tests', 'test117-native-NativeInitialRestartController117Tests', frozenset({
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
    ('tests.test_native_lower_fringe100', 'NativeLowerFringe100Tests', 'test117-native-NativeLowerFringe100Tests', frozenset({
        'test_every_positive_wall_and_floor_witness_is_required',
        'test_existing_mouth_corner_and_shadow_masks_are_preserved',
        'test_fixed_world_chooser_uses_four_observed_floor_steps_then_holds_at_wall',
        'test_observed_lower_exterior_floor_retains_only_fixed_left_bit9',
        'test_short_current_floor_vantage_and_disconnected_exterior_are_required',
        'test_state_goods_gold_item_protection_and_fixed_coordinates_keep_scope',
    }), True),
    ('tests.test_native_navigation116', 'NativeCappedNeck116Tests', 'test117-native-NativeCappedNeck116Tests', frozenset({
        'test_both_observed_neck_cells_and_reachable_inboard_are_required',
        'test_cap_and_both_lateral_wall_segments_are_independent_required_evidence',
        'test_capped_observed_necks_keep_the_existing_world_bits_in_both_axes',
        'test_neck_refuses_goods_other_screens_and_observed_nonfloor_flanks',
        'test_outer_corner_cannot_replace_three_independent_room_boundary_walls',
        'test_unchanged_chooser_walks_only_known_floor_and_stops_at_the_outside',
    }), True),
    ('tests.test_native_navigation117', 'NativeOpaqueFringe117Tests', 'test117-native-NativeOpaqueFringe117Tests', frozenset({
        'test_complete_independent_room_does_not_change_the_fixed_view_or_open_wall',
        'test_each_external_floor_cap_boundary_and_roof_witness_is_required',
        'test_existing_chooser_uses_three_known_floor_steps_then_stops_at_the_wall',
        'test_observed_floor_bend_adds_only_its_fixed_left_mouth',
        'test_ui_goods_positive_gold_and_protected_cells_never_gain_authority',
    }), True),
    ('tests.test_native_offer_coverage104', 'NativeOfferCoverage104Tests', 'test117-native-NativeOfferCoverage104Tests', frozenset({
        'test_all_strip_templates_and_strong_name_keep_target_priority',
        'test_every_positive_support_floor_item_cap_and_gold_context_is_required',
        'test_legacy_wall_mutations_do_not_gain_missing_positive_price_floors',
        'test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards',
        'test_observed_price_floor_footprint_certifies_without_outside_wall_shape',
        'test_raw_caps_prices_extra_groups_and_lower_container_price_remain_observed',
        'test_state_mapping_bounds_deadline_cancel_and_legacy_modes_are_preserved',
        'test_two_real_full_faces_and_no_extra_component_remain_required',
    }), True),
    ('tests.test_native_partial116', 'NativePartial116Tests', 'test117-native-NativePartial116Tests', frozenset({
        'test_issued_but_unbegun_credit_is_retired_without_refunding_an_input',
        'test_reverse_top_projection_keeps_fixed_epoch_and_original_one_up',
        'test_reverse_top_relation_rejects_unexplained_goods_floor_gold_and_motion',
        'test_top_transition_after_unused_credit_starts_independent_data',
    }), True),
    ('tests.test_native_passage115', 'NativePassageFringe115Tests', 'test117-native-NativePassageFringe115Tests', frozenset({
        'test_fringe_needs_full_observed_support_and_positive_inside_floor',
        'test_fringe_rejects_nonclear_goods_protection_and_no_floor_vantage',
        'test_observed_floor_fringe_adds_only_upper_left_dark_mouth',
    }), True),
    ('tests.test_native_passage115', 'NativeUnlocalizedWait115Tests', 'test117-native-NativeUnlocalizedWait115Tests', frozenset({
        'test_candidate_reproof_does_not_extend_original_two_beat_wait',
        'test_independent_candidate_zero_then_blur_waits_without_input_and_reproves',
        'test_issued_but_unbegun_candidate_blur_retires_only_its_permission',
        'test_issued_candidate_ticket_cannot_begin_beyond_original_parent',
        'test_ready_before_W_can_prepare_and_begin_after_W_within_original_parent',
        'test_ready_or_issued_blur_at_W_expires_without_renewing_observation',
        'test_ready_ticket_keeps_normal_window_and_original_parent_after_W',
    }), True),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test117-native-NativePassageNavigation072Tests', frozenset({
        'test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps',
        'test_invalid_start_gold_goods_ordinary_exits_and_protection_do_not_explore',
    }), False),
    ('tests.test_native_plural_stationary103', 'NativePluralStationary103Tests', 'test117-native-NativePluralStationary103Tests', frozenset({
        'test_all_blur_finite_absolute_bound_and_all_raw_competitors',
        'test_both_scenes_near_floor_protection_gold_goods_and_invalid_reject',
        'test_exact_old_plural_stones_and_old_dirt_cannot_be_replaced',
        'test_exactly_one_cardinal_unit_phase_and_supported_unit_axis',
        'test_fixed_world_unit_lighting_phase_adds_only_zero_qualification',
        'test_noncollinear_unique_nine_placements_and_full_hud_rois',
        'test_real_translated_procedural_world_never_qualifies_zero',
        'test_world_axis_strength_regions_and_last_lead_boundaries',
    }), True),
    ('tests.test_native_plural_wait103', 'NativePluralWait103Tests', 'test117-native-NativePluralWait103Tests', frozenset({
        'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
        'test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero',
        'test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back',
        'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
        'test_plural_proof_needs_independent_stable_current_prefix_capture',
        'test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket',
    }), True),
    ('tests.test_native_price_geometry117', 'NativePriceGeometry117Tests', 'test117-native-NativePriceGeometry117Tests', frozenset({
        'test_incomplete_sprite_extra_full_face_and_invalid_alpha_are_not_complete',
        'test_price_height_baseline_missing_extra_and_body_trim_boundaries',
        'test_same_full_sign_and_three_independent_complete_price_glyphs',
    }), True),
    ('tests.test_native_restart_yield112', 'NativeRestartYield112Tests', 'test117-native-NativeRestartYield112Tests', frozenset({
        'test_optin_after_durable_restart_never_enters_another_level_with_spent_budget',
        'test_optin_initial_floor_or_other_ui_is_input_free_but_old_start_is_unchanged',
    }), False),
    ('tests.test_native_ring117', 'NativeRing117Tests', 'test117-native-NativeRing117Tests', frozenset({
        'test_closed_price_recovers_same_row_without_turning_partial_into_absence',
        'test_new_numeric_witness_rejects_field_forgery',
        'test_new_price_layout_has_generic_absence_and_its_own_numeric_bounds',
        'test_new_price_layout_requires_exact_projection_and_all_supporting_floors',
        'test_one_complete_face_with_observed_lower_entrance_certifies_three_offers',
        'test_original_partial_positive_search_outside_selected_strip_is_retained',
        'test_single_face_requires_each_observed_support_and_complete_merchandise',
        'test_three_independent_price_glyphs_do_not_require_identity_of_another_product',
    }), True),
    ('tests.test_native_shared_zero115', 'NativeSharedPassageZero115Tests', 'test117-native-NativeSharedPassageZero115Tests', frozenset({
        'test_invalid_layout_and_known_motion_keep_normal_precedence_and_full_result',
        'test_unknown_positive_reuses_two_views_and_all_original_raw_candidates',
    }), True),
    ('tests.test_native_shop117', 'NativeFullCurrentData117Tests', 'test117-native-NativeFullCurrentData117Tests', frozenset({
        'test_changed_goods_masks_player_neighborhood_walls_and_old_candidates_veto_data',
        'test_current_unknown_is_held_without_phase_proofs_or_move_credit',
        'test_finite_latest_full_data_accepts_normal_negative_in_both_callback_orders',
        'test_new_current_epoch_invalidates_negative_but_keeps_bound_positive_priority',
        'test_parent_equality_or_stale_latest_cannot_start_a_new_data_epoch',
        'test_prepared_pause_is_retired_only_while_definitely_unbegun',
    }), True),
    ('tests.test_native_shop117', 'NativePartialFootprint117Tests', 'test117-native-NativePartialFootprint117Tests', frozenset({
        'test_actual_walk_cells_unexplained_masks_and_parent_deadline_still_veto_entry',
        'test_exact_item_halo_is_not_dilated_again_over_actual_entry_destination',
        'test_remote_observed_wall_retires_old_partial_into_new_data_with_original_horizon',
    }), True),
    ('tests.test_native_shop117', 'NativeSingleLowerEntryController117Tests', 'test117-native-NativeSingleLowerEntryController117Tests', frozenset({
        'test_immutable_anchor_and_numeric_fields_are_rechecked_independently',
        'test_layout3_complete_certificate_translation_cannot_cross_central_pixel_domain',
        'test_layout3_rechecks_exact_anchor_and_each_separate_price_boundary',
        'test_ordinary_producer_certificate_reaches_durable_restart_and_next_floor',
        'test_shared_lower_price_geometry_reaches_independent_adoption_and_real_restart',
    }), True),
    ('tests.test_native_single_gold117', 'NativeSingleGold117Tests', 'test117-native-NativeSingleGold117Tests', frozenset({
        'test_independent_old_dirt_footprint_rejects_a_second_translation_even_with_unique_gold',
        'test_invalid_API_inputs_clear_separate_output_without_changing_normal_contract',
        'test_known_nonzero_Motion_or_nonzero_world_never_gets_scalar_credit',
        'test_old_landmarks_near_floor_and_all_protection_requirements_are_conjunctive',
        'test_old_single_gold_independent_dirt_adds_only_shared_local_zero',
    }), True),
    ('tests.test_native_single_offer108', 'NativeSingleOffer108Tests', 'test117-native-NativeSingleOffer108Tests', frozenset({
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
    ('tests.test_native_stationary117', 'NativeClearProof117Tests', 'test117-native-NativeClearProof117Tests', frozenset({
        'test_clear_ready_loses_current_proof_within_original_W_without_SCREEN',
        'test_independent_reproof_current_HUD_then_recorded_ACK_duration_and_real_Motion',
        'test_issued_but_unbegun_proof_loss_retires_new_id_once_with_original_W',
        'test_issued_replacement_original_P_and_unknown_synth_remain_hard_stops',
        'test_real_nonzero_Motion_cannot_become_permission_withdrawal',
        'test_reproof_without_current_HUD_cannot_reuse_the_retained_model_authority',
        'test_single_actual_GOLD_without_old_STONE_uses_zero_only_inside_owned_wait',
        'test_withdrawn_CLEAR_permission_keeps_original_W_equalities',
    }), True),
    ('tests.test_native_stationary_qualification117', 'NativeStationaryQualification117Tests', 'test117-native-NativeStationaryQualification117Tests', frozenset({
        'test_exact_owned_current_Scene_begin_does_not_repeat_matchers',
        'test_novel_source_recomputes_and_wrong_prefix_cannot_reuse_old_qualification',
        'test_ready_owned_source_publication_tick_does_not_repeat_matchers',
    }), True),
    ('tests.test_native_stationary_support117', 'NativeFixedSupport117Tests', 'test117-native-NativeFixedSupport117Tests', frozenset({
        'test_adjacent_zero_without_direct_original_qualification_cannot_create_support',
        'test_first_direct_support_stays_fixed_and_funds_only_current_zero',
        'test_original_geometry_remains_required_even_when_fixed_support_is_strict_zero',
    }), True),
)
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_classification111',
    'tests.test_native_clear_stationary095',
    'tests.test_native_closed_offer105',
    'tests.test_native_closed_price106',
    'tests.test_native_continuous116',
    'tests.test_native_controller',
    'tests.test_native_corner_vantage086',
    'tests.test_native_current_view114',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_framing101',
    'tests.test_native_gold_stationary092',
    'tests.test_native_goods113',
    'tests.test_native_handoff099',
    'tests.test_native_image_price111',
    'tests.test_native_initial_gold107',
    'tests.test_native_initial_restart_controller117',
    'tests.test_native_irregular110',
    'tests.test_native_lower_fringe100',
    'tests.test_native_motion067',
    'tests.test_native_motion075',
    'tests.test_native_navigation',
    'tests.test_native_navigation116',
    'tests.test_native_navigation117',
    'tests.test_native_observation072',
    'tests.test_native_occluded_corner097',
    'tests.test_native_offer_coverage104',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial116',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_partial_refresh104',
    'tests.test_native_passage072',
    'tests.test_native_passage115',
    'tests.test_native_passage_navigation072',
    'tests.test_native_passage_unsent076',
    'tests.test_native_perception',
    'tests.test_native_plural_stationary103',
    'tests.test_native_plural_wait103',
    'tests.test_native_price_geometry117',
    'tests.test_native_recovery',
    'tests.test_native_restart_yield112',
    'tests.test_native_ring094',
    'tests.test_native_ring117',
    'tests.test_native_ring_bank094',
    'tests.test_native_shadow_passage094',
    'tests.test_native_shared_zero115',
    'tests.test_native_shop115',
    'tests.test_native_shop117',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_single_gold117',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_singleton_stationary095',
    'tests.test_native_solid_corner098',
    'tests.test_native_split_shadow095',
    'tests.test_native_static075',
    'tests.test_native_stationary117',
    'tests.test_native_stationary_qualification117',
    'tests.test_native_stationary_support117',
    'tests.test_native_stationary_texture085',
    'tests.test_native_stationary_wait076',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_supported_mouth084',
    'tests.test_native_ui073',
    'tests.test_native_upper_entry112',
    'tests.test_native_view074',
    'tests.test_target_assessment087',
)
MAC_CASE_GROUPS = (('check_runtime117.py', ('single_face_restart', 'mixed_price_partial',
    'root_floor_restart', 'unsent_clear_reproof', 'unsent_gold1_reproof')),)
FILE_CORE_SOURCES = {'tests.test_native_ring117': 'NG2Ring.c',
    'tests.test_native_price_geometry117': 'NG2ShopPriceGeometry.h'}
PRODUCT_PATHS = ('necroprobe/campaign116.py', 'necroprobe/campaign_forensic116.py',
    'necroprobe/test116.py', 'necroprobe/test117.py', 'test_117.sh',
    'necroprobe/native_cycle.py', 'necroprobe/protocol.py', 'necroprobe/validation.py')
UNCHANGED_CONTINUATION_PATHS = ('patches/loopctrl/ngg2/NG2CycleSpool.swift', 'patches/loopctrl/ngg2/NG2CycleWire.swift',
    'patches/loopctrl/ngg2/NG2CycleExport.swift')
EXPECTED_API = dict(shared.EXPECTED_API, visible_goods_capability='necrogold_native_visible_goods_v1',
    initial_restart_start_flag='initial_restart')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST117 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED:
        raise ValueError('TEST117 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES, MAC_CASE_GROUPS)):
        raise ValueError('TEST117 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST117 empty or duplicate selected native scope')
    mac_cases = [case for _checker, methods in MAC_CASE_GROUPS for case in methods]
    if not mac_cases or len(mac_cases) != len(set(mac_cases)) or any(not methods for _, methods in MAC_CASE_GROUPS):
        raise ValueError('TEST117 selected Mac boundary scope is empty or duplicated')


def source_identity(driver, sealed, upstream):
    ensure_scope(); reject_fixture_overrides()
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest_path = 'patches/loopctrl/ngg2-manifest.json'
    manifest_raw = pinned_bytes(driver, manifest_path, code)
    manifest = json.loads(manifest_raw)
    before = manifest_sources(json.loads(git(driver, 'show', NATIVE_BASELINE+':'+manifest_path)))
    current = sealed['native_source_sha256']
    added = set(current)-set(before)
    changed = {path for path in set(before)&set(current) if before[path] != current[path]}
    if (set(before)-set(current) or len(before) != 36 or len(current) != 36+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST117 exact native changed/added inventory differs')
    if manifest_sources(manifest) != current or any(manifest.get(key) != value for key, value in EXPECTED_API.items()):
        raise ValueError('TEST117 installed source/API/capability identity differs')
    # Some retained Ring fixtures compile ROOT/patches/... directly. Their
    # source and all include additions must equal the installed sealed bytes;
    # this is byte identity, not a claim about a sealed compile location.
    compile_binding = {}
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test117_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    for native_path, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', native_path, row)
        path = source.relative_to(driver).as_posix()
        digest = sha(pinned_bytes(driver, path, code))
        if digest != current[native_path] or sha((upstream/native_path).read_bytes()) != digest:
            raise ValueError('TEST117 driver compile addition differs from sealed source: '+path)
        compile_binding[path] = dict(native_path=native_path, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {path for path in differences&baseline if not path.startswith('docs/')}
    new = {path for path in differences-baseline if not path.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST117 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl',
            '.github/workflows/loopctrl-geometry.yml', 'test_116.sh', 'test_117.sh').strip():
        raise ValueError('TEST117 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'
    ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST117 canonical Ring manifest changed')
    ring = json.loads(ring_raw)
    r12 = sorted(path for path in baseline if path.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST117 canonical/R12 source inventory differs')
    preserved = {}
    for path in (*ring['sources'], *r12, *UNCHANGED_CONTINUATION_PATHS):
        raw = pinned_bytes(driver, path, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+path):
            raise ValueError('TEST117 preserved source changed: '+path)
        preserved[path] = sha(raw)
    fixtures = {name.replace('.', '/')+'.py' for name in (*CORE_MODULES, *(row[0] for row in CASES))}
    fixtures.update(path for path in NEW_PATHS if path.startswith(('tests/', 'patches/loopctrl/')))
    fixtures.update(('patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test116_host.py'))
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE,
        changed_native_sources=sorted(changed), native_added=sorted(added),
        preserved_native_source_sha256={name: value for name, value in current.items() if name not in changed|added},
        fixture_source_sha256={path: sha(pinned_bytes(driver, path, code)) for path in sorted(fixtures)},
        product_sha256={path: sha(pinned_bytes(driver, path, code)) for path in PRODUCT_PATHS},
        fixture_compile_source_binding=compile_binding,
        retained_root_compile_scope='driver source byte-identical to sealed additions; not sealed-location compilation',
        changed_repository_paths=sorted(existing), new_repository_paths=sorted(new),
        preserved_source_sha256=preserved, native_manifest_sha256=sha(manifest_raw),
        mac_case_groups=[dict(checker=checker, cases=list(cases)) for checker, cases in MAC_CASE_GROUPS],
        historical_runtime_replayed=False,
        limitation='Selected software/Mac boundary checks do not establish iPhone reach rate or speed.')


def native_suites(upstream, driver):
    ensure_scope(); reject_fixture_overrides()
    # The imported utility module is private to this driver. Only its explicit
    # native selection inputs are configured; no TEST116 suites are executed.
    shared.CASES, shared.CORE_MODULES = CASES, CORE_MODULES
    suites = shared.native_suites(upstream, driver)
    for name, source in FILE_CORE_SOURCES.items():
        if name in sys.modules:
            sys.modules[name].CORE = upstream/'LoopCtrlUITests'/source
            alias = sys.modules.get(name.rsplit('.', 1)[-1])
            if alias is not None: alias.CORE = upstream/'LoopCtrlUITests'/source
    return suites


def run_scope(name, cases, output, evidence, *, receipt_name='test117-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test117-host-scope.json', 'test117-python39-scope.json'):
        raise ValueError('TEST117 scope receipt name is not permitted')
    cases = selected_cases(cases); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue(); (output/(name+'.txt')).write_text(log)
    print(log, end='', flush=True)
    evidence[name] = dict(selected=[case.id() for case in cases], tests_run=result.testsRun,
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
    driver, upstream, output = (getattr(args, name).resolve() for name in ('driver', 'upstream', 'output'))
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    verifier = importlib.import_module('verify_package')
    sealed = verifier.inspect_native_sources(upstream, driver)
    binding = source_identity(driver, sealed, upstream)
    suites = native_suites(upstream, driver)
    selected_cases(case for _label, cases in suites for case in cases)
    native = importlib.import_module('tests.test_native_controller')
    cycle = importlib.import_module('tests.test_native_cycle094')
    abi = {name: ctypes.sizeof(getattr(native, name)) for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    abi['Cycle'] = ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456, Cycle=216):
        raise ValueError('TEST117 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST117 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        not_run=['unchanged historical Runtime/spool suites', 'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci117')
    run_scope('test117-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection117Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST117 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test117-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST117 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
