"""TEST102 selected Controller admission and Ring structural-coverage contracts.

Current selected C/Ring units test software contracts, not iPhone/game acceptance.
Runtime42f2 is byte-preserved; Mac191 used old Controller4101 and remains historical.
No fresh Runtime/current-Controller callback proof is claimed.
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
_spec = importlib.util.spec_from_file_location('test102_shared_source_utils', HERE/'run_test101_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'cb65755b0d4a01ef90cb139b7a53af354f1bad13'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c','LoopCtrlUITests/NG2Ring.c'})
# Exact new and directly related author inventories are pending; no counts inferred.
CASES = (
    ('tests.test_native_entry_corridor102', 'NativeEntryCorridor102Tests', 'test102-entry-corridor', frozenset({
        'test_observed_row4_corridor_gets_one_future_input_then_new_candidate_job',
        'test_old097_row4_without_positive_gold_rail_still_holds',
        'test_missing_dirt_or_stone_rail_never_grants_a_framing_step',
        'test_origin_destination_and_axis_floor_are_not_inferred',
        'test_item_projection_must_explain_all_protection_without_loss',
        'test_source_roi_cannot_lose_potential_goods_to_viewport_or_hud',
        'test_actual_up_opening_and_completed_unknown_domain_remain_required',
        'test_original_horizon_prefix_static_zero_and_cancel_are_never_refreshed',
    }), True),
    ('tests.test_native_full_footprint102', 'NativeFullFootprint102Tests', 'test102-full-footprint', frozenset({
        'test_neighbor_only_goods_protection_allows_one_fresh_move_then_new_candidate_job',
        'test_exact_dilation_cannot_be_bypassed_by_removing_all_old_buffer_conflicts',
        'test_new_footprint_keeps_original_static_roi_horizon_candidate_and_unknown_guards',
        'test_new_footprint_does_not_release_partial_or_second_unknown_after_its_only_move',
    }), True),
    ('tests.test_native_shop_controller102', 'NativeShopController102Tests', 'test102-shop-controller', frozenset({
        'test_positive_observed_door_enclosure_and_single_top_loss_face_have_independent_authority',
        'test_every_positive_wall_and_door_position_is_checked_despite_equal_total_count',
        'test_full_anchor_bottoms_widths_and_complete_numeric_target_proof_remain_strict',
        'test_normal_classifier_negative_runs_through_durable_intent_real_restart_ack_and_next_floor',
        'test_normal_classifier_target_and_incomplete_result_hold_without_restart',
    }), True),
    ('tests.test_native_entry_episode102', 'NativeEntryEpisode102Tests', 'test102-entry-episode', frozenset({
        'test_partial_unknown_after_first_move_needs_new_assessment_static_and_second_move',
        'test_full_unknown_after_first_move_requalifies_up_from_its_exact_latest_job',
        'test_full_rebind_before_first_input_withdraws_unsent_ticket_without_resetting_parent',
        'test_second_unknown_and_goods_unknown_hold_without_generic_credit_or_third_input',
        'test_ack_unknown_visual_wait_and_unknown_synth_do_not_create_second_step',
        'test_parent_horizon_input_budget_cancel_level_and_prefix_cannot_be_refreshed',
        'test_parent_and_current_roi_masks_floor_or_static_changes_reject_authority',
        'test_old_top_and_horizontal_one_shots_cannot_acquire_entry_episode',
        'test_pending_full_preserves_hold_assess_and_old_candidate_target_before_fifo_rebind',
        'test_pending_full_requires_safe_old_unknown_before_latest_full_second_step',
        'test_pending_worker_keeps_its_original_budget_after_observation_parent_expires',
        'test_second_observation_normal_complete_negative_preserves_durable_restart_protocol',
    }), True),
    ('tests.test_native_partial_framing097', 'NativePartialFraming097Tests', 'test097-partial-framing', frozenset({
        'test_top_item_and_protection_are_positive_complete_footprint_witnesses',
        'test_empty_unknown_keeps_result_and_waits_for_independent_up_framing',
        'test_new_full_observation_before_framing_move_gets_new_normal_job',
    }), False),
    ('tests.test_native_full_framing101', 'NativeFullFraming101Tests', 'test101-full-framing', frozenset({
        'test_full_unknown_later_static_fresh_ticket_actual_moved_then_new_candidate',
        'test_original_horizon_prefix_cancel_and_input_unknown_never_remint_a_move',
        'test_real_opening_axis_known_floor_protection_and_safe_potential_roi_are_required',
    }), False),
    ('tests.test_native_partial_fringe101', 'NativePartialFringe101Tests', 'test101-partial-fringe', frozenset({
        'test_adopted_partial_credit_survives_later_duplicate_top_collapse_to_future_input',
    }), False),
    ('tests.test_native_structural_cycle096', 'NativeStructuralCycle096Tests', 'test096-structural-cycle', frozenset({
        'test_complete_structural_source_and_generic_bounds_reach_existing_durable_restart',
    }), False),
    ('tests.test_native_side_shop_controller100', 'NativeSideShopController100Tests', 'test100-side-shop-controller', frozenset({
        'test_seven_observed_gold_side_shape_reaches_only_existing_durable_restart',
    }), False),
    ('tests.test_native_lower_shop_controller101', 'NativeLowerShopController101Tests', 'test101-lower-shop-controller', frozenset({
        'test_twelve_position_shape_mirrors_and_observed_openings_reach_durable_restart_only',
    }), False),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test094-cycle', frozenset({
        'test_restart_begin_requires_exact_durable_intent_and_fresh_pause',
        'test_ack_and_real_changed_floor_wait_for_linked_outcome_durability',
    }), False),
    ('tests.test_native_shop_coverage102', 'NativeShopCoverage102Tests', 'test102-shop-coverage', frozenset({
        'test_bottom_door_and_top_prefix_have_independent_complete_proof',
        'test_each_twelve_fixed_gold_and_door_is_required_despite_remote_count',
        'test_mirrors_interior_doors_and_observed_side_openings',
        'test_prefix_faces_preserve_anchor_width_bottom_and_unique_components',
        'test_bottom_alignment_selects_one_canonical_row_without_deleting_evidence',
        'test_scene_items_caps_states_and_half_cell_mapping_are_required',
        'test_complete_prices_caps_and_extra_boards_are_independent',
        'test_two_independently_complete_rows_are_not_unique_coverage',
        'test_target_icon_and_strong_word_keep_positive_priority',
        'test_certificate6_rechecks_every_existing_numeric_and_binary_guard',
        'test_existing_size_count_thresholds_are_not_lowered',
        'test_cancel_deadline_and_legacy_modes_keep_original_authority',
    }), True),
    ('tests.test_native_structural_shop096', 'NativeStructuralShop096Tests', 'test096-structural-shop', frozenset({
        'test_complete_structure_authorizes_without_shop_or_merchant_pixel_identity',
        'test_mirrored_openings_and_projected_protection_are_preserved',
        'test_each_required_gold_cell_and_opening_must_be_observed',
        'test_items_caps_scene_state_and_positive_gold_are_independent_requirements',
        'test_half_cell_ties_are_rejected_on_both_signed_axes',
        'test_complete_board_roi_and_scene_support_must_fit_observed_bounds',
        'test_partial_body_missing_price_extra_board_and_absent_item_are_held',
        'test_target_between_prices_and_observed_name_veto_are_never_masked',
        'test_unmatched_items_is_preserved_diagnostic_only_under_policy3',
        'test_certificate3_retains_all_numeric_identity_and_coverage_guards',
        'test_legacy_modes_and_policy2_fallback_keep_their_existing_authority',
        'test_wider_extra_observed_sign_is_not_discarded_by_selected_face_roi',
    }), False),
    ('tests.test_native_side_shop100', 'NativeSideShop100Tests', 'test100-side-shop', frozenset({
        'test_seven_observed_side_supports_authorize_complete_target_only_strip',
        'test_mirror_opening_material_and_source_protection_are_preserved',
        'test_each_side_support_and_observed_opening_is_required_despite_same_gold_count',
        'test_item_cap_scene_ties_and_clipped_support_are_held',
        'test_isolated_item_edge_is_not_a_price_but_fourth_supported_group_anywhere_is_held',
        'test_missing_shifted_price_extra_board_item_or_endcap_are_held',
        'test_target_icon_candidate_and_strong_name_keep_positive_priority',
        'test_full_sweep_holds_each_target_template_between_nominal_price_centres',
        'test_policy4_numeric_certificate_rejects_forgery_and_old_policy3_stays_distinct',
    }), False),
    ('tests.test_native_shop_geometry101', 'NativeShopGeometry101Tests', 'test101-shop-geometry', frozenset({
        'test_observed_twelve_cell_lower_opening_authorizes_only_complete_strip',
        'test_each_positive_wall_and_opening_is_required_despite_equal_gold_count',
        'test_caps_items_state_and_mapping_keep_original_shadowed_view_unknown',
        'test_complete_pixels_prices_and_unique_faces_are_independent_requirements',
        'test_full_strip_target_and_strong_word_keep_positive_priority',
        'test_numeric_certificate_and_old_policies_remain_distinct',
    }), False),
)
REQUIRED_NEW_SCOPES = frozenset({'tests.test_native_entry_corridor102', 'tests.test_native_entry_episode102', 'tests.test_native_full_footprint102', 'tests.test_native_shop_controller102', 'tests.test_native_shop_coverage102'})
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_controller',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_footprint102',
    'tests.test_native_full_framing101',
    'tests.test_native_handoff099',
    'tests.test_native_lower_shop_controller101',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_partial_fringe101',
    'tests.test_native_passage072',
    'tests.test_native_perception',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_shop_controller102',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_side_shop_controller100',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_target_assessment087',
)
DEPENDENCY_FIXTURES = ()
PRODUCT_PATHS = ('necroprobe/test102.py','test_102.sh')
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,*shared.PRODUCT_PATHS,
    'patches/loopctrl/run_test101_host.py','patches/loopctrl/test_device_ci101.py',
    *shared.CURRENT_RUNTIME101_MAC_SOURCES)
RUNTIME_PROOF_POLICY = 'historical_only_unchanged_runtime'
UNCHANGED_RUNTIME_SHA256 = '42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8'
HISTORICAL_CONTROLLER_SHA256 = '4101c6e4fa06d488aead1bad01b338f30afee328e99d66281c997ad643a8c63e'

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO102_') for name in os.environ):
        raise ValueError('TEST102 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST102 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST102 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST102 new focused scopes are missing')


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
            or before.get(controller)!=HISTORICAL_CONTROLLER_SHA256
            or not isinstance(current_controller,str) or len(current_controller)!=64
            or any(char not in '0123456789abcdef' for char in current_controller)
            or current_controller==HISTORICAL_CONTROLLER_SHA256):
        raise ValueError('TEST102 historical-only Runtime scope/source identity changed')
    return dict(policy=RUNTIME_PROOF_POLICY,runtime_sha256=UNCHANGED_RUNTIME_SHA256,
        executed_this_run=False,current_controller_execution=False,
        historical_controller_sha256=HISTORICAL_CONTROLLER_SHA256,
        current_controller_sha256=current[controller],source_reference=NATIVE_BASELINE,
        historical_mac=dict(code='2c5afa96caa3944dc376ece148d274f913880500',run=43663964487,build=191,
            executed_this_run=False,controller_sha256=HISTORICAL_CONTROLLER_SHA256,
            runtime_sha256=UNCHANGED_RUNTIME_SHA256),
        limitation='Mac191 used old101 Controller4101 with Runtime42f2. Runtime bytes remain unchanged, but this is not fresh TEST102 Controller/Runtime execution or game acceptance.')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('102')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('102')]
    paths += ['patches/loopctrl/run_test101_host.py', 'patches/loopctrl/test_device_ci101.py']
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101','necroprobe.test102'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py', 'patches/loopctrl/run_test102_host.py',
                      'patches/loopctrl/test_device_ci102.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        runtime_proof_policy=runtime_history_identity(old,current),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        direct_c_compiler_binding='Selected C fixtures use installed CORE; if selected, old086 Nav uses eight exact current sealed files. No Ring classification replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test102-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test102-nav086-current-') as temporary:
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
            raise ValueError('TEST102 read-only companion ABI changed')
        evidence=dict(scope='TEST102 selected Controller admission and Ring coverage contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'Nav is unchanged; historical086/091 snapshots are created only if an explicit related scope requires them',
                     'old095/096/097/098/099/100/101 complete host suites and Runtime/Mac callbacks; historical Mac191 is not current Controller proof',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci102')
        run_scope('test102-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection102Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test102-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST102 selected C/Ring contracts against exact sealed IPA sources; unchanged Runtime proof is historical and phone acceptance is not run')


if __name__=='__main__':main()
