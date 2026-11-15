"""TEST101 selected continuation, first-gold motion, shop geometry and source-retention contracts.

Current selected units test software contracts, not iPhone/game acceptance. Two new
Mac callbacks run in three distinct source combinations before the IPA job. Old
API/spool/export/Runtime096/099/partial100 evidence remains historical.
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
_spec = importlib.util.spec_from_file_location('test101_shared_source_utils', HERE/'run_test100_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'b731edfa40a273b2a2045eba39dacbfe31cc0bfc'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Runtime.swift'})
# Authors freeze exact new/affected methods before this runner can execute.
CASES = (
    ('tests.test_native_first_gold101', 'NativeFirstGold101Tests', 'test101-first-gold',
     frozenset({
         'test_all_old_stones_and_unique_noncollinear_terrain_remain_required',
         'test_existing_motion_results_and_old_finite_runner_path_remain_separate',
         'test_finite_zero_unit_coverage_and_real_competitor_margins_are_independent',
         'test_first_reveal_safe_floor_unknown_source_and_no_merchandise_are_required',
         'test_private_four_direction_computed_planes_preserve_unit_and_known_output_scope',
         'test_public_left_first_reveal_uses_supported_finite_phase_proof',
         'test_raw_numeric_nonfinite_reverse_and_nonunit_boundaries_do_not_gain_credit',
         'test_world_absolute_strength_regions_and_competing_displacements_still_veto',
     }), True),
    ('tests.test_native_first_gold083', 'NativeFirstGold083Tests', 'test101-related-first-gold083',
     frozenset({
         'test_all_old_stones_noncollinear_dirt_and_unique_nine_remain_required',
         'test_first_gold_requires_clear_single_candidate_unknown_projection_and_safe_floor',
         'test_known_outputs_reverse_partial_stationary_and_two_cells_never_gain_unit_credit',
         'test_original_raw_finite_phase_and_strong_blur_limits_are_independent',
         'test_public_four_direction_first_gold_unit_keeps_opening_and_entry_uncredited',
     }), True),
    ('tests.test_native_single_gold086', 'NativeSingleGold086Tests', 'test101-related-single-gold086',
     frozenset({
         'test_axis_independence_all73_competition_and_blur_dependency_closure_are_required',
         'test_complete_old_stones_dirt_support_noncollinearity_and_unique_nine_are_required',
         'test_public_four_directions_retained_single_gold_unit_requires_independent_old15_unknown_proof',
         'test_raw_all73_phase_unit_and_both_strong_planes_keep_their_original_boundaries',
         'test_scope_gold_projection_endpoints_global_materials_and_known_results_remain_separate',
     }), False),
    ('tests.test_native_terrain_axis091', 'NativeTerrainAxis091Tests', 'test101-related-terrain-axis091',
     frozenset({
         'test_blur_axis_ambiguity_and_single_region_cannot_supply_unit',
         'test_complete_nonhud_old_terrain_and_unique_translation_are_required',
         'test_finite_unit_scope_and_original_known_results_are_preserved',
         'test_public_unit_requires_new_independent_axis_proof',
     }), True),
    ('tests.test_native_shop_geometry101', 'NativeShopGeometry101Tests', 'test101-shop-geometry',
     frozenset({
         'test_caps_items_state_and_mapping_keep_original_shadowed_view_unknown',
         'test_complete_pixels_prices_and_unique_faces_are_independent_requirements',
         'test_each_positive_wall_and_opening_is_required_despite_equal_gold_count',
         'test_full_strip_target_and_strong_word_keep_positive_priority',
         'test_numeric_certificate_and_old_policies_remain_distinct',
         'test_observed_twelve_cell_lower_opening_authorizes_only_complete_strip',
     }), True),
    ('tests.test_native_structural_shop096', 'NativeStructuralShop096Tests', 'test101-related-structural-shop096',
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
    ('tests.test_native_side_shop100', 'NativeSideShop100Tests', 'test101-related-side-shop100',
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
    ('tests.test_native_target_only095', 'TargetOnly095Tests', 'test101-related-target-only095',
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
    ('tests.test_client101', 'Client101Tests', 'test101-client',
     frozenset({
         'test_entry101_isolates_labels_and_recovers_same_uuid_without_continuing',
         'test_shell101_checks_own_module_and_rejects_conflicting_modes_before_start',
     }), True),
    ('tests.test_native_partial_fringe101', 'NativePartialFringe101Tests', 'test101-partial_fringe101',
     frozenset({
         'test_adopted_partial_credit_survives_later_duplicate_top_collapse_to_future_input',
         'test_empty_unknown_framing_does_not_inherit_the_nonempty_partial_alias_relation',
         'test_non_up_unopened_or_ineligible_motion_and_original_guards_do_not_continue',
         'test_only_top_floor_dirt_unknown_or_item_with_explained_outer_margin_is_allowed',
         'test_real_lower_item_and_protection_loss_are_not_duplicate_top_aliases',
     }), True),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test101-full_framing101',
     frozenset({
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
    ('tests.test_native_lower_shop_controller101', 'NativeLowerShopController101Tests', 'test101-lower_shop_controller101',
     frozenset({
         'test_actual217_equivalent_unknown_cap_and_other_material_or_mapping_failures_hold',
         'test_each_gold_position_is_required_even_with_equal_total_count',
         'test_numeric_witness_target_bounds_endcaps_and_extra_objects_remain_strict',
         'test_old_policy_three_and_four_geometry_remain_distinct',
         'test_twelve_position_shape_mirrors_and_observed_openings_reach_durable_restart_only',
     }), True),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test101-related-partial_entry097',
     frozenset({
         'test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit',
         'test_remote_stone_to_dirt_keeps_observation_credit',
     }), False),
    ('tests.test_native_partial_framing097', 'NativePartialFraming097Tests', 'test101-related-partial_framing097',
     frozenset({
         'test_empty_unknown_keeps_result_and_waits_for_independent_up_framing',
         'test_exactly_one_move_requires_new_assessment_and_cannot_reuse_old_ticket',
     }), False),
    ('tests.test_native_partial_rebind100', 'NativePartialRebind100Tests', 'test101-related-partial_rebind100',
     frozenset({
         'test_new_exposure_gets_new_identity_and_rejects_old_worker_result',
         'test_safe_new_result_uses_old_horizon_and_one_rebind_per_stationary_episode',
     }), False),
    ('tests.test_native_structural_cycle096', 'NativeStructuralCycle096Tests', 'test101-related-structural_cycle096',
     frozenset({
         'test_complete_structural_source_and_generic_bounds_reach_existing_durable_restart',
     }), False),
    ('tests.test_native_side_shop_controller100', 'NativeSideShopController100Tests', 'test101-related-side_shop_controller100',
     frozenset({
         'test_seven_observed_gold_side_shape_reaches_only_existing_durable_restart',
     }), False),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test101-related-cycle094',
     frozenset({
         'test_inflight_goods_credit_real_move_once_and_keep_unknown_motion_held',
     }), False),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_partial_fringe101',
    'tests.test_native_full_framing101',
    'tests.test_native_lower_shop_controller101',
    'tests.test_native_first_gold101',
    'tests.test_native_shop_geometry101',
    'tests.test_client101',
})
CORE_MODULES = (*shared.CORE_MODULES,
    'tests.test_native_opened_entry093', 'tests.test_native_opened_fade100')
DEPENDENCY_FIXTURES = shared.DEPENDENCY_FIXTURES
PRODUCT_PATHS = ('necroprobe/test101.py', 'test_101.sh')
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY, *shared.PRODUCT_PATHS,
    'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/test_device_ci100.py',
    *shared.CURRENT_PARTIAL_MAC_SOURCES)
CURRENT_MAC_SOURCES = ()
CURRENT_RUNTIME101_MAC_SOURCES = (
    'patches/loopctrl/check_runtime_observation101.py',
    'patches/loopctrl/ngg2_runtime_observation101_tests.swift',
    'patches/loopctrl/ngg2_runtime_retention101_tests.swift',
    'patches/loopctrl/ngg2_runtime_framing101_fixture.c',
    'patches/loopctrl/ngg2_runtime_framing101_fixture.h',
    'patches/loopctrl/ngg2_runtime_fakes.swift',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.c',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.h',
)
RUNTIME101_BASELINE = NATIVE_BASELINE

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO101_') for name in os.environ):
        raise ValueError('TEST101 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST101 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST101 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST101 new focused scopes are missing')


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

def runtime101_boundary_identity(driver):
    boundary=importlib.import_module('check_runtime_observation101')
    if Path(boundary.__file__).resolve()!=driver/'patches/loopctrl/check_runtime_observation101.py':
        raise ValueError('Runtime101 checker import escaped pinned driver')
    paths=tuple('patches/loopctrl/'+name for name in boundary.SOURCE_FILES)
    if paths!=CURRENT_RUNTIME101_MAC_SOURCES or boundary.BASELINE_CODE!=RUNTIME101_BASELINE or len(boundary.CASES)!=2:
        raise ValueError('Runtime101 source/case/baseline inventory changed')
    baseline_c=git(driver,'show',RUNTIME101_BASELINE+':patches/loopctrl/ngg2/NG2Controller.c')
    baseline_runtime=git(driver,'show',RUNTIME101_BASELINE+':patches/loopctrl/ngg2/NG2Runtime.swift')
    if (sha(baseline_c)!=boundary.BASELINE_CONTROLLER_SHA or sha(baseline_runtime)!=boundary.BASELINE_RUNTIME_SHA):
        raise ValueError('Runtime101 distinct baseline source identity changed')
    expected={'retention-baseline-red':('baseline','current',['retention']),
              'framing-baseline-red':('current','baseline',['framing']),
              'observation-production-green':('current','current',['retention','framing'])}
    if set(boundary.PROOF_SPECS)!=set(expected):raise ValueError('Runtime101 three execution inventory changed')
    for name,(runtime,controller,cases) in expected.items():
        row=boundary.PROOF_SPECS[name]
        if set(row)!={'runtime','controller','cases','expected_assertion'} or (row['runtime'],row['controller'],row['cases'])!=(runtime,controller,cases):
            raise ValueError('Runtime101 source combination changed: '+name)
        if row['expected_assertion']!=boundary.RED_ASSERTIONS.get(name):
            raise ValueError('Runtime101 named assertion identity changed: '+name)
    return dict(baseline_code=RUNTIME101_BASELINE,baseline_controller_sha256=sha(baseline_c),
        baseline_runtime_sha256=sha(baseline_runtime),cases=list(boundary.CASES),
        proof_specs=boundary.PROOF_SPECS,pass_line=boundary.PASS,expected_assertion_red=boundary.RED_ASSERTIONS,
        fixture_controls=list(boundary.FIXTURE_CONTROLS),host_aliases=list(boundary.HOST_ALIASES),
        scope='Selection metadata only; same-CODE standalone oldRuntime/currentC retention Red, currentRuntime/old100C framing Red, then both-current two-case Green precede IPA and are not repeated in the device build')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('101')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('101')]
    paths += ['patches/loopctrl/run_test100_host.py', 'patches/loopctrl/test_device_ci100.py']
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py',
                      'patches/loopctrl/test_device_ci101.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    current_runtime101_mac = {path:sha(pinned_bytes(driver,path,code)) for path in CURRENT_RUNTIME101_MAC_SOURCES}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        current_runtime101_mac_source_sha256=current_runtime101_mac,
        runtime101_callback_selection=runtime101_boundary_identity(driver),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        historical_mac_boundary_proof=dict(code='4ba361d3ca3ec12d4e068294c245546a4b4c1c6d',run=43623716812,build=187,
            source_reference=NATIVE_BASELINE,executed_this_run=False,
            limitation='Historical TEST100 metadata only. Controller/Nav/Ring/Runtime changed; the old partial100 callback and API/spool/export history are not current TEST101 proof. The two new callbacks require their separate same-CODE three-execution evidence. No phone acceptance is claimed.'),
        direct_c_compiler_binding='Selected C fixtures use installed CORE; if selected, old086 Nav uses eight exact current sealed files. No Ring classification replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test101-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test101-nav086-current-') as temporary:
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
            raise ValueError('TEST101 read-only companion ABI changed')
        evidence=dict(scope='TEST101 selected observation continuation and source-retention contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'old086 historical Controller method is not selected; the selected first-five Nav086 and TerrainAxis091 methods compile exact-current eight-source Nav snapshots',
                     'old095/096/097/098/099/100 complete host suites and API/spool/export/Runtime096/099/partial100 callbacks',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci101')
        run_scope('test101-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection101Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test101-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST101 selected contracts against exact sealed IPA sources; Mac checks are separate and phone acceptance is not run')


if __name__=='__main__':main()
