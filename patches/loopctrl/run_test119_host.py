"""TEST119 exact source and boundary selection; pending scopes fail closed."""
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
_spec = importlib.util.spec_from_file_location('test119_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = '64f7b4f518905a02ff70656f18b5bc197f3e83f7'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Ring.c',
    'LoopCtrlUITests/NG2Perception.c'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset({
    '.github/workflows/loopctrl-geometry.yml',
    'necroprobe/campaign116.py',
    'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/ngg2-manifest.json',
    'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/ngg2/NG2Controller.c',
    'patches/loopctrl/ngg2/NG2Perception.c',
    'patches/loopctrl/ngg2/NG2Ring.c',
    'patches/loopctrl/verify_package.py',
    'tests/test_continuous_client117.py',
    'tests/test_continuous_client118.py',
})
NEW_PATHS = frozenset({
    'necroprobe/test119.py',
    'patches/loopctrl/check_runtime119.py',
    'patches/loopctrl/generate_shop119_queue_pixels.py',
    'patches/loopctrl/ngg2_runtime119_queue_fixture.c',
    'patches/loopctrl/ngg2_runtime119_queue_fixture.h',
    'patches/loopctrl/ngg2_runtime119_tests.swift',
    'patches/loopctrl/run_test119_host.py',
    'patches/loopctrl/run_test119_python39.py',
    'patches/loopctrl/test_device_ci119.py',
    'test_119.sh',
    'tests/test_continuous_client119.py',
    'tests/test_native_empty_corridor119.py',
    'tests/test_native_entered_current119.py',
    'tests/test_native_passage_source119.py',
    'tests/test_native_side_price119.py',
    'tests/test_native_torch_floor119.py',
})
# Explicit authored methods and directly related regressions, not whole old suites.
CASES = (
    ('tests.test_native_passage_source119', 'NativePassageSource119Tests', 'test119-native-NativePassageSource119Tests', frozenset({
        'test_begun_ACK_and_unknown_inputs_do_not_become_route_retries',
        'test_changed_goods_protection_next_floor_or_unproved_motion_cannot_use_wait_downgrade',
        'test_refined_unsent_route_change_waits_then_independent_proof_uses_new_physical_beat',
        'test_route_wait_repeated_unknown_proof_does_not_renew_W_or_credit',
        'test_wait_cancel_and_replacement_owner_guard_preserve_zero_additional_inputs',
        'test_wrong_prefix_or_unstable_capture_cannot_retire_or_replace_the_live_ticket',
    }), True),
    ('tests.test_native_side_price119', 'NativeSidePrice119Tests', 'test119-native-NativeSidePrice119Tests', frozenset({
        'test_complete_low_price_and_same_column_small_fragment_are_separate_evidence',
        'test_existing_scene_support_items_caps_and_extra_board_remain_required',
        'test_missing_malformed_fourth_and_split_price_cannot_disappear',
        'test_multiple_lower_tops_cannot_disagree_with_the_independent_C_selector',
        'test_target_image_and_priceless_candidate_stay_prior_to_generic_absence',
        'test_typed_lower_price_geometry_and_generic_cells_are_independently_validated',
    }), True),
    ('tests.test_native_side_price119', 'NativeSidePriceController119Tests', 'test119-native-NativeSidePriceController119Tests', frozenset({
        'test_normal_separate_price_reaches_independent_adoption_durable_restart_and_floor',
        'test_raw_scene_and_typed_price_forgeries_do_not_gain_restart_authority',
    }), True),
    ('tests.test_native_empty_corridor119', 'NativeEmptyCorridor119Tests', 'test119-native-NativeEmptyCorridor119Tests', frozenset({
        'test_remote_dirt_to_stone_preserves_empty_corridor_framing',
        'test_remote_refinement_never_replaces_local_floor_protection_or_zero',
    }), True),
    ('tests.test_native_torch_floor119', 'NativeTorchFloor119Tests', 'test119-native-NativeTorchFloor119Tests', frozenset({
        'test_compact_overlay_and_current_positive_floor_patches_recover_floor',
        'test_each_current_floor_patch_needs_colour_and_texture',
        'test_gold_rail_and_existing_nonfloor_types_remain_required',
        'test_hud_alpha_and_merchandise_priority_are_unchanged',
        'test_overlay_needs_one_dense_component_with_exact_lower_extent',
    }), True),
    ('tests.test_native_entered_current119', 'NativeEnteredCurrent119Tests', 'test119-native-NativeEnteredCurrent119Tests', frozenset({
        'test_data_two_budget_cannot_be_replenished_by_new_remote_material',
        'test_new_wall_still_needs_direct_zero_floor_and_original_bound',
        'test_no_unit_floor_or_identity_shortcut',
        'test_original_unit_without_revealed_halo_binds_current_data_once',
        'test_pending_candidate_and_target_win_before_queued_source',
        'test_pending_remote_wall_drains_then_owns_data_and_one_fresh_observation',
        'test_visual_deadline_is_original_and_inclusive',
    }), True),
    ('tests.test_native_passage115', 'NativePassageSource115Tests', 'test119-native-NativePassageSource115Tests', frozenset({
        'test_clear_passage_presend_refresh_reissues_same_physical_ticket_and_epoch',
        'test_only_one_refinement_per_physical_ticket_and_repetitions_keep_its_source',
        'test_refinement_rejects_wrong_prefix_protection_local_material_choice_and_expiry',
        'test_started_ack_or_unknown_input_never_refreshes_or_resends',
    }), True),
    ('tests.test_native_passage_palette077', 'NativePassagePalette077Tests', 'test119-native-NativePassagePalette077Tests', frozenset({
        'test_adjacent_blocked_palette_frames_cannot_replace_original_anchor',
        'test_palette_wait_uses_fixed_wait_and_parent_deadlines',
    }), False),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test119-native-NativeStationaryWait076Tests', frozenset({
        'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority',
    }), False),
    ('tests.test_native_preinput_refresh118', 'NativePreinputRefresh118Tests', 'test119-native-NativePreinputRefresh118Tests', frozenset({
        'test_clear_passage_same_tiles_uses_new_primary_with_original_epoch',
        'test_first_step_and_started_ACK_UNKNOWN_do_not_refresh',
        'test_once_is_keyed_by_logical_epoch_not_reissued_command_ID',
    }), False),
    ('tests.test_native_side_shop100', 'NativeSideShop100Tests', 'test119-native-NativeSideShop100Tests', frozenset({
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
    ('tests.test_native_closed_price106', 'NativeClosedPrice106Tests', 'test119-native-NativeClosedPrice106Tests', frozenset({
        'test_already_registered_gray_and_purple_closed_bodies_share_the_price_proof',
        'test_each_existing_shop_shape_uses_the_same_closed_price_adapter',
        'test_integer_support_boundaries_are_exact_for_both_masks_and_all_existing_identities',
        'test_observed_closed_price_and_background_variation_have_separate_positive_proof',
        'test_price_complete_unknown_lower_cell_uses_the_same_versioned_identity',
        'test_target_missing_extra_price_and_damaged_closed_identity_are_held',
        'test_version_two_closed_identity_and_actual_price_pose_cannot_be_forged',
    }), True),
    ('tests.test_native_ring117', 'NativeRing117Tests', 'test119-native-NativeRing117Tests', frozenset({
        'test_closed_price_recovers_same_row_without_turning_partial_into_absence',
        'test_new_numeric_witness_rejects_field_forgery',
        'test_new_price_layout_has_generic_absence_and_its_own_numeric_bounds',
        'test_new_price_layout_requires_exact_projection_and_all_supporting_floors',
        'test_one_complete_face_with_observed_lower_entrance_certifies_three_offers',
        'test_original_partial_positive_search_outside_selected_strip_is_retained',
        'test_single_face_requires_each_observed_support_and_complete_merchandise',
        'test_three_independent_price_glyphs_do_not_require_identity_of_another_product',
    }), True),
    ('tests.test_native_shop117', 'NativeSingleLowerEntryController117Tests', 'test119-native-NativeSingleLowerEntryController117Tests', frozenset({
        'test_immutable_anchor_and_numeric_fields_are_rechecked_independently',
        'test_layout3_complete_certificate_translation_cannot_cross_central_pixel_domain',
        'test_layout3_rechecks_exact_anchor_and_each_separate_price_boundary',
        'test_ordinary_producer_certificate_reaches_durable_restart_and_next_floor',
        'test_shared_lower_price_geometry_reaches_independent_adoption_and_real_restart',
    }), True),
    ('tests.test_native_price_fragments118', 'NativePriceFragments118Tests', 'test119-native-NativePriceFragments118Tests', frozenset({
        'test_independent_fourth_price_at_eighteen_ink_still_rejects_absence',
        'test_lower_entry_uses_existing_eighteen_ink_rule_for_small_nonprice_fragments',
        'test_small_fragment_cannot_replace_missing_price_or_cap_visibility',
        'test_target_image_and_own_price_stay_prior_to_nonprice_fragment',
    }), True),
    ('tests.test_native_entry_corridor102', 'NativeEntryCorridor102Tests', 'test119-native-NativeEntryCorridor102Tests', frozenset({
        'test_actual_up_opening_and_completed_unknown_domain_remain_required',
        'test_item_projection_must_explain_all_protection_without_loss',
        'test_missing_dirt_or_stone_rail_never_grants_a_framing_step',
        'test_observed_row4_corridor_gets_one_future_input_then_new_candidate_job',
        'test_old097_row4_without_positive_gold_rail_still_holds',
        'test_origin_destination_and_axis_floor_are_not_inferred',
        'test_original_horizon_prefix_static_zero_and_cancel_are_never_refreshed',
        'test_source_roi_cannot_lose_potential_goods_to_viewport_or_hud',
    }), True),
    ('tests.test_native_outer_floor083', 'NativeOuterFloor083Tests', 'test119-native-NativeOuterFloor083Tests', frozenset({
        'test_each_floor_band_needs_real_colour_and_texture',
        'test_fixed_same_tile_bands_hud_and_invalid_alpha_are_not_bypassed',
        'test_full_colour_bounds_keep_warm_walls_out',
        'test_old_types_gate_and_merchandise_protection_take_precedence',
        'test_two_disjoint_current_floor_bands_recover_occluded_floor',
    }), True),
    ('tests.test_native_shadow_floor084', 'NativeShadowFloor084Tests', 'test119-native-NativeShadowFloor084Tests', frozenset({
        'test_black_entry_and_full_rgb_bounds_are_required',
        'test_black_entry_partial_floor_becomes_observed_mouth',
        'test_existing_materials_gate_goods_and_hud_keep_priority',
        'test_fixed_halves_require_95percent_black_and_90percent_visible_floor',
        'test_observed_floor_requires_original_colour_texture_and_median_r16',
    }), True),
    ('tests.test_native_perception', 'NativePerceptionTests', 'test119-native-NativePerceptionTests', frozenset({
        'test_known_floor_public_entry',
    }), False),
    ('tests.test_native_entered112', 'NativeEntered112Tests', 'test119-native-NativeEntered112Tests', frozenset({
        'test_candidate_target_and_strong_word_keep_priority_over_late_moved',
        'test_changed_items_projection_gold_or_local_floor_never_gain_refresh',
        'test_late_original_moved_updates_once_and_binds_only_fresh_full_data',
        'test_original_unknown_blocked_tween_and_expired_visual_proof_cannot_refresh',
        'test_refreshed_unknown_requires_independent_zero_then_only_one_future_observation',
        'test_unknown_input_cannot_use_late_moved_as_a_known_ack',
        'test_worker_prefix_unstable_and_cancel_cannot_reanchor',
    }), True),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test119-native-NativeFullFraming101Tests', frozenset({
        'test_later_static_requires_immutable_goods_materials_protection_and_zero',
        'test_new_move_visual_unknown_keeps_bounded_wait_without_full_shortcut_or_resend',
        'test_original_horizon_prefix_cancel_and_input_unknown_never_remint_a_move',
    }), False),
    ('tests.test_native_current_data118', 'NativeCurrentData118Tests', 'test119-native-NativeCurrentData118Tests', frozenset({
        'test_bound_positive_remains_prior_to_distant_material',
        'test_data_downgrade_unknown_stays_held_without_observation_move',
        'test_unchanged_source_keeps_existing_two_proof_observation_path',
    }), False),
    ('patches.loopctrl.test_device_ci119', 'DeviceImplementationCapability119Tests', 'test119-capability', frozenset({
        'test_119_cannot_bypass_the_existing_118_package_binding',
        'test_current_patch_adds_119_without_replacing_118',
        'test_historical_118_manifest_gets_no_unrequested_119_field',
        'test_package_has_separate_119_field_and_unchanged_118_API_and_profile',
        'test_resealed_mismatched_119_metadata_patch_or_rpc_is_rejected',
        'test_sealing_requires_one_real_119_array_entry',
    }), True),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test119-package-related', frozenset({
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
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_classification111',
    'tests.test_native_clear_stationary095',
    'tests.test_native_closed_offer105',
    'tests.test_native_closed_price106',
    'tests.test_native_controller',
    'tests.test_native_current_data118',
    'tests.test_native_current_view114',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_empty_corridor119',
    'tests.test_native_entered112',
    'tests.test_native_entered_current119',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_framing101',
    'tests.test_native_goods113',
    'tests.test_native_irregular110',
    'tests.test_native_motion067',
    'tests.test_native_motion075',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_offer_coverage104',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_outer_floor083',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_partial_refresh104',
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
    'tests.test_native_price_fragments118',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring117',
    'tests.test_native_ring_bank094',
    'tests.test_native_shadow_floor084',
    'tests.test_native_shop117',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_price119',
    'tests.test_native_side_shop100',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_singleton_stationary095',
    'tests.test_native_static075',
    'tests.test_native_stationary_texture085',
    'tests.test_native_stationary_wait076',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_torch_floor119',
    'tests.test_target_assessment087',
)
MAC_CASE_GROUPS = (('check_runtime119.py',('entered_current_queue',)),)
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh',
    'necroprobe/test119.py', 'test_119.sh')
PRESERVED_PATHS = (*shared.UNCHANGED_CONTINUATION_PATHS,
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2Raster.swift', 'patches/loopctrl/ngg1.patch',
    'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    device_fixes119_capability='necrogold_native_device_fixes119_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST119 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED:
        raise ValueError('TEST119 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES)):
        raise ValueError('TEST119 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST119 empty or duplicate selected native scope')
    if MAC_CASE_GROUPS != (('check_runtime119.py',('entered_current_queue',)),):
        raise ValueError('TEST119 requires exactly its entered-current queue callback scope')


def native_inventory(old, current):
    """Check the complete sealed inventory before any selected C tests run."""
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST119 exact native changed/added inventory differs')
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
        raise ValueError('TEST119 installed source/API/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test119_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST119 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST119 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_119.sh').strip():
        raise ValueError('TEST119 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST119 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST119 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST119 preserved source changed: '+name)
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


def run_scope(name, cases, output, evidence, *, receipt_name='test119-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test119-host-scope.json', 'test119-python39-scope.json'):
        raise ValueError('TEST119 scope receipt name is not permitted')
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
        raise ValueError('TEST119 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST119 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        not_run=['old Runtime/fault/world collections: not replayed; entered_current_queue is checked by a separate Mac step',
            'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci119')
    run_scope('test119-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection119Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST119 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test119-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST119 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
