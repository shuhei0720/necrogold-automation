"""TEST095 focused C/client contracts against exact sealed IPA sources.

Current C units are procedural contracts, not iPhone or game acceptance.
Legacy TEST094 API/FS/Export/Runtime cases and new policy2 Runtime/Wire cases
run as focused current Mac checks. Historical results are not phone acceptance.
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
_spec = importlib.util.spec_from_file_location('test095_shared_source_utils', HERE/'run_test094_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '2af68f63ee14a4523374bf563ae0b15afefdfdb2'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
    'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Ring.h', 'LoopCtrlUITests/NG2Runtime.swift',
    'LoopCtrlUITests/NG2CycleWire.swift'})
CASES = (
    ('tests.test_native_split_shadow095', 'NativeSplitShadow095Tests', 'test095-split-shadow',
     frozenset({
         'test_all_six_dark_cells_remain_unknown_and_are_required',
         'test_both_roof_sides_and_lower_left_wall_need_observed_support',
         'test_fixed_world_mouth_uses_three_actual_floor_steps_then_holds',
         'test_marked_split_roof_adds_only_fixed_upper_left_hypothesis',
         'test_observed_approach_floor_shortest_path_and_all_protections_are_required',
         'test_old_candidates_and_invalid_gold_goods_other_corners_are_preserved',
     }), True),
    ('tests.test_native_partial_continuation095', 'NativePartialContinuation095Tests', 'test095-partial',
     frozenset({
         'test_only_remote_unprotected_dirt_to_floor_or_unknown_is_admitted',
         'test_remote_change_cannot_clear_candidate_or_started_unknown',
         'test_remote_change_requires_strict_zero_prefix_stability_and_original_deadline',
         'test_remote_dirt_clearance_after_new_ticket_keeps_its_frozen_qualified_input',
         'test_remote_dirt_clearance_in_first_post_assessment_frame_keeps_new_observation_credit',
     }), True),
    ('tests.test_native_cycle_client095', 'CycleClient095Tests', 'test095-client',
     frozenset({
         'test_095_launcher_uses_separate_spool_and_truthful_not_started_message',
         'test_095_zip_prefix_filename_receipt_and_all_registered_bytes',
         'test_existing_094_and_generic_spools_preserve_original_zip_label',
     }), True),
    ('tests.test_native_shadow_passage094', 'NativeShadowPassage094Tests', 'test095-related-shadow',
     frozenset({
         'test_black_gaps_other_sides_goods_gold_protection_and_invalid_scenes_fail_closed',
         'test_fixed_world_mouth_moves_only_on_observed_floor_then_holds',
         'test_four_dark_cells_and_observed_short_floor_vantage_are_required',
         'test_marked_shadow_shape_keeps_unknown_and_adds_only_fixed_upper_left_mouth',
         'test_original_ten_mouths_supported_mouths_and_corner_masks_remain_unchanged',
         'test_tall_brown_column_and_opposite_roof_wall_are_required',
     }), True),
    ('tests.test_native_supported_mouth084', 'NativeSupportedMouth084Tests', 'test095-related-related-nav084',
     frozenset({
         'test_gold_goods_invalid_scenes_and_ordinary_right_down_exits_stay_out',
         'test_missing_flank_needs_outside_floor_and_three_current_walls',
         'test_observed_outside_floor_with_one_unknown_flank_selects_fixed_upper_left_mouths',
         'test_old_two_wall_and_shadowed_mouth_masks_and_source_bytes_are_preserved',
         'test_only_current_safe_floor_paths_authorize_approach',
     }), True),
    ('tests.test_native_corner_vantage086', 'NativeCornerVantage086Tests', 'test095-related-related-nav086',
     frozenset({
         'test_fixed_world_mouth_approaches_only_floor_and_holds_until_a_new_observed_route',
         'test_observed_mouth_outside_two_walls_and_unknown_inboard_are_all_required',
         'test_only_four_fixed_upper_left_corners_gain_the_new_hypothesis',
         'test_scene_guards_and_all_original_ten_mouth_branches_stay_unchanged',
         'test_unknown_inboard_keeps_observed_corner_candidate_for_safe_vantage',
         'test_vantage_requires_observed_shortest_three_step_route_and_clear_crosses',
     }), True),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test095-related-related-nav072',
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
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test095-related-cycle',
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
    ('tests.test_native_opened_entry093', 'NativeOpenedEntry093Tests', 'test095-related-related-opened-entry',
     frozenset({
         'test_expired_partial_entry_reacquires_independent_future_permission',
         'test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative',
         'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
         'test_original_ticket_windows_epochs_and_actual_begin_boundaries_are_frozen',
         'test_projected_top_goods_growth_and_shrink_use_latest_separate_ticket',
         'test_projection_surface_gold_and_motion_counterexamples_reject_revalidation',
     }), True),
    ('tests.test_native_clipped_entry081', 'NativeClippedEntry081Tests', 'test095-related-related-clipped081',
     frozenset({
         'test_clipped_partial_goods_preserve_original_up_entry_then_real_move_and_goods_hold',
         'test_new_protection_nonedge_items_gold_or_near_changes_cannot_use_quarantine',
         'test_source_mask_and_top_gold_quarantine_survive_mask_zero_return',
     }), False),
    ('tests.test_native_device065', 'NativeDevice065Tests', 'test095-related-related-expiry065',
     frozenset({
         'test_pending_same_and_fresh_expiry_reacquire_without_rewriting_retired_ticket',
     }), False),
    ('tests.test_native_cycle_client094', 'CycleClient094Tests', 'test095-related-client',
     frozenset({
         'test_ack_failure_retains_same_archive_and_retries_no_game_start',
         'test_authenticated_definitive_not_started_is_distinct_from_unknown_start',
         'test_cancel_after_durable_start_intent_never_posts_start',
         'test_changed_completed_archive_blocks_ack_and_preserves_destination',
         'test_changed_png_blocks_ack',
         'test_collection_recovers_all_records_and_batched_png_without_pixel_classifier',
         'test_durable_per_run_journal_survives_interruption_before_active_mirror',
         'test_envelope_requires_exact_schema_mode_profile_and_run',
         'test_fresh_session_starts_once_after_ready_and_keeps_heartbeat_before_terminal',
         'test_gameworker_drain_is_required_before_manifest',
         'test_interrupted_diagnostic_is_saved_but_never_claimed_normal_completion',
         'test_late_terminal_assessment_is_reported_as_unadopted_not_unexecuted_or_negative',
         'test_later_explicit_invocation_starts_new_id_only_after_prior_receipt_and_zip_verify',
         'test_malformed_not_started_error_cannot_clear_uncertain_input_intent',
         'test_manifest_hash_is_of_exact_utf8_not_python_reserialization',
         'test_manifest_registry_rejects_extra_fields_duplicate_ids_and_bool_lengths',
         'test_method_admission_rejects_oldprofile_unknownfields_and_arbitrary_input',
         'test_missing_frame_metadata_never_resolves_or_publishes',
         'test_missing_header_is_publishable_only_as_explicit_interrupted_diagnostic',
         'test_native_pending_deadline_and_cancellation_do_not_reissue_after_expiry',
         'test_native_unpublished_id_is_recovered_without_new_start',
         'test_new_profile_has_an_explicit_admitted_client_not_old_profile_fallback',
         'test_notification_preflight_failure_can_start_on_next_explicit_invocation',
         'test_only_authenticated_dedicated_pending_code_is_automatically_polled',
         'test_permission_denied_never_sends_start',
         'test_png_all_chunks_crc_and_rgba_geometry_are_verified',
         'test_published_ack_occurs_only_after_full_crc_sha_zip_and_destination_copy',
         'test_real_encrypted_pending_reply_is_polled_but_bad_mac_is_not',
         'test_return_zip_deflates_stored_recovery_png_and_preserves_all_bytes',
         'test_same_offset_retry_preserves_and_compares_uncheckpointed_suffix',
         'test_schema_requires_current_api_new_capability_and_integer_protocol',
         'test_start_admission_guard_runs_after_crypto_before_transport',
         'test_started_unknown_frozen_terminal_remains_exportable_without_new_input',
         'test_uncertain_start_is_sent_once_and_next_invocation_only_recovers_same_id',
     }), True),
    ('tests.test_native_shop_framing083', 'NativeShopFraming083Tests', 'test095-related-framing083',
     frozenset({
         'test_public_open_entry_partial_framing_then_visible_keeps_ticket_and_goods_priority',
     }), False),
    ('tests.test_native_ring094', 'NativeRing094Tests', 'test095-related-ring',
     frozenset({
         'test_direct_opaque_rgba_same_slot_target_and_raw_word_all_slots',
         'test_fast_upper_bounds_preserve_positive_and_explicitly_qualify_pruned_scores',
         'test_more_than_twelve_observed_sign_hypotheses_fail_instead_of_dropping_candidates',
         'test_negative_finalizer_rejects_missing_identity_foreign_row_and_any_candidate',
         'test_no_match_and_three_rows_never_prove_negative',
         'test_only_completed_observed_partial_without_a_positive_may_continue',
         'test_partial_icon_above_hud_is_retained_when_only_price_overlaps_hud',
         'test_partial_pixels_keep_single_icon_name_even_without_a_complete_row',
         'test_partial_visible_target_and_candidate_survive_missing_three_column_row',
         'test_partial_visible_target_is_retained_when_price_ink_is_occluded',
         'test_pixel_failure_cancellation_and_deadline_never_become_completed_unknown',
         'test_raw_aggregation_cannot_retain_stale_identity_or_coverage_witnesses',
         'test_round9_matches_python_at_binary64_thresholds_and_decimal_ties',
         'test_same_slot_icon_and_name_precedes_a_stronger_unpaired_icon',
     }), True),
    ('tests.test_native_ring_bank094', 'NativeRingBank094Tests', 'test095-related-bank',
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
    ('tests.test_native_singleton_stationary095', 'NativeSingletonStationary095Tests', 'test095-singleton',
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
    ('tests.test_native_clear_stationary095', 'NativeClearStationary095Tests', 'test095-clear-stationary',
     frozenset({
         'test_actual_gold_unknown_uses_the_original_strict_handoff_only',
         'test_cancel_or_started_unknown_cannot_reuse_the_zero_wait',
         'test_independent_clear_singleton_zero_rearms_only_a_new_future_ticket',
         'test_known_motion_or_failed_decode_cannot_fall_back_at_observation_or_begin',
         'test_original_wait_and_parent_equalities_cannot_be_renewed_by_zero_proof',
         'test_zero_proof_needs_independent_stable_current_prefix_capture',
     }), True),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test095-related-wait076',
     frozenset({
         'test_adjacent_blocked_frames_cannot_replace_the_original_anchor',
         'test_goods_priority_and_unproven_new_gold_hold_without_moving',
         'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority',
         'test_proof_requires_independent_current_prefix_and_increasing_capture',
         'test_ready_or_issued_unknown_does_not_reopen_the_same_wait',
         'test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit',
         'test_unsafe_changed_scene_and_unproven_or_expired_ticket_cannot_start_wait',
         'test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it',
     }), True),
    ('tests.test_native_stationary_texture085', 'NativeStationaryTexture085Tests', 'test095-related-zero085',
     frozenset({
         'test_observed_terrain_goods_gold_door_and_protection_guards',
         'test_old_unit_tween_reverse_and_opening_outputs_are_never_overwritten',
         'test_original_numeric_support_agreement_bands_and_competition_boundaries',
         'test_phase_alias_noise_and_blur_dependency_counterexamples_stay_unknown',
         'test_public_clear_floor_zero_requires_independent_stationary_evidence',
     }), False),
    ('tests.test_native_gold_stationary092', 'NativeGoldStationary092Tests', 'test095-related-gold092',
     frozenset({
         'test_complete_nonhud_old_terrain_gold_and_safe_floor_are_required',
         'test_known_motion_and_nonzero_surfaces_cannot_be_overwritten',
         'test_lighting_drift_with_stable_gold_confirms_only_zero',
         'test_raw_finite_zero_and_independent_texture_competition_are_required',
     }), True),
    ('tests.test_native_terrain_axis091', 'NativeTerrainAxis091Tests', 'test095-related-axis091',
     frozenset({
         'test_blur_axis_ambiguity_and_single_region_cannot_supply_unit',
         'test_complete_nonhud_old_terrain_and_unique_translation_are_required',
         'test_finite_unit_scope_and_original_known_results_are_preserved',
         'test_public_unit_requires_new_independent_axis_proof',
     }), True),
    ('tests.test_native_cycle_binary095', 'NativeCycleBinary095Tests', 'test095-cycle-binary',
     frozenset({
         'test_all_five_maxima_require_finite_equal_conservative_bounds_below_candidate',
         'test_complete_generic_five_cell_bounds_reach_only_the_existing_durable_restart',
         'test_generic_domain_and_representative_pose_have_exact_finite_geometry',
         'test_missing_cell_partial_source_failure_or_layout_uncertainty_stays_held',
         'test_target_candidate_or_strong_word_anywhere_vetoes_binary_absence',
     }), True),
    ('tests.test_native_target_only095', 'TargetOnly095Tests', 'test095-target-only',
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
)

CORE_MODULES = tuple(dict.fromkeys((*shared.CORE_MODULES,
    'tests.test_native_cycle094', 'tests.test_native_stationary_wait076',
    'tests.test_native_passage_unsent076', 'tests.test_native_observation072')))
DEPENDENCY_FIXTURES = ('tests/test_protocol.py', 'tests/test_beat_sync.py',
                       'tests/test_target_assessment087.py')
PRESERVED_REPOSITORY = (*shared.RETAINED_PATHS, 'necroprobe/native_cycle.py', 'test_094.sh',
    'necroprobe/goldshop_auth_features094.json', 'necroprobe/non_target_features094.json',
    'tools/ring_native/generate_non_target094.py',
    'patches/loopctrl/ngg1.patch', 'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py',
    'patches/loopctrl/ngg2.patch', 'patches/loopctrl/ngg2_runtime_tests.swift',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.c', 'patches/loopctrl/ngg2_runtime_scene_fixtures.h',
    'patches/loopctrl/ngg2_runtime_fakes.swift', 'patches/loopctrl/check_cycle_api094.py',
    'patches/loopctrl/check_cycle_spool094.py', 'patches/loopctrl/check_cycle_export094.py',
    'patches/loopctrl/check_runtime_cycle094.py', 'patches/loopctrl/ngg2_cycle_api094_tests.swift',
    'patches/loopctrl/ngg2_cycle_spool_tests.swift', 'patches/loopctrl/ngg2_cycle_export094_tests.swift',
    'patches/loopctrl/ngg2_cycle_runtime_tests.swift', 'patches/loopctrl/ngg2_cycle_runtime_fixture.c',
    'patches/loopctrl/ngg2_cycle_runtime_fixture.h', *DEPENDENCY_FIXTURES)
PRODUCT_PATHS = ('necroprobe/cycle_publication.py', 'necroprobe/test094.py', 'necroprobe/test095.py', 'test_095.sh')
CURRENT_MAC_SOURCES = ('patches/loopctrl/check_runtime_target_only095.py',
                       'patches/loopctrl/ngg2_target_only_runtime_tests.swift')


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO095_') for name in os.environ):
        raise ValueError('TEST095 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST095 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST095 scope is empty or duplicated')
    required = {'tests.test_native_split_shadow095', 'tests.test_native_partial_continuation095',
                'tests.test_native_cycle_client095', 'tests.test_native_singleton_stationary095',
                'tests.test_native_clear_stationary095', 'tests.test_native_cycle_binary095',
                'tests.test_native_target_only095'}
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST095 new focused scopes are missing')


def native_delta(before, current, expected):
    if set(before) != set(current):
        raise ValueError('sealed native inventory changed')
    changed = {name for name in current if current[name] != before[name]}
    if changed != set(expected):
        raise ValueError('unexpected TEST095 native change scope: ' + repr(sorted(changed)))
    return changed


def native_suites(upstream, driver=None, axis_snapshot=None):
    driver = HERE.parents[1] if driver is None else driver
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for name,module in modules.items():
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('fixture import escaped pinned driver: '+name)
        module.CORE = upstream/'LoopCtrlUITests'
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream/'LoopCtrlUITests'
    axis_name = 'tests.test_native_terrain_axis091'
    if axis_name in modules:
        if axis_snapshot is None:
            raise ValueError('current eight-file axis snapshot is required')
        modules[axis_name].CORE = axis_snapshot
        alias = sys.modules.get(axis_name.rsplit('.',1)[-1])
        if alias is not None:
            alias.CORE = axis_snapshot
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in CASES]


AXIS091_FILES = ('NG2Beat.c', 'NG2Controller.c', 'NG2Navigation.c', 'NG2Perception.c',
                 'NG2CaptureBridge.h', 'NG2Controller.h', 'NG2Core.h', 'NG2Templates.h')


def axis091_snapshot(upstream, destination, expected):
    # The historical test insists on eight identities and compiles only its Nav
    # shim. Preserve that assertion with eight exact CURRENT sealed files; never
    # supply an old Controller or extra Ring headers and call it current C work.
    if len(AXIS091_FILES) != 8 or len(set(AXIS091_FILES)) != 8:
        raise ValueError('axis snapshot inventory')
    destination.mkdir()
    identities = {}
    for name in AXIS091_FILES:
        source = upstream/'LoopCtrlUITests'/name
        if source.is_symlink() or not source.is_file():
            raise ValueError('axis snapshot source')
        raw = source.read_bytes();digest = sha(raw)
        if digest != expected.get('LoopCtrlUITests/'+name):
            raise ValueError('axis snapshot differs from sealed source: '+name)
        (destination/name).write_bytes(raw);identities[name] = digest
    return dict(source_sha256=identities, files=8, compiled_navigation_sha256=identities['NG2Navigation.c'],
        scope='Only the Nav shim is compiled. The other seven current file identities satisfy the unchanged historical harness; no current Controller integration claim.')


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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('095')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('095')]
    paths += ['patches/loopctrl/run_test094_host.py', 'patches/loopctrl/test_device_ci094.py']
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
    for module_name in ('necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py',
                      'patches/loopctrl/test_device_ci095.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    current_mac = {path:sha(pinned_bytes(driver,path,code)) for path in CURRENT_MAC_SOURCES}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        current_mac_source_sha256=current_mac,
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        historical_mac_boundary_proof=dict(code='60284ae188d3e5bec4981256c1baa6110609ea4b',run=43390253276,build=165,
            source_reference=NATIVE_BASELINE,executed_this_run=False,
            runtime_cases=dict(new=11,old=3),components=['API owner/schema','immutable spool','terminal export','selected Runtime callbacks'],
            limitation='Historical TEST094 metadata only. Current TEST095 changes Runtime/Wire and C callees, so fresh focused Mac proof is required; this record grants no reuse eligibility or phone acceptance.'),
        direct_c_compiler_binding='Fixtures use the installed CORE or hash-identical pinned driver Ring/canonical sources; only bounded current native Ring cases are classified')


def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test095-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test095-axis091-current-') as temporary:
        binding=source_identity(driver,before)
        snapshot_root=Path(temporary)/'axis091'
        snapshot=axis091_snapshot(upstream,snapshot_root,before['native_source_sha256'])
        suites=native_suites(upstream,driver,axis_snapshot=snapshot_root)
        selected_cases(case for _,cases in suites for case in cases)
        fixture=importlib.import_module('tests.test_native_controller');cycle=importlib.import_module('tests.test_native_cycle094')
        abi={n:ctypes.sizeof(getattr(fixture,n)) for n in ('Scene','Status','Event','MotionWait','RecoveryStatus')}
        abi['Cycle']=ctypes.sizeof(cycle.Cycle)
        if abi != dict(Scene=23864,Status=192,Event=128,MotionWait=48,RecoveryStatus=456,Cycle=216):
            raise ValueError('native public or companion ABI changed')
        evidence=dict(scope='TEST095 focused C/client repairs and related contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,device_test='not_run',
            fixture_source_snapshots={'test095-related-axis091':snapshot},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old085 sixth legacy eight-file Controller wrapper: incompatible with current Ring headers; current caller covered by TEST095 clear-stationary',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci095')
        run_scope('test095-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection095Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test095-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST095 selected contracts against exact sealed IPA sources; Mac checks are separate and phone acceptance is not run')


if __name__=='__main__':main()
