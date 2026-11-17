"""TEST113 source-bound selected native contracts; pending author closure.

No device traffic. The current Runtime is retained byte-for-byte; its public
status boundary is still executed separately on Mac with the current C.
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
import unittest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test113_shared_source_utils', HERE/'run_test112_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '6f4925214fa2efd4e9516e898611ab3c10fd3002'
SCOPE_FINALIZED = True
RUNTIME_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
# Root fills exact source-bound Native author inventories after their review.
CASES = (
    ('tests.test_native_closed_floor113', 'NativeClosedFloor113Tests', 'test113-native-NativeClosedFloor113Tests', frozenset({
        'test_closed_floor_refresh_refuses_changed_local_material_route_or_protection',
        'test_remote_floor_palette_keeps_exact_unsent_ticket_without_same_reissues',
        'test_remote_stone_refresh_retires_then_requires_independent_future_ticket',
    }), True),
    ('tests.test_native_goods113', 'NativeGoodsDataRetry113Tests', 'test113-native-NativeGoodsDataRetry113Tests', frozenset({
        'test_a_begun_pause_is_not_withdrawn_or_replaced_by_data_retry',
        'test_candidates_targets_and_malformed_results_never_wait_for_absence_retry',
        'test_changed_item_gold_protection_motion_prefix_cancel_and_parent_cannot_rebind',
        'test_intermediate_unknown_frame_neither_poison_data_retry_nor_grant_authority',
        'test_only_a_definitely_unbegun_pause_can_yield_to_the_fresh_data_wait',
        'test_prepared_pause_does_not_hide_inflight_hard_source_invalidation',
        'test_safe_full_unknown_waits_for_new_normal_negative_without_any_input',
        'test_two_pairwise_zeros_cannot_replace_direct_original_full_proof',
        'test_unknown_and_deadline_retries_share_the_original_two_replacement_budget',
    }), True),
    ('tests.test_native_goods113', 'NativeGoodsUpView113Tests', 'test113-native-NativeGoodsUpView113Tests', frozenset({
        'test_a_prior_real_up_move_keeps_its_single_credit_while_the_new_view_is_independent',
        'test_existing_entry_episode_cannot_gain_an_independent_third_up_allowance',
        'test_known_ack_unknown_motion_gets_one_new_up_ticket_then_real_move_and_normal_negative',
        'test_later_up_ticket_needs_unchanged_original_material_and_direct_zero',
        'test_prepared_pause_cannot_replace_cached_prior_move_source_or_ordinal',
        'test_unknown_after_actual_new_up_does_not_restore_the_single_view_allowance',
        'test_unknown_synth_is_never_reinterpreted_as_known_visual_unknown',
        'test_up_observation_needs_positive_floor_exact_projection_and_single_shop',
        'test_up_view_normal_positive_candidate_preempts_initial_observation',
    }), True),
    ('tests.test_native_initial_uncertain113', 'NativeInitialUncertain113Tests', 'test113-native-NativeInitialUncertain113Tests', frozenset({
        'test_empty_changed_or_missing_retained_support_never_becomes_restart_authority',
        'test_overlapping_or_wrong_prefix_trigger_has_no_new_authority',
        'test_settled_prefirst_ticket_uncertainty_waits_for_new_pair_and_entirely_fresh_fit',
    }), True),
    ('tests.test_native_palette_zero113', 'NativePaletteWait113Tests', 'test113-native-NativePaletteWait113Tests', frozenset({
        'test_ready_wait_survives_palette_then_uses_only_new_future_ticket_and_real_ack',
    }), True),
    ('tests.test_native_palette_zero113', 'NativePaletteZero113Tests', 'test113-native-NativePaletteZero113Tests', frozenset({
        'test_local_unknown_stone_origin_next_landmark_or_protection_never_qualifies',
        'test_near_palette_phase_adds_zero_without_changing_global_motion_or_old_helper',
    }), True),
    ('tests.test_native_revealed_ack113', 'NativeRevealedAck113Tests', 'test113-native-NativeRevealedAck113Tests', frozenset({
        'test_expired_visual_or_unknown_synth_never_acquires_movement_or_resends',
        'test_only_real_current_prefix_ack_gains_the_observed_unit_with_original_visual_deadline',
    }), True),
    ('tests.test_native_revealed_domain113', 'RevealedDomain113Tests', 'test113-native-RevealedDomain113Tests', frozenset({
        'test_complete_domain2_dependency_and_known_axis_prove_one_past_unit',
        'test_dependency_plane_cannot_replace_missing_known_axis_support',
        'test_each_signed_plane_requires_its_own_95_percent_agreement',
        'test_known_axis_needs_both_bands_despite_strong_total_and_margins',
        'test_one_unavailable_wider_alternative_rejects_despite_two_strong_winners',
        'test_positive_competing_known_axis_needs_its_own_15_point_lead',
        'test_raw_domain1_stays_with_its_existing_qualification',
        'test_raw_wrong_direction_nonunit_and_old_known_results_are_not_overridden',
        'test_scene_authority_and_complete_old_witnesses_are_required',
    }), True),
    ('tests.test_native_classification111', 'NativeClassification111Tests', 'test113-native-NativeClassification111Tests', frozenset({
        'test_normal_complete_negative_is_bound_to_retained_pixels_and_current_pause',
        'test_target_candidate_remain_latched_and_never_restore_move',
    }), False),
    ('tests.test_native_classification111', 'NativeClassificationRetry111Tests', 'test113-native-NativeClassificationRetry111Tests', frozenset({
        'test_deadline_waits_for_actual_worker_then_fresh_full_owns_normal_negative',
        'test_late_slot_or_global_positive_hints_veto_fresh_negative',
        'test_latest_unsafe_frame_blocks_retry_without_rewinding_to_earlier_safe_pixels',
        'test_malformed_or_missing_deadline_report_never_starts_retry',
        'test_prefix_cancel_parent_expiration_and_late_root_positive_preserve_freeze',
        'test_retry_unknown_has_no_movement_credit_and_at_most_two_new_jobs',
        'test_source_149_150_ms_worker_begin_and_expired_before_start_keep_root_bound',
        'test_terminal_drain_can_retain_a_late_candidate_without_reopening',
    }), False),
    ('tests.test_native_clear_stationary095', 'NativeClearStationary095Tests', 'test113-native-NativeClearStationary095Tests', frozenset({
        'test_actual_gold_unknown_uses_the_original_strict_handoff_only',
        'test_cancel_or_started_unknown_cannot_reuse_the_zero_wait',
        'test_independent_clear_singleton_zero_rearms_only_a_new_future_ticket',
        'test_known_motion_or_failed_decode_cannot_fall_back_at_observation_or_begin',
        'test_original_wait_and_parent_equalities_cannot_be_renewed_by_zero_proof',
        'test_zero_proof_needs_independent_stable_current_prefix_capture',
    }), True),
    ('tests.test_native_closed_refresh081', 'NativeClosedRefresh081Tests', 'test113-native-NativeClosedRefresh081Tests', frozenset({
        'test_direct_anchor_strict_proof_and_independent_current_prefix_are_required',
        'test_four_direction_closed_gate_refresh_accepts_remote_stone_without_credit',
        'test_geometry_near_cells_and_all_protection_materials_bound_stone_scope',
        'test_goods_cancel_phase_owner_and_unknown_sent_input_preempt_refresh',
        'test_original_horizons_current_hud_and_fifty_ms_preparation_remain_frozen',
        'test_published_identity_source_and_old_refresh_scope_do_not_broaden',
    }), True),
    ('tests.test_native_dirt_ticket079', 'NativeDirtTicket079Tests', 'test113-native-NativeDirtTicket079Tests', frozenset({
        'test_closed_gate_unit_target_unknown_goods_and_verified_lead_are_required',
        'test_goods_cancel_owner_and_started_or_unknown_input_never_gain_another_send',
        'test_local_gold_protected_material_item_and_nonpalette_changes_are_rejected',
        'test_original_actual_deadline_and_stable_current_prefix_are_kept',
        'test_unknown_tween_or_nonzero_motion_cannot_preserve_dig_authority',
        'test_verified_four_direction_dig_keeps_ticket_then_counts_only_terrain_opening',
    }), True),
    ('tests.test_native_entry_episode102', 'NativeEntryEpisode102Tests', 'test113-native-NativeEntryEpisode102Tests', frozenset({
        'test_ack_unknown_visual_wait_and_unknown_synth_do_not_create_second_step',
        'test_full_unknown_after_first_move_requalifies_up_from_its_exact_latest_job',
        'test_second_observation_normal_complete_negative_preserves_durable_restart_protocol',
        'test_second_unknown_and_goods_unknown_hold_without_generic_credit_or_third_input',
    }), False),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test113-native-NativeFullFraming101Tests', frozenset({
        'test_candidate_target_upper_bound_or_strong_word_is_held_before_observation_input',
        'test_fresh_partial_after_local_move_is_classified_truthfully_but_never_navigates',
        'test_full_unknown_later_static_fresh_ticket_actual_moved_then_new_candidate',
        'test_later_static_requires_immutable_goods_materials_protection_and_zero',
        'test_new_full_negative_counts_once_and_uses_only_its_new_durable_source',
        'test_new_move_visual_unknown_keeps_bounded_wait_without_full_shortcut_or_resend',
        'test_original_horizon_prefix_cancel_and_input_unknown_never_remint_a_move',
        'test_real_opening_axis_known_floor_protection_and_safe_potential_roi_are_required',
        'test_second_unknown_in_same_level_does_not_restore_framing',
    }), False),
    ('tests.test_native_goods111', 'NativeGoods111Tests', 'test113-native-NativeGoods111Tests', frozenset({
        'test_each_raw_price_cap_extra_board_and_extra_object_remains_a_hold',
        'test_target_and_candidate_priority_and_failed_jobs_are_preserved',
        'test_upper_numeric_certificate_rejects_forged_fields',
    }), False),
    ('tests.test_native_initial_gold107', 'NativeInitialGold107Tests', 'test113-native-NativeInitialGold107Tests', frozenset({
        'test_data_anchor_changes_keep_original_wait_deadline_and_do_not_skip_a_pair',
        'test_fade_anchor_retires_before_latest_independent_pair_gets_a_new_ticket',
        'test_goods_protection_cancellation_and_moved_evidence_never_recover_an_initial_ticket',
        'test_moved_before_a_reanchor_episode_cannot_be_forgotten_by_unknown_views',
        'test_nonindependent_stale_and_foreign_prefix_frames_never_supply_the_second_proof',
        'test_original_wait_and_sync_limits_are_not_renewed_by_fade_observations',
        'test_post_restart_first_fade_gold_uses_only_latest_pair_for_its_first_move',
    }), True),
    ('tests.test_native_initial_scene091', 'NativeInitialScene091Tests', 'test113-native-NativeInitialScene091Tests', frozenset({
        'test_cancel_started_unknown_ack_and_goods_cannot_reacquire',
        'test_changed_gold_cannot_combine_two_different_views_into_authority',
        'test_crossing_stale_and_original_sync_limit_do_not_supply_new_proof',
        'test_hidden_old_mouth_is_not_a_negative_even_after_two_new_frames',
        'test_new_actual_gold_also_needs_two_independent_frames',
        'test_recovery_allowance_is_two_and_initial_deadline_never_restarts',
        'test_signature_only_uncertainty_retires_before_new_source',
        'test_unknown_gold_withdraws_and_requires_two_new_clear_frames',
    }), True),
    ('tests.test_native_offer_coverage104', 'NativeOfferCoverage104Tests', 'test113-native-NativeOfferCoverage104Tests', frozenset({
        'test_all_strip_templates_and_strong_name_keep_target_priority',
        'test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards',
        'test_raw_caps_prices_extra_groups_and_lower_container_price_remain_observed',
    }), False),
    ('tests.test_native_plural_wait103', 'NativePluralWait103Tests', 'test113-native-NativePluralWait103Tests', frozenset({
        'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
        'test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero',
        'test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back',
        'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
        'test_plural_proof_needs_independent_stable_current_prefix_capture',
        'test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket',
    }), True),
    ('tests.test_native_revealed_motion108', 'RevealedMotion108Tests', 'test113-native-RevealedMotion108Tests', frozenset({
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
    ('tests.test_native_revealed_singleton096', 'NativeRevealedSingleton096Tests', 'test113-native-NativeRevealedSingleton096Tests', frozenset({
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
    ('tests.test_native_singleton_phase112', 'NativeSingletonPhase112Tests', 'test113-native-NativeSingletonPhase112Tests', frozenset({
        'test_each_lighting_phase_and_action_adds_only_read_only_zero_qualification',
        'test_known_zero_translated_texture_and_missing_independent_bands_do_not_qualify',
        'test_null_and_out_of_range_direction_are_rejected',
        'test_old_landmark_two_dimensional_dirt_and_near_floor_are_required',
    }), True),
    ('tests.test_native_singleton_phase112', 'NativeSingletonPhaseWait112Tests', 'test113-native-NativeSingletonPhaseWait112Tests', frozenset({
        'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
        'test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero',
        'test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back',
        'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
        'test_plural_proof_needs_independent_stable_current_prefix_capture',
        'test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket',
    }), True),
    ('tests.test_native_upper_entry112', 'NativeUpperEntry112Tests', 'test113-native-NativeUpperEntry112Tests', frozenset({
        'test_geometry_projection_and_first_safe_floor_are_independent_requirements',
        'test_started_unknown_move_never_resends_or_credits_a_new_step',
        'test_target_candidate_and_late_hint_preempt_later_negative',
    }), False),
)
REQUIRED_NEW_SCOPES = frozenset({'tests.test_native_closed_floor113', 'tests.test_native_goods113', 'tests.test_native_initial_uncertain113', 'tests.test_native_palette_zero113', 'tests.test_native_revealed_ack113', 'tests.test_native_revealed_domain113'})
CORE_MODULES = tuple(dict.fromkeys((*shared.CORE_MODULES,
    'tests.test_native_upper_entry112',
    'tests.test_native_goods111',
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_classification111',
    'tests.test_native_clear_stationary095',
    'tests.test_native_closed_refresh081',
    'tests.test_native_controller',
    'tests.test_native_entry_episode102',
    'tests.test_native_motion067',
    'tests.test_native_motion075',
    'tests.test_native_observation072',
    'tests.test_native_passage072',
    'tests.test_native_passage_unsent076',
    'tests.test_native_plural_stationary103',
    'tests.test_native_plural_wait103',
    'tests.test_native_recovery',
    'tests.test_native_revealed_motion108',
    'tests.test_native_singleton_stationary095',
    'tests.test_native_stationary_texture085',
    'tests.test_native_stationary_wait076',
    'tests.test_native_ui073',
    'tests.test_native_view074',
)))
DEPENDENCY_FIXTURES = ()
PRODUCT_PATHS = ('necroprobe/native_cycle.py', 'necroprobe/cycle_publication.py',
    'necroprobe/trial_evidence099.py', 'necroprobe/campaign099.py', 'necroprobe/test099.py',
    'necroprobe/test113.py', 'test_113.sh', 'patches/loopctrl/ngg2.patch', 'patches/loopctrl/apply_ngg2.py')
APPROVED_CHANGED_REPOSITORY = frozenset({'necroprobe/native_cycle.py', 'necroprobe/cycle_publication.py'})
# Exact TEST079/081/101 method revisions are admitted after independent review. The
# historical TEST112 exception is already in our baseline and stays immutable.
LEGACY_FIXTURE_EXCEPTIONS_PATH = 'patches/loopctrl/test113-fixture-exceptions.json'
_exception_manifest = json.loads((HERE/'test113-fixture-exceptions.json').read_text())
if (_exception_manifest.get('schema') != 'test113-historical-source-exception-v1'
        or _exception_manifest.get('baseline') != NATIVE_BASELINE):
    raise ValueError('TEST113 historical fixture exception identity differs')
LEGACY_FIXTURE_EXCEPTIONS = _exception_manifest['files']
APPROVED_FIXTURE_METHODS = {
    'tests/test_native_dirt_ticket079.py': 'NativeDirtTicket079Tests.test_closed_gate_unit_target_unknown_goods_and_verified_lead_are_required',
    'tests/test_native_closed_refresh081.py': 'NativeClosedRefresh081Tests.test_geometry_near_cells_and_all_protection_materials_bound_stone_scope',
    'tests/test_native_full_framing101.py': 'NativeFullFraming101Tests.test_real_opening_axis_known_floor_protection_and_safe_potential_roi_are_required',
}
PRESERVED_REPOSITORY = tuple(dict.fromkeys((*shared.PRESERVED_REPOSITORY, *shared.PRODUCT_PATHS,
    'necroprobe/test112.py', 'test_112.sh', 'patches/loopctrl/run_test112_host.py',
    'patches/loopctrl/run_test112_python39.py', 'patches/loopctrl/test_device_ci112.py')))
RUNTIME_PROOF_POLICY = 'selected_current_runtime_boundaries_required'
BASELINE_RUNTIME_SHA256 = 'dc082fd9658df32924c90423c544030d327c744f4224d4d8c868762a6e2e741f'
CURRENT_MAC_CASES = ('terminal_status', 'upper_entry')
NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith(('NECRO113_', 'NECRO_TEST113_')) for name in os.environ):
        raise ValueError('TEST113 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST113 native/method/current Mac author inventories are pending')
    labels = [row[2] for row in CASES]
    if not CASES or not REQUIRED_NEW_SCOPES or len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST113 scope is empty or duplicated')
    if not REQUIRED_NEW_SCOPES <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST113 new focused scopes are missing')


def native_delta(before, current, allowed, added=None):
    added = set(EXPECTED_NATIVE_ADDITIONS if added is None else added)
    if set(before)-set(current) or set(current)-set(before) != added:
        raise ValueError('TEST113 native addition/removal scope differs')
    changed = {path for path in current if before.get(path) != current[path]}
    if not allowed or changed != set(allowed) or not added <= changed:
        raise ValueError('TEST113 exact native changed-source set differs')
    return changed


def approved_patch_identity(current, original, manifest, before):
    if (current != original or sha(current) != manifest['patch_sha256']
            or sha(original) != before['patch_sha256']):
        raise ValueError('TEST113 retained G2 patch/manifest source differs')
    return sha(current)


def preserved_fixture_identity(path, current, original):
    matches = [row for row in LEGACY_FIXTURE_EXCEPTIONS if row['path'] == path]
    if not matches:
        return retained_identity(current, original)
    if len(matches) != 1 or path not in APPROVED_FIXTURE_METHODS:
        raise ValueError('TEST113 unknown or duplicate fixture exception')
    spec = matches[0]
    if (sha(original) != spec['old_file_sha256'] or sha(current) != spec['new_file_sha256']
            or len(spec['methods']) != 1
            or spec['methods'][0]['name'] != APPROVED_FIXTURE_METHODS[path]):
        raise ValueError('TEST113 unreviewed historical fixture revision: '+path)
    scrubbed = []
    for raw, key in ((original, 'old_sha256'), (current, 'new_sha256')):
        text = raw.decode(); tree = ast.parse(text); lines = text.splitlines(keepends=True)
        method = spec['methods'][0]
        klass, name = method['name'].split('.')
        target = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == klass)
        selected = next(n for n in target.body if isinstance(n, ast.FunctionDef) and n.name == name)
        if selected.decorator_list or sha(ast.get_source_segment(text, selected).encode()) != method[key]:
            raise ValueError('TEST113 approved method hash differs: '+method['name'])
        lines[selected.lineno-1:selected.end_lineno] = ['    # APPROVED TEST113 METHOD '+method['name']+'\n']
        scrubbed.append(''.join(lines))
    if scrubbed[0] != scrubbed[1]:
        raise ValueError('TEST113 bytes outside approved method changed: '+path)
    return sha(current)


def runtime_source_identity(before, current):
    if not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST113 focused current Runtime boundary scope is pending')
    runtime = 'LoopCtrlUITests/NG2Runtime.swift'
    if before.get(runtime) != BASELINE_RUNTIME_SHA256 or current.get(runtime) != before[runtime]:
        raise ValueError('TEST113 retained Runtime source identity differs')
    return dict(policy=RUNTIME_PROOF_POLICY, source_reference=NATIVE_BASELINE,
        baseline_runtime_sha256=before[runtime], current_runtime_sha256=current[runtime],
        current_controller_sha256=current['LoopCtrlUITests/NG2Controller.c'],
        executed_in_host_selector=False, current_mac_execution_required=True,
        expected_current_mac_cases=list(CURRENT_MAC_CASES),
        before_runtime_api_assertion_required=False,
        limitation='Runtime bytes retained; current C/public status and upper entry need current Mac execution. BeforeParser actual3.9 assertion Red is a separate source-bound author receipt, not a repeated old Runtime API Red.')


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest = json.loads(pinned_bytes(driver, 'patches/loopctrl/ngg2-manifest.json', code))
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    if len(old) != 36 or len(current) != 36:
        raise ValueError('TEST113 native inventory is not 36')
    changed = native_delta(old, current, EXPECTED_NATIVE_CHANGES)
    approved_patch_identity(pinned_bytes(driver, 'patches/loopctrl/ngg2.patch', code),
        git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2.patch'), manifest, before)
    expected = {'api_version': '1.98.16-ngg2', 'client_capability': 'necrogold_native_v15',
        'cycle_capability': 'necrogold_native_cycle_v1', 'cycle_profile': 'normal-1-1-cycle-v1',
        'irregular_capability': 'necrogold_native_irregular_v1', 'irregular_profile': 'normal-1-1-irregular-v1',
        'image_price_capability': 'necrogold_native_image_price_v1', 'compiler_profile_version': 3,
        'restart_yield_capability': 'necrogold_native_restart_yield_v1', 'restart_yield_start_flag': 'yield_after_restart'}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError('TEST113 native API/profile/cap/compiler identity differs')
    if (sealed['api_version'], sealed['client_capability']) != ('1.98.16-ngg2', 'necrogold_native_v15'):
        raise ValueError('TEST113 installed native API changed')
    baseline_paths = [p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p]
    paths = list(PRESERVED_REPOSITORY)
    ring_raw = pinned_bytes(driver, 'necroprobe/ring_native_manifest.json', code)
    retained_identity(ring_raw, git(driver, 'show', NATIVE_BASELINE+':necroprobe/ring_native_manifest.json'))
    ring = json.loads(ring_raw)
    if len(ring['sources']) != 15:
        raise ValueError('TEST113 canonical inventory differs')
    paths.extend(ring['sources'])
    paths.extend(p for p in baseline_paths if p.startswith(('tests/', 'necroprobe/', 'tools/ring_native/', 'legacy/r12/')))
    preserved = {}
    for path in dict.fromkeys(paths):
        if path not in APPROVED_CHANGED_REPOSITORY:
            preserved[path] = preserved_fixture_identity(path, pinned_bytes(driver, path, code), git(driver, 'show', NATIVE_BASELINE+':'+path))
    if sum(path.startswith('legacy/r12/') for path in preserved) != 40:
        raise ValueError('TEST113 R12 source inventory differs')
    revised = {}
    for path in APPROVED_CHANGED_REPOSITORY:
        raw = pinned_bytes(driver, path, code)
        if raw == git(driver, 'show', NATIVE_BASELINE+':'+path):
            raise ValueError('TEST113 approved changed source is unchanged: '+path)
        revised[path] = sha(raw)
    repository = {}
    for name, spec in manifest['additions'].items():
        digest = addition_identity(driver, name, spec)
        directory = 'tools/ring_native/' if spec.get('source_root') == 'ring_native' else 'patches/loopctrl/ngg2/'
        pinned_bytes(driver, directory+spec['source'], code)
        if current[name] != digest:
            raise ValueError('TEST113 repository/installed native source differs: '+name)
        repository[name] = digest
    products = {path: sha(pinned_bytes(driver, path, code)) for path in PRODUCT_PATHS}
    fixtures = set(path for path in baseline_paths if Path(path).parent.as_posix() == 'patches/loopctrl' and path.endswith(('.py', '.swift', '.c')))
    fixtures.update(name.replace('.', '/')+'.py' for name in (*CORE_MODULES, *(row[0] for row in CASES)))
    fixtures.update(('patches/loopctrl/run_test113_host.py', 'patches/loopctrl/test_device_ci113.py',
        'patches/loopctrl/run_test113_python39.py', 'patches/loopctrl/check_runtime113.py',
        'patches/loopctrl/ngg2_runtime113_tests.swift', LEGACY_FIXTURE_EXCEPTIONS_PATH,
        'patches/loopctrl/generate_upper112_pixels.py', 'patches/loopctrl/ngg2_runtime112_upper_fixture.c',
        'tests/test_native_ring_bank094.py', 'tests/test_native_shop_coverage102.py',
        'tests/test_native_offer_coverage104.py', 'necroprobe/non_target_features094.json'))
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE,
        fixture_source_sha256={path: sha(pinned_bytes(driver, path, code)) for path in sorted(fixtures)},
        runtime_proof_policy=runtime_source_identity(old, current), changed_native_sources=sorted(changed),
        preserved_native_source_sha256={name: current[name] for name in current if name not in changed},
        retained_source_sha256=preserved, changed_repository_source_sha256=revised,
        repository_native_source_sha256=repository, product_sha256=products,
        legacy_fixture_exceptions=LEGACY_FIXTURE_EXCEPTIONS,
        direct_c_compiler_binding='Selected fixtures compile exact installed sealed native sources; original-image calibration is separate.')


def native_suites(upstream, driver=None, nav086_source=None):
    driver = HERE.parents[1] if driver is None else driver
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES),
        *(path[:-3].replace('/', '.') for path in DEPENDENCY_FIXTURES))))
    modules = {name: importlib.import_module(name) for name in names}
    for name, module in modules.items():
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST113 fixture import escaped pinned driver: '+name)
        module.CORE = upstream/'LoopCtrlUITests'
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream/'LoopCtrlUITests'
    for name in ('tests.test_native_single_gold086', 'tests.test_native_terrain_axis091'):
        if name in modules:
            if nav086_source is None:
                raise ValueError('TEST113 current eight-file Nav snapshot is required for '+name)
            modules[name].CORE = nav086_source
            alias = sys.modules.get(name.rsplit('.', 1)[-1])
            if alias is not None:
                alias.CORE = nav086_source
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
        for name, klass, label, methods, exact in CASES]


def run_scope(name, cases, output, evidence):
    cases = selected_cases(cases)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue()
    (output/(name+'.txt')).write_text(log)
    print(log, end='', flush=True)
    evidence[name] = dict(selected=[case.id() for case in cases], tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), expected_failures=len(result.expectedFailures))
    (output/'test113-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    driver, upstream, output = (getattr(args, name).resolve() for name in ('driver', 'upstream', 'output'))
    ensure_scope()
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    verifier = importlib.import_module('verify_package')
    sealed = verifier.inspect_native_sources(upstream, driver)
    binding = source_identity(driver, sealed)
    suites = native_suites(upstream, driver)
    selected_cases(case for _, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    cycle = importlib.import_module('tests.test_native_cycle094')
    abi = {name: ctypes.sizeof(getattr(fixture, name)) for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    abi['Cycle'] = ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456, Cycle=216):
        raise ValueError('TEST113 public ABI changed')
    evidence = dict(scope='TEST113 selected device-failure contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        not_run=['old110 complete29 Runtime faults', 'historical whole host suites',
            'iPhone reach rate, rare-target precision and human speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci113')
    run_scope('test113-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection113Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed) != binding:
        raise ValueError('TEST113 selected tests changed sealed source')
    reject_fixture_overrides()
    evidence['sealed_sources_unchanged_after_tests'] = True
    evidence['manifest_sha256'] = sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
    (output/'test113-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST113 selected source-bound contracts; actual selected Mac boundaries and phone acceptance are separate')


if __name__ == '__main__':
    main()
