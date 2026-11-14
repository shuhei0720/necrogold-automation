"""TEST100 selected observed-entry, partial-rebind, candidate and shop proof contracts.

Current C/Nav/Ring/client units test software contracts, not iPhone/game acceptance.
Only one new partial-rebind Runtime callback runs separately before the IPA job; old
API/spool/export/Runtime096/099 evidence remains historical and source-preserved.
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
_spec = importlib.util.spec_from_file_location('test100_shared_source_utils', HERE/'run_test099_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '39851a45f5327ba5611c7c6bf57211f04eddf3e0'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Ring.c'})
# Authors freeze explicit new/related methods before this runner can execute.
CASES = (
    ('tests.test_native_lower_fringe100', 'NativeLowerFringe100Tests', 'test100-lower_fringe100',
     frozenset({
         'test_every_positive_wall_and_floor_witness_is_required',
         'test_existing_mouth_corner_and_shadow_masks_are_preserved',
         'test_fixed_world_chooser_uses_four_observed_floor_steps_then_holds_at_wall',
         'test_observed_lower_exterior_floor_retains_only_fixed_left_bit9',
         'test_short_current_floor_vantage_and_disconnected_exterior_are_required',
         'test_state_goods_gold_item_protection_and_fixed_coordinates_keep_scope',
     }), True),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test100-passage_navigation072',
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
    ('tests.test_native_supported_mouth084', 'NativeSupportedMouth084Tests', 'test100-supported_mouth084',
     frozenset({
         'test_gold_goods_invalid_scenes_and_ordinary_right_down_exits_stay_out',
         'test_missing_flank_needs_outside_floor_and_three_current_walls',
         'test_observed_outside_floor_with_one_unknown_flank_selects_fixed_upper_left_mouths',
         'test_old_two_wall_and_shadowed_mouth_masks_and_source_bytes_are_preserved',
         'test_only_current_safe_floor_paths_authorize_approach',
     }), True),
    ('tests.test_native_corner_vantage086', 'NativeCornerVantage086Tests', 'test100-corner_vantage086',
     frozenset({
         'test_fixed_world_mouth_approaches_only_floor_and_holds_until_a_new_observed_route',
         'test_observed_mouth_outside_two_walls_and_unknown_inboard_are_all_required',
         'test_only_four_fixed_upper_left_corners_gain_the_new_hypothesis',
         'test_scene_guards_and_all_original_ten_mouth_branches_stay_unchanged',
         'test_unknown_inboard_keeps_observed_corner_candidate_for_safe_vantage',
         'test_vantage_requires_observed_shortest_three_step_route_and_clear_crosses',
     }), True),
    ('tests.test_native_shadow_passage094', 'NativeShadowPassage094Tests', 'test100-shadow_passage094',
     frozenset({
         'test_black_gaps_other_sides_goods_gold_protection_and_invalid_scenes_fail_closed',
         'test_fixed_world_mouth_moves_only_on_observed_floor_then_holds',
         'test_four_dark_cells_and_observed_short_floor_vantage_are_required',
         'test_marked_shadow_shape_keeps_unknown_and_adds_only_fixed_upper_left_mouth',
         'test_original_ten_mouths_supported_mouths_and_corner_masks_remain_unchanged',
         'test_tall_brown_column_and_opposite_roof_wall_are_required',
     }), True),
    ('tests.test_native_split_shadow095', 'NativeSplitShadow095Tests', 'test100-split_shadow095',
     frozenset({
         'test_all_six_dark_cells_remain_unknown_and_are_required',
         'test_both_roof_sides_and_lower_left_wall_need_observed_support',
         'test_fixed_world_mouth_uses_three_actual_floor_steps_then_holds',
         'test_marked_split_roof_adds_only_fixed_upper_left_hypothesis',
         'test_observed_approach_floor_shortest_path_and_all_protections_are_required',
         'test_old_candidates_and_invalid_gold_goods_other_corners_are_preserved',
     }), True),
    ('tests.test_native_occluded_corner097', 'NativeOccludedCorner097Tests', 'test100-occluded_corner097',
     frozenset({
         'test_elbow_requires_each_observed_turn_wall_floor_and_unknown_direct_outside',
         'test_fixed_world_chooser_advances_only_existing_floor_and_holds_before_unknown',
         'test_left_elbow_uses_diagonal_outside_floor_without_inventing_direct_outside_floor',
         'test_old_mouths_shadows_corners_and_unrelated_sides_keep_original_masks',
         'test_scene_central_floor_goods_gold_all_protection_and_abi_guards_are_preserved',
         'test_upper_dark_portal_and_inside_materials_do_not_authorize_walls_doors_or_hidden_floor',
         'test_upper_requires_independent_outer_roof_and_left_boundary_positive_walls',
         'test_upper_shadow_retains_floor_or_unknown_inside_and_mixed_opaque_wall_support',
     }), True),
    ('tests.test_native_solid_corner098', 'NativeSolidCorner098Tests', 'test100-solid_corner098',
     frozenset({
         'test_each_positive_corner_wall_exterior_and_hidden_front_is_required',
         'test_fixed_mouth_approach_uses_four_floor_steps_and_holds_at_solid_corner',
         'test_old_candidate_shapes_and_masks_are_unchanged',
         'test_short_existing_floor_vantage_and_all_protections_are_required',
         'test_solid_corner_exterior_floor_adds_only_fixed_left_upper_hypothesis',
         'test_state_goods_gold_item_and_noncanonical_orientations_keep_old_scope',
     }), True),
    ('tests.test_native_side_shop100', 'NativeSideShop100Tests', 'test100-side_shop100',
     frozenset({
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
    ('tests.test_native_target_only095', 'TargetOnly095Tests', 'test100-target_only095',
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
    ('tests.test_native_structural_shop096', 'NativeStructuralShop096Tests', 'test100-structural_shop096',
     frozenset({
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
    ('tests.test_client100', 'Client100Tests', 'test100-client',
     frozenset({
         'test_default_test099_labels_and_recovery_stay_unchanged',
         'test_test100_archive_index_and_nested_run_use_separate_label',
         'test_test100_entry_routes_own_spool_and_preserves_closed_test_number',
         'test_test100_interrupted_collection_recovers_same_uuid_and_label',
     }), True),
    ('tests.test_native_opened_fade100', 'NativeOpenedFade100Tests', 'test100-opened-fade',
     frozenset({
         'test_cycle_remote_bracketed_door_to_gold_keeps_fresh_frozen_entry',
         'test_legacy_profile_does_not_gain_remote_door_relabel_permission',
         'test_nearby_material_or_old_gold_item_loss_are_not_remote_permission',
         'test_other_direction_opening_does_not_authorize_this_entry',
         'test_prefix_deadline_and_cancel_do_not_create_new_entry_authority',
         'test_remote_relabel_requires_observed_gold_bracket_and_no_protection',
         'test_remote_relabel_requires_real_same_direction_opening',
     }), True),
    ('tests.test_native_partial_rebind100', 'NativePartialRebind100Tests', 'test100-partial-rebind',
     frozenset({
         'test_horizon_expiry_after_new_result_cannot_restore_old_observation_credit',
         'test_new_candidate_or_unsafe_unknown_is_held_without_movement_or_restart',
         'test_new_exposure_gets_new_identity_and_rejects_old_worker_result',
         'test_real_opening_same_prefix_strict_zero_and_original_deadline_remain_required',
         'test_reveal_requires_old_items_protection_and_remote_envelope',
         'test_safe_new_result_uses_old_horizon_and_one_rebind_per_stationary_episode',
     }), True),
    ('tests.test_native_side_shop_controller100', 'NativeSideShopController100Tests', 'test100-side-shop-controller',
     frozenset({
         'test_correct_source_does_not_authorize_wrong_policy_and_old_policy3_stays_independent',
         'test_every_required_gold_position_is_recomputed_even_with_equal_numeric_count',
         'test_offer_cells_endcaps_gate_and_rounded_row_must_belong_to_actual_source',
         'test_policy_price_baseline_extra_objects_and_complete_bounds_are_strict',
         'test_seven_observed_gold_side_shape_reaches_only_existing_durable_restart',
     }), True),
    ('tests.test_native_opened_entry093', 'NativeOpenedEntry093Tests', 'test100-related-opened-entry093',
     frozenset({
         'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
         'test_projection_surface_gold_and_motion_counterexamples_reject_revalidation',
     }), False),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test100-related-partial-entry097',
     frozenset({
         'test_nearby_or_protected_material_and_other_stone_destinations_are_not_quiet',
         'test_remote_stone_to_dirt_keeps_observation_credit',
     }), False),
    ('tests.test_native_partial_reacquire098', 'NativePartialReacquire098Tests', 'test100-related-partial-reacquire098',
     frozenset({
         'test_only_unknown_motion_waits_then_later_independent_zero_releases_once',
     }), False),
    ('tests.test_native_partial_framing097', 'NativePartialFraming097Tests', 'test100-related-partial-framing097',
     frozenset({
         'test_new_full_observation_before_framing_move_gets_new_normal_job',
     }), False),
    ('tests.test_native_structural_cycle096', 'NativeStructuralCycle096Tests', 'test100-related-structural-cycle096',
     frozenset({
         'test_opening_must_be_observed_floor_or_door_and_unseen_corner_is_not_filled',
         'test_structural_numeric_certificate_still_requires_all_bounds_faces_and_observed_goods',
     }), False),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_opened_fade100',
    'tests.test_native_partial_rebind100',
    'tests.test_native_side_shop_controller100',
    'tests.test_native_lower_fringe100',
    'tests.test_native_side_shop100',
    'tests.test_client100',
})

# Helper source closure is pending final owner inventories; helpers add no test scopes.
CORE_MODULES = (*shared.CORE_MODULES,
    'tests.test_native_stop099', 'tests.test_native_handoff099',
    'tests.test_native_cycle_binary095')
DEPENDENCY_FIXTURES = (*shared.DEPENDENCY_FIXTURES,
    'tests/test_campaign099.py', 'tests/test_native_cycle_client094.py')
PRODUCT_PATHS = ('necroprobe/trial_evidence099.py', 'necroprobe/campaign099.py',
                 'necroprobe/test099.py', 'necroprobe/test100.py', 'test_100.sh')
PRESERVED_REPOSITORY = (*(path for path in shared.PRESERVED_REPOSITORY
    if path not in PRODUCT_PATHS),
    'necroprobe/cycle_publication.py', 'necroprobe/native_cycle.py',
    'necroprobe/protocol.py', 'test_099.sh',
    'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/test_device_ci099.py',
    *shared.CURRENT_MAC_SOURCES, *shared.CURRENT_MAC099_SOURCES,
    *DEPENDENCY_FIXTURES)
# The single new partial-rebind Mac callback runs separately before the IPA job.
CURRENT_MAC_SOURCES = ()
CURRENT_PARTIAL_MAC_SOURCES = (
    'patches/loopctrl/check_runtime_partial100.py',
    'patches/loopctrl/ngg2_runtime_partial100_tests.swift',
    'patches/loopctrl/ngg2_runtime_partial100_fixture.c',
    'patches/loopctrl/ngg2_runtime_partial100_fixture.h',
    'patches/loopctrl/ngg2_runtime_fakes.swift',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.c',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.h',
)
PARTIAL_RUNTIME_BASELINE = NATIVE_BASELINE

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO100_') for name in os.environ):
        raise ValueError('TEST100 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST100 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST100 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST100 new focused scopes are missing')


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
    name = 'tests.test_native_single_gold086'
    if name in modules:
        if nav086_source is None:
            raise ValueError('current eight-file single-gold086 Nav snapshot is required')
        modules[name].CORE = nav086_source
        alias = sys.modules.get(name.rsplit('.',1)[-1])
        if alias is not None:
            alias.CORE = nav086_source
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in CASES]

def runtime_partial_boundary_identity(driver):
    boundary = importlib.import_module('check_runtime_partial100')
    if Path(boundary.__file__).resolve() != driver/'patches/loopctrl/check_runtime_partial100.py':
        raise ValueError('Runtime partial100 checker import escaped pinned driver')
    paths = tuple('patches/loopctrl/'+name for name in boundary.SOURCE_FILES)
    if not CURRENT_PARTIAL_MAC_SOURCES or paths != CURRENT_PARTIAL_MAC_SOURCES:
        raise ValueError('Runtime partial100 fixture source closure is not frozen')
    cases = list(boundary.CASES)
    baseline = git(driver, 'show', PARTIAL_RUNTIME_BASELINE+':patches/loopctrl/ngg2/NG2Controller.c')
    if (boundary.BASELINE_CODE != PARTIAL_RUNTIME_BASELINE or len(cases) != 1
            or sha(baseline) != boundary.BASELINE_CONTROLLER_SHA):
        raise ValueError('Runtime partial100 single callback/baseline identity changed')
    return dict(baseline_code=PARTIAL_RUNTIME_BASELINE, cases=cases,
        baseline_controller_sha256=sha(baseline),
        pass_line=boundary.PASS, expected_assertion_red=boundary.RED_ASSERTION,
        fixture_controls=list(boundary.FIXTURE_CONTROLS), host_aliases=list(boundary.HOST_ALIASES),
        scope='Selection metadata only; same-CODE standalone old-C semantic Red/current-C Green runs before IPA and is not repeated in the device build')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('100')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('100')]
    paths += ['patches/loopctrl/run_test099_host.py', 'patches/loopctrl/test_device_ci099.py']
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py',
                      'patches/loopctrl/test_device_ci100.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    current_partial_mac = {path:sha(pinned_bytes(driver,path,code)) for path in CURRENT_PARTIAL_MAC_SOURCES}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        current_partial_mac_source_sha256=current_partial_mac,
        partial_runtime_callback_selection=runtime_partial_boundary_identity(driver),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        historical_mac_boundary_proof=dict(code='ade7d047224b8ee789a5110b626b9df052cb2518',run=43614403456,build=183,
            source_reference=NATIVE_BASELINE,executed_this_run=False,
            limitation='Historical TEST099 metadata only. Runtime/header/API/spool/export sources remain unchanged; Controller/Nav/Ring changed and the new partial-rebind callback requires its separate same-CODE proof. No phone acceptance is claimed.'),
        direct_c_compiler_binding='Selected C fixtures use installed CORE; if selected, old086 Nav uses eight exact current sealed files. No Ring classification replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test100-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test100-nav086-current-') as temporary:
        binding=source_identity(driver,before)
        snapshot_root=Path(temporary)/'single-gold086'
        snapshot=None
        if any(row[0]=='tests.test_native_single_gold086' for row in CASES):
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
            raise ValueError('TEST100 read-only companion ABI changed')
        evidence=dict(scope='TEST100 selected observed shop-stop and evidence contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={'test100-related-single-gold086':snapshot} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'old086 historical Controller wrapper is not selected; an exact current eight-source Nav snapshot is created only when first-five Nav methods are explicitly selected',
                     'old095/096/097/098/099 complete host suites and unchanged API/spool/export/Runtime096/099 callbacks',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci100')
        run_scope('test100-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection100Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test100-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST100 selected contracts against exact sealed IPA sources; Mac checks are separate and phone acceptance is not run')


if __name__=='__main__':main()
