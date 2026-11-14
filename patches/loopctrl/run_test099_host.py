"""TEST099 selected stop diagnostics and qualified finite-run campaign contracts.

Current C/client units test software contracts, not iPhone/game acceptance. Fresh Mac
API/spool/export, bounded PAUSE Runtime096 and focused Runtime099 callbacks run separately.
The old Runtime094 PAUSE-before-classifier fixture is preserved, not executed.
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
_spec = importlib.util.spec_from_file_location('test099_shared_source_utils', HERE/'run_test098_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
retained_identity, addition_identity = shared.retained_identity, shared.addition_identity
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'bd5edaa0e2b721926775d75b1004193e5c0e0a85'
RUNTIME_BASELINE = 'c071f41d4a38b4b513d342ea3f3c68f5db8ec067'
SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Controller.h', 'LoopCtrlUITests/NG2Runtime.swift'})
# This exact author inventory is frozen; only the selected methods execute.
CASES = (
    ('tests.test_native_stop099', 'NativeStop099Tests', 'test099-stop',
     frozenset({
         'test_companion_query_is_read_only_null_safe_and_keeps_old_abi',
         'test_first_generic_stop_is_frozen_before_cleanup_and_late_callbacks',
         'test_live_passage_anchor_last_failed_comparison_and_timeout_are_preserved',
         'test_observe_more_rejection_uses_distinct_stage_without_new_input',
         'test_post_credit_failure_reports_exact_comparison_and_original_anchor',
         'test_post_credit_motion_unknown_still_stops_and_reports_zero_credit',
     }), True),
    ('tests.test_native_handoff099', 'NativeHandoff099Tests', 'test099-handoff',
     frozenset({
         'test_changed_uncertain_gold_goods_candidate_or_protection_never_requalifies_clear_handoff',
         'test_clear_cutoff_requalifies_and_freezes_a_new_clear_pause_source',
         'test_clear_search_twelve_needs_actual_cleanup_pause_before_allowed',
         'test_earlier_durable_negative_history_needs_a_new_clear_level_and_explicit_search_cutoff',
         'test_only_fourth_durable_negative_limit_mints_classified_source_handoff',
         'test_read_only_handoff_companion_has_separate_abi_and_inert_missing_controller',
         'test_residual_negative_does_not_turn_generic_walk_or_session_limit_into_handoff',
         'test_target_candidate_unknown_and_unknown_pause_cannot_handoff',
     }), True),
    ('tests.test_native_partial_reacquire098', 'NativePartialReacquire098Tests', 'test099-related-partial098',
     frozenset({
         'test_actual_opened_entry_remote_floor_loss_keeps_fixed_continuation',
         'test_first_rejected_cycle_observation_logs_immutable_source_and_no_permission',
         'test_floor_loss_does_not_expand_unopened_wrong_direction_near_or_protected_authority',
         'test_material_rejection_diagnostic_uses_cycle_anchor_not_pre_door_ticket',
         'test_new_full_floor_handoff_is_not_limited_to_empty_framing_and_retires_old_job',
         'test_only_unknown_motion_waits_then_later_independent_zero_releases_once',
         'test_unknown_wait_does_not_clear_known_motion_static_changes_or_missing_open_ack',
         'test_unknown_wait_keeps_original_deadline_and_cancel_owner_lock_stop',
         'test_wrong_prefix_unstable_pre_release_and_old_id_never_supply_wait_proof',
     }), True),
    ('tests.test_native_partial_entry097', 'NativePartialEntry097Tests', 'test099-related-entry097',
     frozenset({
         'test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit',
         'test_nearby_or_protected_material_and_other_stone_destinations_are_not_quiet',
         'test_new_ticket_keeps_its_frozen_bounds_and_completed_opening_id_does_not_revive',
         'test_original_prefix_continuation_horizon_and_cancel_remain_required',
         'test_partial_relation_still_requires_same_decision_and_independent_strict_zero',
         'test_remote_stone_to_dirt_keeps_observation_credit',
         'test_shield_permission_requires_actual_same_direction_opening_and_unchanged_gold',
     }), True),
    ('tests.test_native_partial_framing097', 'NativePartialFraming097Tests', 'test099-related-framing097',
     frozenset({
         'test_empty_unknown_keeps_result_and_waits_for_independent_up_framing',
         'test_exactly_one_move_requires_new_assessment_and_cannot_reuse_old_ticket',
         'test_framing_requires_actual_up_opening_and_correct_result_domain',
         'test_hypothetical_fringe_item_bounds_and_new_hud_occlusion_are_conservative',
         'test_independent_frame_needs_original_item_protection_choice_and_zero',
         'test_new_full_observation_before_framing_move_gets_new_normal_job',
         'test_original_horizon_cancel_and_foreground_guards_never_renew_framing',
         'test_same_or_pre_release_frame_wrong_prefix_and_unstable_cannot_release_credit',
         'test_top_item_and_protection_are_positive_complete_footprint_witnesses',
     }), True),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test099-related-cycle094',
     frozenset({
         'test_negative_authority_needs_durable_checkpoint_and_new_pause_source',
         'test_restart_begin_requires_exact_durable_intent_and_fresh_pause',
         'test_storage_failure_revokes_an_already_reserved_restart_before_begin',
         'test_target_candidate_and_unknown_keep_pause_without_restart',
         'test_two_shops_continue_and_fourth_shop_holds_with_cumulative_budget',
         'test_unknown_synth_freeze_survives_late_classifier_and_writer',
     }), False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test099-related-controller',
     frozenset({
         'test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged',
         'test_twelve_changed_restarts_bound_and_no_thirteenth',
     }), False),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test099-related-passage072',
     frozenset({
         'test_final_vantage_requires_independent_clear_before_restart',
         'test_shadowed_outer_goal_waits_for_observed_floor_and_never_steps_unknown',
         'test_uncertain_floor_gold_evidence_revokes_local_completion_and_skip',
     }), False),
    ('tests.test_native_closed_mouth080', 'NativeClosedMouth080Tests', 'test099-related-closed-mouth080',
     frozenset({
         'test_independent_closed_upper_and_left_mouth_use_existing_restart_without_step_credit',
         'test_original_two_beat_and_walk_session_deadlines_are_not_extended',
         'test_unknown_changed_or_unsupported_mouth_never_becomes_a_closed_inspection',
     }), False),
    ('tests.test_campaign099', 'Campaign099Tests', 'test099-campaign',
     frozenset({
         'test_cancel_after_publication_keeps_last_zip_and_issues_no_next_start',
         'test_clean_search_after_earlier_resolved_negative_uses_current_handoff',
         'test_clean_search_limit_default_unknown_is_distinct_from_unknown_assessment',
         'test_collection_interruption_recovers_same_uuid_without_new_start',
         'test_completed_run_before_index_crash_is_reconciled_before_next_start',
         'test_controller_fault_or_unadopted_negative_does_not_restart_campaign',
         'test_handoff_denies_pause_command_source_from_other_generation',
         'test_handoff_denies_referenced_frame_without_manifest_image',
         'test_handoff_requires_matching_registered_stable_source_and_pause_prefix',
         'test_indexed_published_run_clears_pending_markers_after_recovery',
         'test_missing_malformed_or_denied_handoff_does_not_repeat_limit',
         'test_negative_handoff_publishes_before_new_uuid_and_stops_at_target',
         'test_next_intent_crash_never_skips_or_restarts_the_previous_uuid',
         'test_prepared_next_journal_cannot_skip_revalidation_of_prior_proof',
         'test_publication_ack_failure_returns_incomplete_fault_bundle_and_same_id_recovery',
         'test_recovery_only_restores_last_bundle_without_start_or_new_campaign',
         'test_single_mode_returns_a_checked_index_and_last_full_run_zip',
         'test_target_candidate_and_real_unknown_never_start_another_run',
         'test_trial_client_reads_feature_every_preflight_and_rejects_old_or_malformed',
         'test_trial_run_limit_stops_before_an_additional_native_start',
         'test_uncertain_start_response_is_only_recovered_under_original_uuid',
         'test_unsupported_trial_feature_stops_before_any_native_start',
     }), True),
    ('tests.test_native_cycle_client094', 'CycleClient094Tests', 'test099-related-client094',
     frozenset({
         'test_durable_per_run_journal_survives_interruption_before_active_mirror',
         'test_method_admission_rejects_oldprofile_unknownfields_and_arbitrary_input',
         'test_published_ack_occurs_only_after_full_crc_sha_zip_and_destination_copy',
         'test_uncertain_start_is_sent_once_and_next_invocation_only_recovers_same_id',
     }), False),
)
REQUIRED_NEW_SCOPES = frozenset({
    'tests.test_native_stop099',
    'tests.test_native_handoff099',
    'tests.test_campaign099',
})

CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_controller',
    'tests.test_native_first_gold083',
    'tests.test_native_motion067',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_passage_motion082',
    'tests.test_native_perception',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_cycle094',
    'tests.test_native_partial_entry097',
    'tests.test_native_side_gate081',
    'tests.test_target_assessment087',
)
DEPENDENCY_FIXTURES = (
    'tests/test_native_paged_results.py',
    'tests/test_native_results.py',
    'tests/test_native_passage072.py',
    'tests/test_native_passage_unsent076.py',
    'tests/test_native_recovery_results.py',
    'tests/test_native_walk.py',
    'tests/test_protocol.py',
    'tests/timer_support.py',
)
PRESERVED_REPOSITORY = (*(path for path in shared.PRESERVED_REPOSITORY
    if path != 'necroprobe/native_walk.py'),
    'necroprobe/native_walk.py', 'necroprobe/test098.py', 'test_098.sh',
    'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/test_device_ci098.py',
    *DEPENDENCY_FIXTURES)
PRODUCT_PATHS = ('necroprobe/trial_evidence099.py', 'necroprobe/campaign099.py', 'necroprobe/test099.py', 'test_099.sh')
CURRENT_MAC_SOURCES = shared.CURRENT_MAC_SOURCES
TRIAL_RUNTIME_BASELINE = NATIVE_BASELINE
CURRENT_MAC099_SOURCES = (
    'patches/loopctrl/check_runtime099.py',
    'patches/loopctrl/ngg2_runtime099_fixture.c',
    'patches/loopctrl/ngg2_runtime099_fixture.h',
    'patches/loopctrl/ngg2_runtime099_tests.swift',
    'patches/loopctrl/check_runtime_cycle094.py',
    'patches/loopctrl/check_runtime_target_only095.py',
    'patches/loopctrl/ngg2_cycle_runtime_tests.swift',
    'patches/loopctrl/ngg2_target_only_runtime_tests.swift',
    'patches/loopctrl/ngg2_runtime_tests.swift',
    'patches/loopctrl/ngg2_dispatch_preparation_tests.swift',
    'patches/loopctrl/ngg2_runtime_fakes.swift',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.c',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.h',
    'patches/loopctrl/ngg2_cycle_runtime_fixture.c',
    'patches/loopctrl/ngg2_cycle_runtime_fixture.h',
)
NAV086_FILES = shared.NAV086_FILES
nav086_snapshot = shared.nav086_snapshot


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO099_') for name in os.environ):
        raise ValueError('TEST099 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES or not REQUIRED_NEW_SCOPES:
        raise ValueError('TEST099 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST099 scope is empty or duplicated')
    required = REQUIRED_NEW_SCOPES
    if not required <= {row[0] for row in CASES if row[4]}:
        raise ValueError('TEST099 new focused scopes are missing')


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

def runtime_boundary_identity(driver):
    boundary = importlib.import_module('check_runtime_pause096')
    if Path(boundary.__file__).resolve() != driver/CURRENT_MAC_SOURCES[0]:
        raise ValueError('Runtime checker import escaped pinned driver')
    baseline = git(driver, 'show', RUNTIME_BASELINE+':patches/loopctrl/ngg2/NG2Runtime.swift')
    if boundary.BASELINE_CODE != RUNTIME_BASELINE or sha(baseline) != boundary.BASELINE_RUNTIME_SHA:
        raise ValueError('Runtime096 baseline identity changed')
    new, related = list(boundary.CASES), list(boundary.RELATED_CASES)
    if len(new) != 4 or len(related) != 8 or len(set(new+related)) != 12:
        raise ValueError('Runtime096 callback inventory changed')
    return dict(baseline_code=RUNTIME_BASELINE, baseline_runtime_sha256=sha(baseline),
        new_cases=new, related_cases=related, pass_line=boundary.PASS,
        expected_assertion_red=boundary.RED_ASSERTION,
        scope='Selection metadata only; actual baseline assertion Red and current Runtime Green execute on Mac')



def runtime099_boundary_identity(driver):
    boundary = importlib.import_module('check_runtime099')
    if Path(boundary.__file__).resolve() != driver/'patches/loopctrl/check_runtime099.py':
        raise ValueError('Runtime099 checker import escaped pinned driver')
    paths = tuple('patches/loopctrl/'+name for name in boundary.SOURCE_FILES)
    if paths != CURRENT_MAC099_SOURCES:
        raise ValueError('Runtime099 fixture source closure changed')
    baseline = git(driver, 'show', TRIAL_RUNTIME_BASELINE+':patches/loopctrl/ngg2/NG2Runtime.swift')
    if boundary.BASELINE_CODE != TRIAL_RUNTIME_BASELINE or sha(baseline) != boundary.BASELINE_RUNTIME_SHA:
        raise ValueError('Runtime099 separate baseline identity changed')
    new, related = list(boundary.CASES), list(boundary.RELATED_CASES)
    if len(new) != 6 or len(related) != 1 or len(set(new+related)) != 7:
        raise ValueError('Runtime099 callback inventory changed')
    return dict(baseline_code=TRIAL_RUNTIME_BASELINE,baseline_runtime_sha256=sha(baseline),
        new_cases=new,related_cases=related,pass_line=boundary.PASS,
        expected_assertion_red=boundary.RED_ASSERTION,
        projection_fixture_sha256=sha(boundary.fixture_source('projection').encode()),
        green_fixture_sha256=sha(boundary.fixture_source().encode()),
        host_getter_alias=boundary.HOST_GETTER_ALIAS,fixture_controls=list(boundary.FIXTURE_CONTROLS),
        scope='Selection metadata only; stage1 old Runtime named assertion Red is a separate run, current Green executes on final device Mac lane')

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
    paths += [name.replace('.', '/')+'.py' for name in CORE_MODULES if not name.endswith('099')]
    paths += [name.replace('.', '/')+'.py' for name,_,_,_,_ in CASES if not name.endswith('099')]
    paths += ['patches/loopctrl/run_test098_host.py', 'patches/loopctrl/test_device_ci098.py']
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
    for module_name in ('necroprobe.native_walk','necroprobe.native_cycle','necroprobe.cycle_publication','necroprobe.test094','necroprobe.test095','necroprobe.test096','necroprobe.test097','necroprobe.test098','necroprobe.trial_evidence099','necroprobe.campaign099','necroprobe.test099'):
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
                      'patches/loopctrl/run_test094_host.py', 'patches/loopctrl/run_test095_host.py', 'patches/loopctrl/run_test096_host.py', 'patches/loopctrl/run_test097_host.py', 'patches/loopctrl/run_test098_host.py', 'patches/loopctrl/run_test099_host.py',
                      'patches/loopctrl/test_device_ci099.py']
    fixtures = {path:sha(pinned_bytes(driver,path,code)) for path in fixture_paths}
    current_mac = {path:sha(pinned_bytes(driver,path,code)) for path in CURRENT_MAC_SOURCES}
    current_trial_mac = {path:sha(pinned_bytes(driver,path,code)) for path in CURRENT_MAC099_SOURCES}
    return dict(driver_commit=code,native_baseline=NATIVE_BASELINE,fixture_source_sha256=fixtures,
        current_mac_source_sha256=current_mac,
        runtime_callback_selection=runtime_boundary_identity(driver),
        current_trial_mac_source_sha256=current_trial_mac,
        trial_runtime_callback_selection=runtime099_boundary_identity(driver),
        changed_native_sources=sorted(changed),preserved_native_source_sha256={n:current[n] for n in current if n not in changed},
        retained_source_sha256=preserved,repository_native_source_sha256=repository,
        product_sha256={p:sha(pinned_bytes(driver,p,code)) for p in PRODUCT_PATHS},
        historical_mac_boundary_proof=dict(code='7b7d7515cd1a394d1215f1c619c4e41bf7b9fe16',run=43537002612,build=175,
            source_reference=NATIVE_BASELINE,executed_this_run=False,
            limitation='Historical TEST098 metadata only. Controller, companion header and Runtime changed; fresh selected Mac boundaries prove only current procedural integration, not phone acceptance.'),
        direct_c_compiler_binding='Selected C fixtures use installed CORE; if selected, old086 Nav uses eight exact current sealed files. No Ring classification replay runs in this host selector')
def run_scope(name,cases,output,evidence):
    cases=selected_cases(cases);stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(cases))
    log=stream.getvalue();(output/(name+'.txt')).write_text(log);print(log,end='',flush=True)
    evidence[name]=dict(selected=[case.id() for case in cases],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures))
    (output/'test099-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('driver','upstream','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();driver,upstream,output=(getattr(args,n).resolve() for n in ('driver','upstream','output'))
    ensure_scope();output.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(driver),str(driver/'tests'),str(driver/'patches/loopctrl')]
    verifier=importlib.import_module('verify_package');before=verifier.inspect_native_sources(upstream,driver)
    with tempfile.TemporaryDirectory(prefix='test099-nav086-current-') as temporary:
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
            raise ValueError('TEST099 read-only companion ABI changed')
        evidence=dict(scope='TEST099 selected first-stop diagnostics and qualified campaign handoff contracts',source_identity=before,
            production_source_binding=binding,abi_bytes=abi,diagnostic_companion_abi_bytes=companion_abi,device_test='not_run',
            fixture_source_snapshots={'test099-related-single-gold086':snapshot} if snapshot else {},
            not_run=['canonical i386 Ring replay corpus','historical full Runtime/world/fault suites',
                     'old Runtime094 fourteen-case fixture: obsolete PAUSE-before-classifier release deadlocks under bounded pre-PAUSE adoption; preserved byte-for-byte and replaced by Runtime096 independent-release intent cancellation plus selected related callbacks',
                     'old086 historical Controller wrapper is not selected; an exact current eight-source Nav snapshot is created only when first-five Nav methods are explicitly selected',
                     'old095/096/097/098 complete host suites and separate Runtime095 four-case executable',
                     'iPhone reach rate, rare-target precision and human speed acceptance'])
        for label,cases in suites:run_scope(label,cases,output,evidence)
        selector=importlib.import_module('test_device_ci099')
        run_scope('test099-selector',unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection099Tests),output,evidence)
        if verifier.inspect_native_sources(upstream,driver) != before or source_identity(driver,before) != binding:
            raise ValueError('selected tests changed sealed source')
        reject_fixture_overrides();evidence['sealed_sources_unchanged_after_tests']=True
        evidence['manifest_sha256']=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes())
        (output/'test099-host-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS TEST099 selected contracts against exact sealed IPA sources; Mac checks are separate and phone acceptance is not run')


if __name__=='__main__':main()
