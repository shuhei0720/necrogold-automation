"""TEST107 selected partial observation composition and initial reacquisition contracts.

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
_spec = importlib.util.spec_from_file_location('test107_shared_source_utils', HERE/'run_test106_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'adda0e7222fc168c100682548f005edcfb19f28f'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c'})
# Controller-only source and exact authored method inventories are frozen.
CASES = (
    ('tests.test_native_initial_gold107', 'NativeInitialGold107Tests', 'test107-initial-gold', frozenset({
        'test_data_anchor_changes_keep_original_wait_deadline_and_do_not_skip_a_pair',
        'test_fade_anchor_retires_before_latest_independent_pair_gets_a_new_ticket',
        'test_goods_protection_cancellation_and_moved_evidence_never_recover_an_initial_ticket',
        'test_moved_before_a_reanchor_episode_cannot_be_forgotten_by_unknown_views',
        'test_nonindependent_stale_and_foreign_prefix_frames_never_supply_the_second_proof',
        'test_original_wait_and_sync_limits_are_not_renewed_by_fade_observations',
        'test_post_restart_first_fade_gold_uses_only_latest_pair_for_its_first_move',
    }), True),
    ('tests.test_native_initial_scene091', 'NativeInitialScene091Tests', 'test091-initial-scene', frozenset({
        'test_cancel_started_unknown_ack_and_goods_cannot_reacquire',
        'test_changed_gold_cannot_combine_two_different_views_into_authority',
        'test_crossing_stale_and_original_sync_limit_do_not_supply_new_proof',
        'test_new_actual_gold_also_needs_two_independent_frames',
        'test_recovery_allowance_is_two_and_initial_deadline_never_restarts',
    }), False),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test097-partial-entry', frozenset({
        'test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit',
        'test_original_prefix_continuation_horizon_and_cancel_remain_required',
        'test_partial_relation_still_requires_same_decision_and_independent_strict_zero',
        'test_shield_permission_requires_actual_same_direction_opening_and_unchanged_gold',
    }), False),
    ('tests.test_native_partial_fringe101', 'NativePartialFringe101Tests', 'test101-partial-fringe', frozenset({
        'test_adopted_partial_credit_survives_later_duplicate_top_collapse_to_future_input',
        'test_empty_unknown_framing_does_not_inherit_the_nonempty_partial_alias_relation',
        'test_non_up_unopened_or_ineligible_motion_and_original_guards_do_not_continue',
        'test_only_top_floor_dirt_unknown_or_item_with_explained_outer_margin_is_allowed',
        'test_real_lower_item_and_protection_loss_are_not_duplicate_top_aliases',
    }), False),
    ('tests.test_native_partial_rebind100', 'NativePartialRebind100Tests', 'test100-partial-rebind', frozenset({
        'test_new_exposure_gets_new_identity_and_rejects_old_worker_result',
    }), False),
    ('tests.test_native_partial_refresh104', 'NativePartialRefresh104Tests', 'test104-partial-refresh', frozenset({
        'test_new_candidate_target_or_unsafe_unknown_holds_and_pending_source_never_refreshes',
        'test_repeated_same_prefix_refresh_keeps_first_parent_and_requires_each_new_result',
    }), False),
    ('tests.test_native_partial_roles107', 'NativePartialRoles107Tests', 'test107-partial-roles', frozenset({
        'test_growth_over_supported_top_gold_composes_with_far_palette_before_new_job_and_move',
        'test_mixed_refresh_real_up_and_current_normal_producer_reach_durable_restart',
        'test_new_job_target_candidate_and_missing_independent_zero_hold',
        'test_remote_protected_non_item_top_exposure_reclassifies_once_without_old_credit',
        'test_role_support_geometry_authority_and_original_deadline_are_required',
        'test_supported_roles_translate_to_the_other_observed_top_columns',
        'test_top_alias_reduction_and_old_shielded_palette_share_one_static_proof',
    }), True),
    ('tests.test_native_partial_wall_refresh105', 'NativePartialWallRefresh105Tests', 'test105-partial-wall-refresh', frozenset({
        'test_wall_refresh_rejects_other_protected_changes_and_missing_original_authority',
    }), False),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test072-passage', frozenset({
        'test_acknowledged_unknown_visual_motion_never_becomes_another_exploration_step',
        'test_first_skip_pause_new_gold_starts_walk_once_at_real_device_uptime',
        'test_moved_gold_reveal_uses_normal_shop_without_restart',
        'test_new_gold_revokes_skip_and_started_pause_holds_candidate',
        'test_unknown_sent_exploration_and_restart_cannot_issue_or_reset',
    }), False),
    ('tests.test_native_top_projection106', 'NativeTopProjection106Tests', 'test106-top-projection', frozenset({
        'test_new_target_candidate_and_missing_independent_zero_hold_after_the_new_job',
        'test_new_top_projection_retires_reserved_credit_and_classifies_latest_before_up',
        'test_projection_does_not_restore_the_one_use_exposed_item_allowance',
        'test_projection_requires_the_unchanged_supported_lower_row_and_explained_halo',
    }), False),
    ('tests.test_native_view074', 'NativeView074Tests', 'test074-view', frozenset({
        'test_faded_candidate_closes_before_first_move_only_after_two_wall_frames',
        'test_genuine_post_ui_passage_reaches_first_move_and_moved_origin_is_not_reclassified',
        'test_initial_wait_retains_original_sync_session_and_unknown_input_limits',
        'test_new_gold_and_goods_take_priority_over_initial_negative_or_wall_wait',
        'test_uncertain_drawing_waits_for_gold_or_two_clear_observations_without_ending',
    }), False),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_initial_gold107',
    'tests.test_native_partial_roles107',
})
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_closed_offer105',
    'tests.test_native_controller',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_initial_gold107',
    'tests.test_native_initial_scene091',
    'tests.test_native_motion067',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_observed_shop_controller104',
    'tests.test_native_offer_controller105',
    'tests.test_native_offer_coverage104',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_partial_fringe101',
    'tests.test_native_partial_rebind100',
    'tests.test_native_partial_refresh104',
    'tests.test_native_partial_roles107',
    'tests.test_native_partial_wall_refresh105',
    'tests.test_native_passage072',
    'tests.test_native_perception',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_top_projection106',
    'tests.test_native_ui073',
    'tests.test_native_view074',
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
PRODUCT_PATHS = ('necroprobe/test107.py','test_107.sh')
LEGACY_FIXTURE_EXCEPTION = {'path': 'tests/test_native_partial_fringe101.py', 'klass': 'NativePartialFringe101Tests', 'method': 'test_real_lower_item_and_protection_loss_are_not_duplicate_top_aliases', 'baseline_sha256': 'b0e1d07c8e8a06e348a784375833a712e48b906236e1002a48c33480647dbbe8', 'approved_sha256': '83fb0d5dd39b9947b96ca8a8a7eec2b5105237c5e5e4cdc9ffa63358e7f60555'}
PRESERVED_REPOSITORY = (*shared.PRESERVED_REPOSITORY,*shared.PRODUCT_PATHS,*PRESERVED_LOCAL_PYTHON,
    'patches/loopctrl/run_test106_host.py','patches/loopctrl/test_device_ci106.py',
    'tools/ring_native/generate_non_target094.py',
    'necroprobe/closed_container_features105.json','tools/ring_native/generate_closed105.py',
    *(name.replace('.', '/')+'.py' for name in shared.CORE_MODULES))
RUNTIME_PROOF_POLICY = 'historical_only_unchanged_runtime'
UNCHANGED_RUNTIME_SHA256 = '42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8'
BASELINE_CONTROLLER_SHA256 = 'd24716752ba6edb6346d96ee157f45c1289d0343ca763aad366fde3a96e3869e'
HISTORICAL_CONTROLLER_SHA256 = '4101c6e4fa06d488aead1bad01b338f30afee328e99d66281c997ad643a8c63e'

NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO107_') for name in os.environ):
        raise ValueError('TEST107 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST107 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST107 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST107 new focused scopes are missing')


native_delta = shared.native_delta

def preserved_fixture_identity(path, current, original):
    """Preserve every old byte except a separately approved, source-bound method."""
    exception=LEGACY_FIXTURE_EXCEPTION
    if exception is None or path!=exception['path']:
        return retained_identity(current,original)
    if sha(original)!=exception['baseline_sha256'] or sha(current)!=exception['approved_sha256']:
        raise ValueError('TEST107 unreviewed legacy fixture revision')
    trees=[ast.parse(raw.decode()) for raw in (original,current)]
    classes=[next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==exception['klass']) for tree in trees]
    methods=[[n for n in klass.body if isinstance(n,ast.FunctionDef)] for klass in classes]
    if [n.name for n in methods[0]]!=[n.name for n in methods[1]]:
        raise ValueError('TEST107 legacy method markers changed')
    selected=[next(n for n in group if n.name==exception['method']) for group in methods]
    old,new=selected
    if old.decorator_list or new.decorator_list or ast.dump(old.args)!=ast.dump(new.args):
        raise ValueError('TEST107 legacy method interface changed')
    old_lines,new_lines=[raw.decode().splitlines(keepends=True) for raw in (original,current)]
    if old_lines[:old.lineno-1]!=new_lines[:new.lineno-1] or old_lines[old.end_lineno:]!=new_lines[new.end_lineno:]:
        raise ValueError('TEST107 bytes outside the approved legacy method changed')
    other=[[ast.dump(n,include_attributes=False) for n in group if n.name!=exception['method']] for group in methods]
    if other[0]!=other[1]:
        raise ValueError('TEST107 other legacy methods changed')
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
        raise ValueError('TEST107 historical-only Runtime scope/source identity changed')
    return dict(policy=RUNTIME_PROOF_POLICY,runtime_sha256=UNCHANGED_RUNTIME_SHA256,
        executed_this_run=False,current_controller_execution=False,
        baseline_controller_sha256=BASELINE_CONTROLLER_SHA256,
        historical_controller_sha256=HISTORICAL_CONTROLLER_SHA256,
        current_controller_sha256=current[controller],source_reference=NATIVE_BASELINE,
        historical_mac=dict(code='2c5afa96caa3944dc376ece148d274f913880500',run=43663964487,build=191,
            executed_this_run=False,controller_sha256=HISTORICAL_CONTROLLER_SHA256,
            runtime_sha256=UNCHANGED_RUNTIME_SHA256),
        limitation='Mac191 used old101 Controller4101 with Runtime42f2. Runtime bytes remain unchanged, but this is not fresh TEST107 Controller/Navigation/Runtime execution or game acceptance.')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('107')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('107')]
    paths += ['patches/loopctrl/run_test106_host.py', 'patches/loopctrl/test_device_ci106.py']
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099','necroprobe.test100','necroprobe.test101','necroprobe.test102','necroprobe.test103','necroprobe.test104','necroprobe.test105','necroprobe.test106','necroprobe.test107'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py', 'patches/loopctrl/run_test100_host.py', 'patches/loopctrl/run_test101_host.py', 'patches/loopctrl/run_test102_host.py', 'patches/loopctrl/run_test103_host.py', 'patches/loopctrl/run_test104_host.py', 'patches/loopctrl/run_test105_host.py', 'patches/loopctrl/run_test106_host.py', 'patches/loopctrl/run_test107_host.py',
                      'patches/loopctrl/test_device_ci107.py']
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
    (output/'test107-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test107-nav086-current-') as temporary:
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
            raise ValueError('TEST107 read-only companion ABI changed')
        evidence=dict(scope='TEST107 selected partial observation composition and initial reacquisition contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={label:snapshot for name,_klass,label,_methods,_exact in CASES
                if name in ('tests.test_native_single_gold086','tests.test_native_terrain_axis091')} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'Historical086/091 current eight-source snapshots are created only if an explicit related scope requires them',
                     'old095/096/097/098/099/100/101/102 complete host suites and Runtime/Mac callbacks; historical Mac191 is not current Controller proof',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci107')
        run_scope('test107-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection107Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test107-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST107 selected native contracts against exact sealed IPA sources; unchanged Runtime proof is historical and phone acceptance is not run')


if __name__=='__main__':main()
