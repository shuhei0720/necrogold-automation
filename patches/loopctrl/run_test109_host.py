"""TEST109 selected real-failure entry, offer witness and passage contracts.

Current selected native units check software contracts, not phone/game acceptance.
Runtime42f2/Mac191 old-Controller4101 remains historical metadata only.
No current callback, game or iPhone acceptance proof is claimed.
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
_spec = importlib.util.spec_from_file_location('test109_shared_source_utils', HERE/'run_test108_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '7fe34ff12d31422ad89a647de183304c870d260a'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c',
    'LoopCtrlUITests/NG2Ring.c','LoopCtrlUITests/NG2Navigation.c'})
# Exact authored methods are frozen; imports are source-bound dependencies only.
CASES = (
    ('tests.test_native_dark_side109', 'NativeDarkSide109Tests', 'test109-dark-side', frozenset({
        'test_every_independent_roof_and_lower_wall_is_required',
        'test_fixed_world_chooser_uses_three_floors_then_stops_before_unknown',
        'test_inside_observed_floors_and_short_route_are_required',
        'test_mouth_is_observed_floor_and_dark_surroundings_are_not_inferred',
        'test_observed_mouth_with_roof_and_lower_boundary_adds_only_bit5',
        'test_other_orientations_and_shifted_boundaries_are_not_the_same_witness',
        'test_wrong_state_goods_gold_items_and_any_protection_do_not_gain_authority',
    }), True),
    ('tests.test_native_partial_remote109', 'NativePartialRemote109Tests', 'test109-partial-remote', frozenset({
        'test_actual_opening_exact_mask_and_binary_safe_result_are_required',
        'test_each_independent_outer_wall_cell_and_horizontal_opening_are_required',
        'test_nearby_material_and_each_protected_role_cannot_use_remote_palette',
        'test_original_deadline_and_cancel_bound_remote_palette_credit',
        'test_remote_palette_keeps_classified_anchor_then_future_entry_ack',
        'test_reserved_palette_observation_keeps_original_ticket_and_deadline',
        'test_target_candidate_or_invalid_frame_never_create_observation_credit',
        'test_unknown_intermediate_pair_never_bridges_the_frozen_motion_proof',
    }), True),
    ('tests.test_native_open_edge109', 'NativeOpenEdge109Tests', 'test109-open-edge', frozenset({
        'test_direct_opening_keeps_visible_outer_domain_and_enters_on_new_proof',
        'test_edge_entry_target_is_held_and_second_unknown_never_repeats_move',
        'test_edge_never_resends_an_unknown_sent_input',
        'test_edge_requires_fresh_current_prefix_and_original_deadline',
        'test_icon_core_and_every_visible_search_pixel_must_remain_central',
        'test_old_unknown_entry_history_does_not_inherit_direct_opening_edge_domain',
        'test_target_upper_bound_or_name_priority_does_not_gain_edge_permission',
    }), True),
    ('tests.test_native_offer_witness109', 'NativeOfferWitness109Tests', 'test109-offer-witness', frozenset({
        'test_both_independent_causes_are_fixed_in_one_normal_producer_result',
        'test_existing_numeric_certificate_rejects_missing_positive_evidence',
        'test_half_hue_gain_texture_visibility_and_bright_bounds_are_independent',
        'test_observed_caps_all_three_lower_floors_and_exact_projection_are_required',
        'test_same_hue_textured_half_uses_the_independent_observed_full_floor',
        'test_single_offer_uses_same_local_witness_without_extending_legacy_modes',
        'test_small_non_price_fragment_does_not_count_as_a_fourth_price',
        'test_supported_extra_price_missing_price_and_fourth_item_remain_incomplete',
        'test_target_candidate_and_missing_visibility_are_never_negative',
    }), True),
    ('tests.test_native_offer_witness109', 'NativeOfferWitnessController109Tests', 'test109-offer-witness-controller', frozenset({
        'test_controller_independently_rejects_removed_floor_and_forged_cap_price_or_target',
        'test_normal_negative_requires_pause_durable_intent_restart_ack_and_new_floor',
        'test_target_candidate_and_incomplete_price_keep_restart_closed',
    }), True),
    ('tests.test_native_left_observation106', 'NativeLeftObservation106Tests', 'test106-left-observation', frozenset({
        'test_dark_left_gap_with_pillar_and_both_boundary_ends_adds_only_bit8',
        'test_each_positive_wall_floor_and_dark_gap_is_independent',
        'test_fixed_world_chooser_uses_only_three_observed_floors_then_holds',
        'test_observed_left_floor_mouth_with_independent_long_wall_adds_only_bit5',
        'test_state_gold_goods_protection_and_other_sides_cannot_gain_authority',
    }), True),
    ('tests.test_native_split_roof108', 'NativeSplitRoof108Tests', 'test108-split-roof', frozenset({
        'test_dark_mouth_outside_and_inboard_are_not_inferred_or_walked',
        'test_each_independent_wall_is_required_without_accepting_doors_or_hidden_walls',
        'test_every_observed_floor_and_short_route_is_required',
        'test_observed_flanks_outer_cap_and_both_boundaries_support_only_bit0',
        'test_rotated_reflected_transposed_and_shifted_boundaries_are_not_the_same_witness',
        'test_weaker_near_roof_or_single_boundary_does_not_replace_independent_support',
        'test_wrong_state_gold_goods_any_protection_and_items_cannot_gain_authority',
    }), True),
    ('tests.test_native_partial_refresh104', 'NativePartialRefresh104Tests', 'test104-partial-refresh', frozenset({
        'test_far_floor_to_dirt_rebinds_observe_more_before_fresh_result_and_new_static',
        'test_far_refresh_does_not_consume_or_restore_old_exposed_item_once_allowance',
        'test_left_opening_two_real_left_moves_then_down_uses_current_normal_jobs',
        'test_new_candidate_target_or_unsafe_unknown_holds_and_pending_source_never_refreshes',
        'test_new_far_gold_and_material_refresh_withdraw_credit_and_reserved_ticket',
        'test_refresh_rejects_lost_gold_item_protection_near_material_and_nonzero_motion',
        'test_refresh_requires_fresh_stable_prefix_original_parent_and_control_owner',
        'test_repeated_same_prefix_refresh_keeps_first_parent_and_requires_each_new_result',
    }), True),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test097-partial-entry', frozenset({
        'test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit',
        'test_nearby_or_protected_material_and_other_stone_destinations_are_not_quiet',
        'test_new_ticket_keeps_its_frozen_bounds_and_completed_opening_id_does_not_revive',
        'test_original_prefix_continuation_horizon_and_cancel_remain_required',
        'test_partial_relation_still_requires_same_decision_and_independent_strict_zero',
        'test_remote_stone_to_dirt_keeps_observation_credit',
        'test_shield_permission_requires_actual_same_direction_opening_and_unchanged_gold',
    }), True),
    ('tests.test_native_partial_roles107', 'NativePartialRoles107Tests', 'test107-partial-roles', frozenset({
        'test_growth_over_supported_top_gold_composes_with_far_palette_before_new_job_and_move',
        'test_mixed_refresh_real_up_and_current_normal_producer_reach_durable_restart',
        'test_new_job_target_candidate_and_missing_independent_zero_hold',
        'test_remote_protected_non_item_top_exposure_reclassifies_once_without_old_credit',
        'test_role_support_geometry_authority_and_original_deadline_are_required',
        'test_supported_roles_translate_to_the_other_observed_top_columns',
        'test_top_alias_reduction_and_old_shielded_palette_share_one_static_proof',
    }), True),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test101-full-framing', frozenset({
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
    ('tests.test_native_open_full108', 'NativeOpenFull108Tests', 'test108-open-full', frozenset({
        'test_a_second_unknown_does_not_restore_the_one_step_credit',
        'test_direct_opening_full_unknown_waits_for_independent_zero_then_enters_once',
        'test_new_candidate_after_actual_entry_is_held_without_restarting',
        'test_old_unknown_entry_history_does_not_borrow_the_direct_opening_geometry',
        'test_opening_bracket_positive_floor_and_exact_projection_are_required',
        'test_source_prefix_deadline_cancel_and_unknown_input_do_not_gain_new_authority',
        'test_target_candidate_upper_bound_and_strong_word_precede_new_entry',
    }), True),
    ('tests.test_native_full_wait108', 'NativeFullWait108Tests', 'test108-full-wait', frozenset({
        'test_invalid_stage_two_revokes_phase_preparation_and_proof_without_rebinding',
        'test_known_motion_or_changed_door_permanently_refuses_later_anchor_zero',
        'test_material_or_raw_unknown_waits_then_direct_anchor_zero_creates_a_new_current_model',
        'test_new_goods_gold_protection_and_nonfull_scenes_never_become_wait_credit',
        'test_reserved_stage_three_does_not_gain_a_wait_or_resend',
        'test_two_later_zero_frames_cannot_bridge_unknown_from_the_fixed_anchor',
        'test_wait_original_deadline_expires_with_no_further_capture_or_only_prefix_discards',
    }), True),
    ('tests.test_native_offer_coverage104', 'NativeOfferCoverage104Tests', 'test104-offer-coverage', frozenset({
        'test_all_strip_templates_and_strong_name_keep_target_priority',
        'test_every_positive_support_floor_item_cap_and_gold_context_is_required',
        'test_legacy_wall_mutations_do_not_gain_missing_positive_price_floors',
        'test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards',
        'test_observed_price_floor_footprint_certifies_without_outside_wall_shape',
        'test_raw_caps_prices_extra_groups_and_lower_container_price_remain_observed',
        'test_state_mapping_bounds_deadline_cancel_and_legacy_modes_are_preserved',
        'test_two_real_full_faces_and_no_extra_component_remain_required',
    }), True),
    ('tests.test_native_single_offer108', 'NativeSingleOffer108Tests', 'test108-single-offer', frozenset({
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
    ('tests.test_native_single_offer108', 'NativeSingleOfferController108Tests', 'test108-single-offer-controller', frozenset({
        'test_controller_rechecks_observed_boundary_floor_projection_and_forged_certificate',
        'test_existing_closed_price_certificate_is_independently_adopted',
        'test_normal_producer_joins_durable_pause_intent_restart_ack_and_next_floor',
        'test_target_candidate_and_unobserved_price_never_receive_restart_authority',
    }), True),
    ('tests.test_native_closed_price106', 'NativeClosedPrice106Tests', 'test106-closed-price', frozenset({
        'test_already_registered_gray_and_purple_closed_bodies_share_the_price_proof',
        'test_each_existing_shop_shape_uses_the_same_closed_price_adapter',
        'test_integer_support_boundaries_are_exact_for_both_masks_and_all_existing_identities',
        'test_observed_closed_price_and_background_variation_have_separate_positive_proof',
        'test_price_complete_unknown_lower_cell_uses_the_same_versioned_identity',
        'test_target_missing_extra_price_and_damaged_closed_identity_are_held',
        'test_version_two_closed_identity_and_actual_price_pose_cannot_be_forged',
    }), True),
    ('tests.test_native_closed_price_controller106', 'NativeClosedPriceController106Tests', 'test106-closed-price-controller', frozenset({
        'test_c_independently_checks_integer_coverage_boundaries_and_lattice_for_every_identity',
        'test_canonical_closed_identities_reach_durable_restart_in_each_offer_slot',
        'test_complete_prices_and_unknown_closed_lower_cell_keep_version_two_identity',
        'test_normal_closed_price_reaches_durable_intent_restart_ack_and_next_floor',
        'test_target_candidate_and_forged_closed_price_never_restart',
    }), True),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_dark_side109',
    'tests.test_native_offer_witness109',
    'tests.test_native_open_edge109',
    'tests.test_native_partial_remote109',
})
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_closed_offer105',
    'tests.test_native_closed_price106',
    'tests.test_native_closed_price_controller106',
    'tests.test_native_controller',
    'tests.test_native_corner_vantage086',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_dark_side109',
    'tests.test_native_full_framing101',
    'tests.test_native_full_wait108',
    'tests.test_native_handoff099',
    'tests.test_native_left_observation106',
    'tests.test_native_motion067',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_observed_mouth104',
    'tests.test_native_observed_shop_controller104',
    'tests.test_native_occluded_corner097',
    'tests.test_native_offer_controller105',
    'tests.test_native_offer_coverage104',
    'tests.test_native_offer_witness109',
    'tests.test_native_open_edge109',
    'tests.test_native_open_full108',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_refresh104',
    'tests.test_native_partial_remote109',
    'tests.test_native_partial_roles107',
    'tests.test_native_passage072',
    'tests.test_native_passage_navigation072',
    'tests.test_native_perception',
    'tests.test_native_preserved_sparse097',
    'tests.test_native_recovery',
    'tests.test_native_revealed_gate079',
    'tests.test_native_revealed_motion108',
    'tests.test_native_revealed_singleton096',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_shadow_passage094',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_gate081',
    'tests.test_native_side_opening098',
    'tests.test_native_side_shop100',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_split_roof108',
    'tests.test_native_split_shadow095',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_supported_mouth084',
    'tests.test_native_vantage_replan108',
    'tests.test_target_assessment087',
)
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
PRODUCT_PATHS = ('necroprobe/test109.py','test_109.sh')
LEGACY_FIXTURE_EXCEPTION = None
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,*shared.PRODUCT_PATHS,*PRESERVED_LOCAL_PYTHON,
    'patches/loopctrl/run_test107_host.py','patches/loopctrl/test_device_ci107.py',
    'patches/loopctrl/run_test108_host.py','patches/loopctrl/test_device_ci108.py',
    'tools/ring_native/generate_non_target094.py',
    'necroprobe/closed_container_features105.json','tools/ring_native/generate_closed105.py',
    *(name.replace('.', '/')+'.py' for name in shared.CORE_MODULES))
RUNTIME_PROOF_POLICY = 'historical_only_unchanged_runtime'
UNCHANGED_RUNTIME_SHA256 = '42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8'
BASELINE_CONTROLLER_SHA256 = '8f07146971b35ff77f754c3821eeb50b77427a541a670e11ecef95dd3300ad41'
HISTORICAL_CONTROLLER_SHA256 = '4101c6e4fa06d488aead1bad01b338f30afee328e99d66281c997ad643a8c63e'

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO109_') for name in os.environ):
        raise ValueError('TEST109 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST109 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST109 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST109 new focused scopes are missing')


native_delta = shared.native_delta

def preserved_fixture_identity(path, current, original):
    """Preserve every old byte except a separately approved, source-bound method."""
    exception=LEGACY_FIXTURE_EXCEPTION
    if exception is None or path!=exception['path']:
        return retained_identity(current,original)
    if sha(original)!=exception['baseline_sha256'] or sha(current)!=exception['approved_sha256']:
        raise ValueError('TEST109 unreviewed legacy fixture revision')
    trees=[ast.parse(raw.decode()) for raw in (original,current)]
    classes=[next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==exception['klass']) for tree in trees]
    methods=[[n for n in klass.body if isinstance(n,ast.FunctionDef)] for klass in classes]
    if [n.name for n in methods[0]]!=[n.name for n in methods[1]]:
        raise ValueError('TEST109 legacy method markers changed')
    selected=[next(n for n in group if n.name==exception['method']) for group in methods]
    old,new=selected
    if old.decorator_list or new.decorator_list or ast.dump(old.args)!=ast.dump(new.args):
        raise ValueError('TEST109 legacy method interface changed')
    old_lines,new_lines=[raw.decode().splitlines(keepends=True) for raw in (original,current)]
    if old_lines[:old.lineno-1]!=new_lines[:new.lineno-1] or old_lines[old.end_lineno:]!=new_lines[new.end_lineno:]:
        raise ValueError('TEST109 bytes outside the approved legacy method changed')
    other=[[ast.dump(n,include_attributes=False) for n in group if n.name!=exception['method']] for group in methods]
    if other[0]!=other[1]:
        raise ValueError('TEST109 other legacy methods changed')
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

def runtime_history_identity(before,current):
    runtime='LoopCtrlUITests/NG2Runtime.swift';controller='LoopCtrlUITests/NG2Controller.c'
    current_controller=current.get(controller)
    if (before.get(runtime)!=UNCHANGED_RUNTIME_SHA256 or current.get(runtime)!=UNCHANGED_RUNTIME_SHA256
            or before.get(controller)!=BASELINE_CONTROLLER_SHA256
            or not isinstance(current_controller,str) or len(current_controller)!=64
            or any(char not in '0123456789abcdef' for char in current_controller)
            or current_controller in (BASELINE_CONTROLLER_SHA256,HISTORICAL_CONTROLLER_SHA256)):
        raise ValueError('TEST109 historical-only Runtime scope/source identity changed')
    return dict(policy=RUNTIME_PROOF_POLICY,runtime_sha256=UNCHANGED_RUNTIME_SHA256,
        executed_this_run=False,current_controller_execution=False,
        baseline_controller_sha256=BASELINE_CONTROLLER_SHA256,
        historical_controller_sha256=HISTORICAL_CONTROLLER_SHA256,
        current_controller_sha256=current[controller],source_reference=NATIVE_BASELINE,
        historical_mac=dict(code='2c5afa96caa3944dc376ece148d274f913880500',run=43663964487,build=191,
            executed_this_run=False,controller_sha256=HISTORICAL_CONTROLLER_SHA256,
            runtime_sha256=UNCHANGED_RUNTIME_SHA256),
        limitation='Mac191 used old101 Controller4101 with Runtime42f2. Runtime bytes remain unchanged, but this is not fresh TEST109 Controller/Navigation/Runtime execution or game acceptance.')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('109')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('109')]
    paths += ['patches/loopctrl/run_test108_host.py', 'patches/loopctrl/test_device_ci108.py']
    paths += [p.decode() for p in git(driver,'ls-tree','-r','--name-only','-z',NATIVE_BASELINE,'legacy/r12').split(b'\0') if p]
    if sum(path.startswith('legacy/r12/') for path in paths) != 40:
        raise ValueError('R12 source inventory changed')
    for path in dict.fromkeys(paths):
        preserved[path] = preserved_fixture_identity(path,pinned_bytes(driver,path,code),git(driver,'show',NATIVE_BASELINE+':'+path))
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101','necroprobe.test102','necroprobe.test103','necroprobe.test104','necroprobe.test105','necroprobe.test106','necroprobe.test107','necroprobe.test108','necroprobe.test109'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py', 'patches/loopctrl/run_test102_host.py', 'patches/loopctrl/run_test103_host.py', 'patches/loopctrl/run_test104_host.py', 'patches/loopctrl/run_test105_host.py', 'patches/loopctrl/run_test106_host.py', 'patches/loopctrl/run_test107_host.py', 'patches/loopctrl/run_test108_host.py', 'patches/loopctrl/run_test109_host.py',
                      'patches/loopctrl/test_device_ci109.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        runtime_proof_policy=runtime_history_identity(old,current),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        legacy_fixture_exception=LEGACY_FIXTURE_EXCEPTION,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        direct_c_compiler_binding='Finalized selected fixtures compile exact source bound to the installed native seal. Compilation scope is frozen with the authored CASES; no original-image Ring replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test109-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test109-nav086-current-') as temporary:
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
            raise ValueError('TEST109 read-only companion ABI changed')
        evidence=dict(scope='TEST109 selected actual-failure entry, offer witness and passage contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'Historical086/091 current eight-source snapshots are created only if an explicit related scope requires them',
                     'old095/096/097/098/099/100/101/102/103/104/105/106/107 complete host suites and Runtime/Mac callbacks; historical Mac191 is not current Controller proof',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci109')
        run_scope('test109-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection109Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test109-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST109 selected native contracts against exact sealed IPA sources; unchanged Runtime proof is historical and phone acceptance is not run')


if __name__=='__main__':main()
