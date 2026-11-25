"""TEST120 exact source and boundary selection; pending scopes fail closed."""
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
_spec = importlib.util.spec_from_file_location('test120_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = '1d9a0a430b90e85910696eef8a4ac2d99e15ab00'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset({
    '.github/workflows/loopctrl-geometry.yml',
    'necroprobe/campaign116.py',
    'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/ngg2-manifest.json',
    'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/ngg2/NG2Controller.c',
    'patches/loopctrl/ngg2/NG2Navigation.c',
    'patches/loopctrl/verify_package.py',
    'tests/test_continuous_client117.py',
    'tests/test_continuous_client118.py',
    'tests/test_continuous_client119.py',
})
# Explicit authored files; pending scopes still prevent any fixture execution.
NEW_PATHS = frozenset({
    'necroprobe/test120.py',
    'patches/loopctrl/check_runtime120.py',
    'patches/loopctrl/generate_shop120_partial_pixels.py',
    'patches/loopctrl/ngg2_runtime120_partial_fixture.c',
    'patches/loopctrl/ngg2_runtime120_partial_fixture.h',
    'patches/loopctrl/ngg2_runtime120_tests.swift',
    'patches/loopctrl/run_test120_host.py',
    'patches/loopctrl/run_test120_python39.py',
    'patches/loopctrl/test_device_ci120.py',
    'test_120.sh',
    'tests/test_continuous_client120.py',
    'tests/test_native_route_observation120.py',
    'tests/test_native_partial_begin120.py',
    'tests/test_native_navigation120.py',
})
# Explicit authored methods and directly related regressions, not whole old suites.
CASES = (
    ('tests.test_native_route_observation120', 'NativeRouteObservation120Tests', 'test120-native-NativeRouteObservation120Tests', frozenset({
        'test_gold_vantage_orthogonal_route_waits_for_independent_proof_and_future_id',
        'test_near_closed_bracket_uses_fresh_id_with_original_physical_beat',
        'test_near_closed_fresh_rejects_unsafe_bracket_palette_and_motion',
        'test_route_wait_never_renews_original_W_or_parent',
        'test_route_wait_requires_independent_current_prefix_and_strict_zero',
        'test_started_or_consumed_ticket_cannot_rearm_route_wait',
        'test_stationary_handoff_rejects_missing_current_zero_and_unsafe_route',
        'test_stationary_target_change_retires_old_unknown_source_until_independent_new_anchor',
        'test_vantage_recipe_rejects_unrelated_material_and_protection_changes',
    }), True),
    ('tests.test_native_partial_begin120', 'NativePartialBegin120Tests', 'test120-native-NativePartialBegin120Tests', frozenset({
        'test_candidate_job_owner_cancel_and_original_deadline_preempt_begin',
        'test_each_identity_full_scene_and_epoch_mismatch_uses_fallback_or_refuses',
        'test_new_static_or_nonzero_observation_cannot_use_the_previous_fact',
        'test_reserved_partial_new_current_reuses_zero_without_changing_the_move',
        'test_stale_id_is_inert_true_begin_consumes_and_post_getter_does_not_recalculate',
        'test_unproved_or_discarded_current_keeps_the_old_normal_motion',
    }), True),
    ('tests.test_native_navigation120', 'NativeCappedLeft120Tests', 'test120-native-NativeCappedLeft120Tests', frozenset({
        'test_cap_and_independent_boundaries_merit_only_the_fixed_left_bit5',
        'test_each_wall_and_outer_cap_is_required_without_erasing_legacy_candidates',
        'test_every_inside_floor_and_unknown_outside_are_required',
        'test_old_nonzero_masks_win_even_when_the_new_witness_also_matches',
        'test_scene_goods_gold_item_protection_and_ordinary_door_alone_do_not_qualify',
        'test_unchanged_chooser_uses_four_known_floors_and_stops_before_the_opaque_mouth',
    }), True),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test120-native-NativePassageNavigation072Tests', frozenset({
        'test_candidate_bits_cover_annotated_families_and_multiple_mouths',
        'test_chooser_rejects_unsafe_steps_invalid_world_targets_and_unreachable_floor',
        'test_fixed_second_mouth_remains_reachable_across_the_initial_room',
        'test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps',
        'test_invalid_start_gold_goods_ordinary_exits_and_protection_do_not_explore',
        'test_shadowed_mouth_requires_outside_floor_and_wall_line_support',
        'test_shop_chooser_stays_separate_and_null_outputs_fail_closed',
        'test_unknown_outside_uses_a_monotone_observed_vantage_then_new_view',
    }), True),
    ('tests.test_native_occluded_corner097', 'NativeOccludedCorner097Tests', 'test120-native-NativeOccludedCorner097Tests', frozenset({
        'test_elbow_requires_each_observed_turn_wall_floor_and_unknown_direct_outside',
        'test_fixed_world_chooser_advances_only_existing_floor_and_holds_before_unknown',
        'test_left_elbow_uses_diagonal_outside_floor_without_inventing_direct_outside_floor',
        'test_old_mouths_shadows_corners_and_unrelated_sides_keep_original_masks',
        'test_scene_central_floor_goods_gold_all_protection_and_abi_guards_are_preserved',
        'test_upper_dark_portal_and_inside_materials_do_not_authorize_walls_doors_or_hidden_floor',
        'test_upper_requires_independent_outer_roof_and_left_boundary_positive_walls',
        'test_upper_shadow_retains_floor_or_unknown_inside_and_mixed_opaque_wall_support',
    }), True),
    ('tests.test_native_solid_corner098', 'NativeSolidCorner098Tests', 'test120-native-NativeSolidCorner098Tests', frozenset({
        'test_each_positive_corner_wall_exterior_and_hidden_front_is_required',
        'test_fixed_mouth_approach_uses_four_floor_steps_and_holds_at_solid_corner',
        'test_old_candidate_shapes_and_masks_are_unchanged',
        'test_short_existing_floor_vantage_and_all_protections_are_required',
        'test_solid_corner_exterior_floor_adds_only_fixed_left_upper_hypothesis',
        'test_state_goods_gold_item_and_noncanonical_orientations_keep_old_scope',
    }), True),
    ('tests.test_native_lower_fringe100', 'NativeLowerFringe100Tests', 'test120-native-NativeLowerFringe100Tests', frozenset({
        'test_every_positive_wall_and_floor_witness_is_required',
        'test_existing_mouth_corner_and_shadow_masks_are_preserved',
        'test_fixed_world_chooser_uses_four_observed_floor_steps_then_holds_at_wall',
        'test_observed_lower_exterior_floor_retains_only_fixed_left_bit9',
        'test_short_current_floor_vantage_and_disconnected_exterior_are_required',
        'test_state_goods_gold_item_protection_and_fixed_coordinates_keep_scope',
    }), True),
    ('tests.test_native_navigation116', 'NativeCappedNeck116Tests', 'test120-native-NativeCappedNeck116Tests', frozenset({
        'test_both_observed_neck_cells_and_reachable_inboard_are_required',
        'test_cap_and_both_lateral_wall_segments_are_independent_required_evidence',
        'test_capped_observed_necks_keep_the_existing_world_bits_in_both_axes',
        'test_neck_refuses_goods_other_screens_and_observed_nonfloor_flanks',
        'test_outer_corner_cannot_replace_three_independent_room_boundary_walls',
        'test_unchanged_chooser_walks_only_known_floor_and_stops_at_the_outside',
    }), True),
    ('tests.test_native_navigation117', 'NativeOpaqueFringe117Tests', 'test120-native-NativeOpaqueFringe117Tests', frozenset({
        'test_complete_independent_room_does_not_change_the_fixed_view_or_open_wall',
        'test_each_external_floor_cap_boundary_and_roof_witness_is_required',
        'test_existing_chooser_uses_three_known_floor_steps_then_stops_at_the_wall',
        'test_observed_floor_bend_adds_only_its_fixed_left_mouth',
        'test_ui_goods_positive_gold_and_protected_cells_never_gain_authority',
    }), True),
    ('tests.test_native_partial_remote109', 'NativePartialRemote109Tests', 'test120-related-NativePartialRemote109Tests', frozenset({
        'test_original_deadline_and_cancel_bound_remote_palette_credit',
        'test_remote_palette_keeps_classified_anchor_then_future_entry_ack',
        'test_reserved_palette_observation_keeps_original_ticket_and_deadline',
        'test_unknown_intermediate_pair_never_bridges_the_frozen_motion_proof',
    }), False),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test120-related-NativePartialEntry097Tests', frozenset({
        'test_new_ticket_keeps_its_frozen_bounds_and_completed_opening_id_does_not_revive',
        'test_partial_relation_still_requires_same_decision_and_independent_strict_zero',
    }), False),
    ('tests.test_native_partial_framing097', 'NativePartialFraming097Tests', 'test120-related-NativePartialFraming097Tests', frozenset({
        'test_exactly_one_move_requires_new_assessment_and_cannot_reuse_old_ticket',
        'test_new_full_observation_before_framing_move_gets_new_normal_job',
    }), False),
    ('tests.test_native_upper_begin118', 'NativeUpperBegin118Tests', 'test120-related-NativeUpperBegin118Tests', frozenset({
        'test_V1_retains_its_normal_begin_motion_call',
        'test_exact_V2_pair_reuses_normal_zero_at_begin_with_newer_current',
    }), False),
    ('tests.test_native_entered_current119', 'NativeEnteredCurrent119Tests', 'test120-related-NativeEnteredCurrent119Tests', frozenset({
        'test_original_unit_without_revealed_halo_binds_current_data_once',
        'test_pending_candidate_and_target_win_before_queued_source',
    }), False),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test120-related-NativeFullFraming101Tests', frozenset({
        'test_new_full_negative_counts_once_and_uses_only_its_new_durable_source',
    }), False),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test120-related-NativeStationaryWait076Tests', frozenset({
        'test_adjacent_blocked_frames_cannot_replace_the_original_anchor',
        'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority',
        'test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit',
    }), False),
    ('tests.test_native_passage_unsent076', 'NativePassageUnsent076Tests', 'test120-related-NativePassageUnsent076Tests', frozenset({
        'test_passage_recovery_never_extends_proof_walk_or_session_budgets',
        'test_started_unknown_authority_and_changed_evidence_cannot_gain_passage_recovery',
    }), False),
    ('tests.test_native_passage_source119', 'NativePassageSource119Tests', 'test120-related-NativePassageSource119Tests', frozenset({
        'test_begun_ACK_and_unknown_inputs_do_not_become_route_retries',
        'test_refined_unsent_route_change_waits_then_independent_proof_uses_new_physical_beat',
        'test_route_wait_repeated_unknown_proof_does_not_renew_W_or_credit',
    }), False),
    ('tests.test_native_side_opening098', 'NativeSideOpening098Tests', 'test120-related-NativeSideOpening098Tests', frozenset({
        'test_eight_side_turns_retire_old_ticket_and_prepare_new_direction_without_credit',
        'test_fixed_new_anchor_cannot_be_replaced_by_transitive_zero_frames',
    }), False),
    ('tests.test_native_vantage_replan108', 'NativeVantageReplan108Tests', 'test120-related-NativeVantageReplan108Tests', frozenset({
        'test_old_full_decision_progress_once_and_session_count_cannot_be_bypassed',
        'test_only_one_remote_stone_loss_and_positive_route_opening_are_eligible',
        'test_unsent_route_is_retired_then_independent_zero_issues_only_a_new_future_ticket',
    }), False),
    ('tests.test_native_revealed_route090', 'NativeRevealedRoute090Tests', 'test120-related-NativeRevealedRoute090Tests', frozenset({
        'test_new_bracket_exception_rejects_near_palette_lost_anchors_blockers_and_nonstationary_pixels',
        'test_new_bracket_reveal_cannot_bypass_existing_run_or_chain_limits',
        'test_stationary_new_bracket_reissues_same_floor_step_without_extending_frozen_ticket',
    }), False),
    ('tests.test_native_stationary_qualification117', 'NativeStationaryQualification117Tests', 'test120-related-NativeStationaryQualification117Tests', frozenset({
        'test_exact_owned_current_Scene_begin_does_not_repeat_matchers',
        'test_novel_source_recomputes_and_wrong_prefix_cannot_reuse_old_qualification',
    }), False),
    ('tests.test_native_stationary_support117', 'NativeFixedSupport117Tests', 'test120-related-NativeFixedSupport117Tests', frozenset({
        'test_first_direct_support_stays_fixed_and_funds_only_current_zero',
    }), False),
    ('tests.test_native_stationary117', 'NativeClearProof117Tests', 'test120-related-NativeClearProof117Tests', frozenset({
        'test_clear_ready_loses_current_proof_within_original_W_without_SCREEN',
        'test_issued_but_unbegun_proof_loss_retires_new_id_once_with_original_W',
        'test_withdrawn_CLEAR_permission_keeps_original_W_equalities',
    }), False),
    ('patches.loopctrl.test_device_ci120', 'DeviceImplementationCapability120Tests', 'test120-capability', frozenset({
        'test_120_cannot_bypass_the_existing_119_package_binding',
        'test_current_patch_adds_120_without_replacing_119',
        'test_historical_119_manifest_gets_no_unrequested_120_field',
        'test_package_has_separate_120_field_and_unchanged_119_API_and_profile',
        'test_resealed_mismatched_120_metadata_patch_or_rpc_is_rejected',
        'test_sealing_requires_one_real_120_array_entry',
    }), True),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test120-package-related', frozenset({
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
# Import/source binding only; these modules are not whole-suite selections.
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_classification111',
    'tests.test_native_clear_stationary095',
    'tests.test_native_controller',
    'tests.test_native_corner_vantage086',
    'tests.test_native_current_view114',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_entered112',
    'tests.test_native_entered_current119',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_framing101',
    'tests.test_native_goods113',
    'tests.test_native_irregular110',
    'tests.test_native_lower_fringe100',
    'tests.test_native_motion067',
    'tests.test_native_motion075',
    'tests.test_native_navigation',
    'tests.test_native_navigation116',
    'tests.test_native_navigation117',
    'tests.test_native_navigation120',
    'tests.test_native_observation072',
    'tests.test_native_occluded_corner097',
    'tests.test_native_offer_coverage104',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial_begin120',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_partial_refresh104',
    'tests.test_native_partial_remote109',
    'tests.test_native_passage072',
    'tests.test_native_passage115',
    'tests.test_native_passage_navigation072',
    'tests.test_native_passage_source119',
    'tests.test_native_passage_unsent076',
    'tests.test_native_perception',
    'tests.test_native_plural_stationary103',
    'tests.test_native_plural_wait103',
    'tests.test_native_recovery',
    'tests.test_native_revealed_route090',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_route_observation120',
    'tests.test_native_shadow_passage094',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_opening098',
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
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_supported_mouth084',
    'tests.test_native_upper118',
    'tests.test_native_upper_begin118',
    'tests.test_native_upper_entry112',
    'tests.test_native_vantage_replan108',
    'tests.test_target_assessment087',
)
# The untouched pre117 SCREEN assertion fails on exact119 as well as120.
# Select the current117 original-W contract instead; do not erase or skip it.
EXCLUDED_LEGACY_METHODS = {
    'tests.test_native_stationary_wait076.NativeStationaryWait076Tests.test_ready_or_issued_unknown_does_not_reopen_the_same_wait':
        'Pre117 SCREEN expectation fails identically on exact119/current; retained unchanged, replaced by three current117 original-W proof-loss methods.',
}
MAC_CASE_GROUPS = (('check_runtime120.py',('partial_begin_dispatch',)),)
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh',
    'necroprobe/test119.py', 'test_119.sh', 'necroprobe/test120.py', 'test_120.sh')
PRESERVED_PATHS = (*shared.UNCHANGED_CONTINUATION_PATHS,
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2Raster.swift', 'patches/loopctrl/ngg1.patch',
    'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py',
    'patches/loopctrl/ngg2/NG2Perception.c', 'patches/loopctrl/ngg2/NG2Ring.c',
    'patches/loopctrl/run_test119_host.py', 'patches/loopctrl/run_test119_python39.py')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    device_fixes119_capability='necrogold_native_device_fixes119_v1',
    device_fixes120_capability='necrogold_native_device_fixes120_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST120 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED:
        raise ValueError('TEST120 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES)):
        raise ValueError('TEST120 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST120 empty or duplicate selected native scope')
    if MAC_CASE_GROUPS != (('check_runtime120.py',('partial_begin_dispatch',)),):
        raise ValueError('TEST120 requires exactly its PARTIAL begin dispatch callback scope')


def native_inventory(old, current):
    """Check the complete sealed inventory before any selected C tests run."""
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST120 exact native changed/added inventory differs')
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
        raise ValueError('TEST120 installed source/API/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test120_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST120 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST120 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_118.sh', 'test_119.sh', 'test_120.sh').strip():
        raise ValueError('TEST120 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST120 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST120 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST120 preserved source changed: '+name)
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
    return shared.native_suites(upstream, driver)


def run_scope(name, cases, output, evidence, *, receipt_name='test120-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test120-host-scope.json', 'test120-python39-scope.json'):
        raise ValueError('TEST120 scope receipt name is not permitted')
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
        raise ValueError('TEST120 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST120 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        excluded_legacy_methods=EXCLUDED_LEGACY_METHODS,
        not_run=['old Runtime/fault/world collections: not replayed; partial_begin_dispatch is checked by a separate Mac step',
            'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci120')
    run_scope('test120-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection120Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST120 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test120-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST120 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
