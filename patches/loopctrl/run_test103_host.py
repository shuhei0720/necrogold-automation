"""TEST103 selected UNKNOWN visual wait, stationary proof and single-sign shop contracts.

Current selected C/Navigation/Ring units test software contracts, not iPhone/game acceptance.
Runtime42f2 is byte-preserved; Mac191 used old Controller4101 and remains historical.
No fresh Runtime/current-Controller/Navigation callback proof is claimed.
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
_spec = importlib.util.spec_from_file_location('test103_shared_source_utils', HERE/'run_test102_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '4df0a6381e6697339204b1b9c8be2f9513aa07a7'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c','LoopCtrlUITests/NG2Ring.c','LoopCtrlUITests/NG2Navigation.c','LoopCtrlUITests/NG2Core.h'})
# Author method inventories and exact import closure are pending.
CASES = (
    ('tests.test_native_unknown_wait103', 'NativeUnknownWait103Tests', 'test103-unknown-wait', frozenset({
        'test_cancel_foreground_lock_and_owner_guards_cannot_resume_after_unknown',
        'test_expired_unknown_pause_and_pre_ack_capture_keep_the_failure_path',
        'test_later_full_floor_with_proven_unknown_motion_binds_fresh_candidate_without_old_credit',
        'test_repeated_unknown_uses_one_phase_failure_and_never_renews_visual_deadline_or_attempts',
        'test_transient_unknown_preserves_ack_source_deadline_then_fresh_floor_resolves_same_move',
        'test_unknown_synth_never_turns_an_unknown_screen_into_wait_or_new_input',
        'test_unstable_wrong_prefix_and_old_capture_do_not_mutate_the_ack_wait',
    }), True),
    ('tests.test_native_plural_wait103', 'NativePluralWait103Tests', 'test103-plural-wait', frozenset({
        'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
        'test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero',
        'test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back',
        'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
        'test_plural_proof_needs_independent_stable_current_prefix_capture',
        'test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket',
    }), True),
    ('tests.test_native_single_sign_controller103', 'NativeSingleSignController103Tests', 'test103-single-sign-controller', frozenset({
        'test_complete_prices_caps_binary_domain_and_positive_veto_are_not_relaxed',
        'test_fixed_gold_items_caps_and_same_row_door_are_recomputed_despite_equal_count',
        'test_normal_policy7_producer_reaches_durable_intent_restart_ack_and_next_floor',
        'test_normal_target_and_incomplete_results_never_acquire_restart_authority',
        'test_observed_same_row_seven_gold_one_full_sign_and_merchant_have_independent_authority',
        'test_one_full_left_face_zero_absent_face_and_real_merchant_are_all_mandatory',
    }), True),
    ('tests.test_native_bottom_shop_controller103', 'NativeBottomShopController103Tests', 'test103-bottom-shop-controller', frozenset({
        'test_every_fixed_gold_center_floor_item_cap_and_gate_is_independent',
        'test_normal_policy8_producer_reaches_durable_intent_restart_ack_and_next_floor',
        'test_normal_target_and_incomplete_results_never_acquire_restart_authority',
        'test_ten_fixed_gold_bottom_entrance_and_two_full_signs_have_independent_authority',
        'test_two_full_faces_zero_glyph_merchant_and_all_numeric_target_guards_remain_strict',
    }), True),
    ('tests.test_native_clear_stationary095', 'NativeClearStationary095Tests', 'test095-clear-stationary', frozenset({
        'test_actual_gold_unknown_uses_the_original_strict_handoff_only',
        'test_cancel_or_started_unknown_cannot_reuse_the_zero_wait',
        'test_independent_clear_singleton_zero_rearms_only_a_new_future_ticket',
        'test_known_motion_or_failed_decode_cannot_fall_back_at_observation_or_begin',
        'test_original_wait_and_parent_equalities_cannot_be_renewed_by_zero_proof',
        'test_zero_proof_needs_independent_stable_current_prefix_capture',
    }), True),
    ('tests.test_native_controller', 'NativeControllerTests', 'test-native-controller', frozenset({
        'test_goods_frame_unknown_motion_is_recorded_once_without_waiting',
        'test_visual_wait_keeps_original_source_phase_walk_and_session_horizons',
    }), False),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test094-cycle', frozenset({
        'test_inflight_goods_credit_real_move_once_and_keep_unknown_motion_held',
    }), False),
    ('tests.test_native_structural_cycle096', 'NativeStructuralCycle096Tests', 'test096-structural-cycle', frozenset({
        'test_structural_numeric_certificate_still_requires_all_bounds_faces_and_observed_goods',
        'test_target_candidate_or_strong_word_in_any_original_cell_remains_a_veto',
    }), False),
    ('tests.test_native_side_shop_controller100', 'NativeSideShopController100Tests', 'test100-side-shop-controller', frozenset({
        'test_policy_price_baseline_extra_objects_and_complete_bounds_are_strict',
        'test_seven_observed_gold_side_shape_reaches_only_existing_durable_restart',
    }), False),
    ('tests.test_native_lower_shop_controller101', 'NativeLowerShopController101Tests', 'test101-lower-shop-controller', frozenset({
        'test_twelve_position_shape_mirrors_and_observed_openings_reach_durable_restart_only',
    }), False),
    ('tests.test_native_shop_controller102', 'NativeShopController102Tests', 'test102-shop-controller', frozenset({
        'test_normal_classifier_negative_runs_through_durable_intent_real_restart_ack_and_next_floor',
        'test_positive_observed_door_enclosure_and_single_top_loss_face_have_independent_authority',
    }), False),
    ('tests.test_native_plural_stationary103', 'NativePluralStationary103Tests', 'test103-plural-stationary', frozenset({
        'test_all_blur_finite_absolute_bound_and_all_raw_competitors',
        'test_both_scenes_near_floor_protection_gold_goods_and_invalid_reject',
        'test_exact_old_plural_stones_and_old_dirt_cannot_be_replaced',
        'test_exactly_one_cardinal_unit_phase_and_supported_unit_axis',
        'test_fixed_world_unit_lighting_phase_adds_only_zero_qualification',
        'test_noncollinear_unique_nine_placements_and_full_hud_rois',
        'test_real_translated_procedural_world_never_qualifies_zero',
        'test_world_axis_strength_regions_and_last_lead_boundaries',
    }), True),
    ('tests.test_native_singleton_stationary095', 'NativeSingletonStationary095Tests', 'test095-singleton-stationary', frozenset({
        'test_all_raw_scores_are_finite_zero_ranked_and_inside_fallback_domain',
        'test_blur_zero_absolute_bound_and_all_seventy_two_finite_competitors',
        'test_common_noncollinear_dirt_support_and_unique_nine_placements_are_required',
        'test_exact_old_singleton_is_preserved_and_new_stone_cannot_replace_it',
        'test_full_source_and_projected_hud_sample_rois_are_excluded',
        'test_near_floor_all_protection_gold_goods_invalid_scenes_and_direction_reject',
        'test_single_old_stone_fixed_surface_adds_only_readonly_zero_evidence',
        'test_world_axis_strength_regions_and_last_competitor_lead_boundaries',
    }), True),
    ('tests.test_native_terrain_axis091', 'NativeTerrainAxis091Tests', 'test091-terrain-axis', frozenset({
        'test_blur_axis_ambiguity_and_single_region_cannot_supply_unit',
        'test_complete_nonhud_old_terrain_and_unique_translation_are_required',
        'test_finite_unit_scope_and_original_known_results_are_preserved',
        'test_public_unit_requires_new_independent_axis_proof',
    }), True),
    ('tests.test_native_stationary_texture085', 'NativeStationaryTexture085Tests', 'test085-stationary-texture', frozenset({
        'test_observed_terrain_goods_gold_door_and_protection_guards',
        'test_old_unit_tween_reverse_and_opening_outputs_are_never_overwritten',
        'test_original_numeric_support_agreement_bands_and_competition_boundaries',
        'test_phase_alias_noise_and_blur_dependency_counterexamples_stay_unknown',
        'test_public_clear_floor_zero_requires_independent_stationary_evidence',
    }), False),
    ('tests.test_native_gold_stationary092', 'NativeGoldStationary092Tests', 'test092-gold-stationary', frozenset({
        'test_complete_nonhud_old_terrain_gold_and_safe_floor_are_required',
        'test_known_motion_and_nonzero_surfaces_cannot_be_overwritten',
        'test_lighting_drift_with_stable_gold_confirms_only_zero',
        'test_raw_finite_zero_and_independent_texture_competition_are_required',
    }), True),
    ('tests.test_native_single_sign_shop103', 'NativeSingleSignShop103Tests', 'test103-single-sign-shop', frozenset({
        'test_each_fixed_gold_item_cap_and_observed_doorway_is_independent',
        'test_full_face_size_count_roi_and_no_extra_component_remain_required',
        'test_merchant_is_real_strong_bounded_evidence_not_an_optional_field',
        'test_numeric_certificate_rejects_missing_face_fake_merchant_and_old_binary_mutations',
        'test_one_real_full_face_and_strong_merchant_certify_only_complete_strip',
        'test_raw_endcaps_prices_extra_groups_and_missing_items_are_held',
        'test_state_mapping_deadline_cancel_and_legacy_modes_preserve_old_authority',
        'test_target_full_strip_and_strong_name_keep_positive_priority',
    }), True),
    ('tests.test_native_bottom_shop103', 'NativeBottomShop103Tests', 'test103-bottom-shop', frozenset({
        'test_every_fixed_gold_center_floor_item_cap_and_gate_is_required',
        'test_full_strip_target_and_strong_word_remain_held',
        'test_mapping_state_deadline_cancel_and_legacy_modes_keep_old_rules',
        'test_numeric_certificate_rejects_forgery_with_same_old_binary_guards',
        'test_ten_fixed_gold_bottom_entry_and_two_full_faces_have_separate_proof',
        'test_two_complete_faces_not_partial_missing_shifted_or_extra_are_required',
    }), True),
    ('tests.test_native_structural_shop096', 'NativeStructuralShop096Tests', 'test096-structural-shop', frozenset({
        'test_certificate3_retains_all_numeric_identity_and_coverage_guards',
        'test_complete_board_roi_and_scene_support_must_fit_observed_bounds',
        'test_complete_structure_authorizes_without_shop_or_merchant_pixel_identity',
        'test_each_required_gold_cell_and_opening_must_be_observed',
        'test_half_cell_ties_are_rejected_on_both_signed_axes',
        'test_items_caps_scene_state_and_positive_gold_are_independent_requirements',
        'test_legacy_modes_and_policy2_fallback_keep_their_existing_authority',
        'test_mirrored_openings_and_projected_protection_are_preserved',
        'test_partial_body_missing_price_extra_board_and_absent_item_are_held',
        'test_target_between_prices_and_observed_name_veto_are_never_masked',
        'test_unmatched_items_is_preserved_diagnostic_only_under_policy3',
        'test_wider_extra_observed_sign_is_not_discarded_by_selected_face_roi',
    }), True),
    ('tests.test_native_side_shop100', 'NativeSideShop100Tests', 'test100-side-shop', frozenset({
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
    ('tests.test_native_shop_geometry101', 'NativeShopGeometry101Tests', 'test101-shop-geometry', frozenset({
        'test_caps_items_state_and_mapping_keep_original_shadowed_view_unknown',
        'test_complete_pixels_prices_and_unique_faces_are_independent_requirements',
        'test_each_positive_wall_and_opening_is_required_despite_equal_gold_count',
        'test_full_strip_target_and_strong_word_keep_positive_priority',
        'test_numeric_certificate_and_old_policies_remain_distinct',
        'test_observed_twelve_cell_lower_opening_authorizes_only_complete_strip',
    }), True),
    ('tests.test_native_shop_coverage102', 'NativeShopCoverage102Tests', 'test102-shop-coverage', frozenset({
        'test_bottom_alignment_selects_one_canonical_row_without_deleting_evidence',
        'test_bottom_door_and_top_prefix_have_independent_complete_proof',
        'test_cancel_deadline_and_legacy_modes_keep_original_authority',
        'test_certificate6_rechecks_every_existing_numeric_and_binary_guard',
        'test_complete_prices_caps_and_extra_boards_are_independent',
        'test_each_twelve_fixed_gold_and_door_is_required_despite_remote_count',
        'test_existing_size_count_thresholds_are_not_lowered',
        'test_mirrors_interior_doors_and_observed_side_openings',
        'test_prefix_faces_preserve_anchor_width_bottom_and_unique_components',
        'test_scene_items_caps_states_and_half_cell_mapping_are_required',
        'test_target_icon_and_strong_word_keep_positive_priority',
        'test_two_independently_complete_rows_are_not_unique_coverage',
    }), True),
)
REQUIRED_NEW_SCOPES = frozenset({'tests.test_native_unknown_wait103', 'tests.test_native_plural_wait103', 'tests.test_native_single_sign_controller103', 'tests.test_native_bottom_shop_controller103', 'tests.test_native_plural_stationary103', 'tests.test_native_single_sign_shop103', 'tests.test_native_bottom_shop103'})
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_bottom_shop_controller103',
    'tests.test_native_clear_stationary095',
    'tests.test_native_controller',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_gold_stationary092',
    'tests.test_native_handoff099',
    'tests.test_native_lower_shop_controller101',
    'tests.test_native_motion067',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_partial_entry097',
    'tests.test_native_passage072',
    'tests.test_native_passage_motion082',
    'tests.test_native_passage_unsent076',
    'tests.test_native_perception',
    'tests.test_native_plural_stationary103',
    'tests.test_native_plural_wait103',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_shop_controller102',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_side_shop_controller100',
    'tests.test_native_single_sign_controller103',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_singleton_stationary095',
    'tests.test_native_stationary_texture085',
    'tests.test_native_stationary_wait076',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_terrain_axis091',
    'tests.test_native_unknown_wait103',
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
PRODUCT_PATHS = ('necroprobe/test103.py','test_103.sh')
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,*shared.PRODUCT_PATHS,*PRESERVED_LOCAL_PYTHON,
    'patches/loopctrl/run_test102_host.py','patches/loopctrl/test_device_ci102.py',
    *(name.replace('.', '/')+'.py' for name in shared.CORE_MODULES))
RUNTIME_PROOF_POLICY = 'historical_only_unchanged_runtime'
UNCHANGED_RUNTIME_SHA256 = '42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8'
BASELINE_CONTROLLER_SHA256 = '8c74aa3e931d732af3d88dc52c080ad7c04b2ba9bc1607258cbe9e5df1ea5b11'
HISTORICAL_CONTROLLER_SHA256 = '4101c6e4fa06d488aead1bad01b338f30afee328e99d66281c997ad643a8c63e'

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO103_') for name in os.environ):
        raise ValueError('TEST103 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST103 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST103 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST103 new focused scopes are missing')


native_delta = shared.native_delta

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
        raise ValueError('TEST103 historical-only Runtime scope/source identity changed')
    return dict(policy=RUNTIME_PROOF_POLICY,runtime_sha256=UNCHANGED_RUNTIME_SHA256,
        executed_this_run=False,current_controller_execution=False,
        baseline_controller_sha256=BASELINE_CONTROLLER_SHA256,
        historical_controller_sha256=HISTORICAL_CONTROLLER_SHA256,
        current_controller_sha256=current[controller],source_reference=NATIVE_BASELINE,
        historical_mac=dict(code='2c5afa96caa3944dc376ece148d274f913880500',run=43663964487,build=191,
            executed_this_run=False,controller_sha256=HISTORICAL_CONTROLLER_SHA256,
            runtime_sha256=UNCHANGED_RUNTIME_SHA256),
        limitation='Mac191 used old101 Controller4101 with Runtime42f2. Runtime bytes remain unchanged, but this is not fresh TEST103 Controller/Navigation/Runtime execution or game acceptance.')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('103')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('103')]
    paths += ['patches/loopctrl/run_test102_host.py', 'patches/loopctrl/test_device_ci102.py']
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101','necroprobe.test102','necroprobe.test103'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py', 'patches/loopctrl/run_test102_host.py', 'patches/loopctrl/run_test103_host.py',
                      'patches/loopctrl/test_device_ci103.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        runtime_proof_policy=runtime_history_identity(old,current),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        direct_c_compiler_binding='Controller/Navigation fixtures use installed CORE; selected old086/091 Nav harnesses use eight exact current sealed files. Ring procedural producers compile pinned driver native sources whose hashes match the installed seal. No original-image Ring replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test103-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test103-nav086-current-') as temporary:
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
            raise ValueError('TEST103 read-only companion ABI changed')
        evidence=dict(scope='TEST103 selected UNKNOWN visual wait, stationary proof and single-sign shop contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'Historical086/091 current eight-source snapshots are created only if an explicit related scope requires them',
                     'old095/096/097/098/099/100/101/102 complete host suites and Runtime/Mac callbacks; historical Mac191 is not current Controller proof',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci103')
        run_scope('test103-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection103Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test103-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST103 selected C/Navigation/Ring contracts against exact sealed IPA sources; unchanged Runtime proof is historical and phone acceptance is not run')


if __name__=='__main__':main()
