"""Run TEST076 bounded unsent stationary reobservation and passage recovery units with named related regressions.

All native fixtures compile the sealed patched upstream used by the IPA.
Historical synthetic worlds and Runtime mutation suites remain explicit lanes.
"""
import argparse
import ctypes
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import unittest


STATIONARY076_METHODS = frozenset({
    'test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit',
    'test_adjacent_blocked_frames_cannot_replace_the_original_anchor',
    'test_proof_requires_independent_current_prefix_and_increasing_capture',
    'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority',
    'test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it',
    'test_ready_or_issued_unknown_does_not_reopen_the_same_wait',
    'test_unsafe_changed_scene_and_unproven_or_expired_ticket_cannot_start_wait',
    'test_goods_priority_and_unproven_new_gold_hold_without_moving',
})

PASSAGE076_METHODS = frozenset({
    'test_late_live_passage_complete_begin_and_tick_preserve_verified_pose',
    'test_future_passage_ticket_and_stale_callbacks_never_reuse_old_authority',
    'test_repeated_passage_misses_keep_one_original_episode_and_deadline',
    'test_deadline_equality_in_time_failure_and_unproven_first_step_do_not_recover',
    'test_started_unknown_authority_and_changed_evidence_cannot_gain_passage_recovery',
    'test_passage_recovery_never_extends_proof_walk_or_session_budgets',
})

RELATED_GATE_METHODS = frozenset({
    'test_new_independent_stationary_pair_and_fresh_hud_open_then_enter',
    'test_geometry_protection_goods_and_known_motion_drift_end_refresh',
})

RELATED_TERRAIN_METHODS = frozenset({
    'test_independent_floor_proof_resumes_on_a_future_beat_without_opening_credit',
    'test_hud_proof_original_budgets_and_fifty_ms_preparation_are_not_reset',
})

RELATED_OBSERVATION_METHODS = frozenset({
    'test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket',
    'test_refresh_limit_is_once_per_verified_progress_and_eight_per_session',
})

RELATED_PASSAGE_METHODS = frozenset({
    'test_gold_reveal_retires_unsent_exploration_before_new_shop_ticket',
    'test_goods_item_and_protection_hold_at_every_exploration_stage',
    'test_unknown_sent_exploration_and_restart_cannot_issue_or_reset',
})

RELATED_UNSENT_METHODS = frozenset({
    'test_complete_zero_late_retires_known_unsent_ticket_and_restarts_from_verified_pose',
    'test_direct_begin_and_tick_late_share_definite_unsent_retirement',
    'test_started_ack_unknown_cancel_and_goods_never_use_unsent_recovery',
})

RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})

NATIVE_CASES = (
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test076-stationary-wait', STATIONARY076_METHODS, True),
    ('tests.test_native_passage_unsent076', 'NativePassageUnsent076Tests', 'test076-passage-unsent', PASSAGE076_METHODS, True),
    ('tests.test_native_gate069', 'NativeGate069Tests', 'test076-related-gate', RELATED_GATE_METHODS, False),
    ('tests.test_native_terrain071', 'NativeTerrain071Tests', 'test076-related-terrain', RELATED_TERRAIN_METHODS, False),
    ('tests.test_native_observation072', 'NativeObservation072Tests', 'test076-related-observation', RELATED_OBSERVATION_METHODS, False),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test076-related-passage', RELATED_PASSAGE_METHODS, False),
    ('tests.test_native_unsent_continuous', 'NativeUnsentContinuousTests', 'test076-related-unsent', RELATED_UNSENT_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test076-related-recovery', RECOVERY_METHODS, False),
)

CLIENT_CASES = ()
PACKAGE_CASES = ()
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception',
                'tests.test_native_device066', 'tests.test_native_blocked067',
                'test_native_perception')
NATIVE_BASELINE = '6408286ec380a29541e385836e1c209d445f1fe1'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test076',
                         'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_',
                             'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_',
                             'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_')


def reject_fixture_overrides():
    present = sorted(name for name in os.environ
                     if name.startswith(FIXTURE_OVERRIDE_PREFIXES) or name == 'BASELINE_NAV')
    if present:
        raise ValueError('sealed fixture baseline overrides are forbidden: '+', '.join(present))


def selected_cases(cases):
    cases = list(cases)
    identifiers = [case.id() for case in cases]
    if not cases or len(identifiers) != len(set(identifiers)):
        raise ValueError('missing or duplicate device cases')
    return cases


def method_cases(case_type, methods, *, exact=False):
    available = set(unittest.defaultTestLoader.getTestCaseNames(case_type))
    if not methods or not methods <= available or (exact and available != set(methods)):
        raise ValueError('device method inventory changed: ' + case_type.__name__)
    return selected_cases(case_type(method) for method in sorted(methods))


def native_suites(upstream):
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(case[0] for case in NATIVE_CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for module in modules.values():
        module.CORE = upstream / 'LoopCtrlUITests'
    # Support fixture imports under their historical bare names without
    # selecting either module's unrelated tests.
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream / 'LoopCtrlUITests'
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in NATIVE_CASES]


def client_source_identity(driver):
    native = importlib.import_module('necroprobe.native_walk')
    validation = importlib.import_module('necroprobe.validation')
    protocol = importlib.import_module('necroprobe.protocol')
    code = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=driver, text=True).strip()
    sources = {}
    for name in CLIENT_SOURCE_MODULES:
        module = importlib.import_module(name)
        relative = name.replace('.', '/')+'.py'
        path = driver / relative
        if Path(module.__file__).resolve() != path:
            raise ValueError('client module was imported outside the actual driver: '+name)
        committed = subprocess.check_output(['git', 'show', code+':'+relative], cwd=driver)
        raw = path.read_bytes()
        if raw != committed:
            raise ValueError('client module differs from the pinned driver commit: '+name)
        if name != 'necroprobe.test076' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST076 client source differs from the baseline: '+name)
        sources[name] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
    if (native.REVISION != 'native-walk-v15' or native.API_VERSION != '1.98.16-ngg2'
            or native.CAPABILITY != 'necrogold_native_v14'):
        raise ValueError('collection client revision/API/capability changed')
    if (protocol.json_object is not validation.json_object
            or protocol.Client._call.__globals__.get('json_object') is not validation.json_object
            or native.json_object is not validation.json_object
            or native.Client is not protocol.Client):
        raise ValueError('actual RPC client is not bound to the pinned JSON validator')
    return {'modules': sources, 'driver_commit': code, 'revision': native.REVISION, 'api_version': native.API_VERSION,
            'capability': native.CAPABILITY,
            'json_binding': {'protocol_json_object_is_validation_json_object': True,
                            'client_call_global_is_validation_json_object': True,
                            'native_json_object_is_validation_json_object': True,
                            'native_client_is_protocol_client': True}}


def client_suites():
    modules = {name: importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native = importlib.import_module('necroprobe.native_walk')
    publication = importlib.import_module('necroprobe.test069')
    entry = importlib.import_module('necroprobe.test076')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST076 entry is not bound to the actual driver publication wrapper')
    for name, module in modules.items():
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        for fixture in (module, alias):
            if fixture is not None and getattr(fixture, 'native', native) is not native:
                raise ValueError('collection fixture is not bound to the actual driver client: '+name)
            if fixture is not None and getattr(fixture, 'publication', publication) is not publication:
                raise ValueError('publication fixture is not bound to the actual driver wrapper: '+name)
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in CLIENT_CASES]


def package_suites():
    return [(label, method_cases(getattr(importlib.import_module(name), class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in PACKAGE_CASES]


def run_scope(name, cases, output, record):
    cases = selected_cases(cases)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue()
    (output / (name + '.txt')).write_text(log)
    print(log, end='', flush=True)
    record[name] = {'selected': [case.id() for case in cases], 'tests_run': result.testsRun,
                   'failures': len(result.failures), 'errors': len(result.errors),
                   'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures)}
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    if (result.testsRun != len(cases) or not result.wasSuccessful()
            or result.skipped or result.expectedFailures):
        raise RuntimeError(name + ': selected device tests must execute Green without skips/errors')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    driver, upstream, output = (value.resolve() for value in (args.driver, args.upstream, args.output))
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver/'tests'), str(driver/'patches/loopctrl')]
    verifier = importlib.import_module('verify_package')
    before = verifier.inspect_native_sources(upstream, driver)
    if (before['api_version'] != '1.98.16-ngg2' or before['client_capability'] != 'necrogold_native_v14'
            or len(before['native_source_sha256']) != 22):
        raise ValueError('TEST076 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST076 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST076 bounded unsent stationary reobservation and passage recovery units with named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'fixture_source_policy': {'baseline_override_env_prefixes': list(FIXTURE_OVERRIDE_PREFIXES),
                  'baseline_override_env_names': ['BASELINE_NAV'],
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unchanged Nav and JSON suites (same TEST075 bytes; historical results are not current TEST076 executions)',
                          'unchanged client and RPC suites', 'unchanged package/profile and client version unit suites',
                          'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test076-stationary-wait': 'retire an unstarted uncertain ticket, retain its fixed anchor and parent/wait deadlines, and require independent strict anchor-to-current stationary proof before a future ID',
                  'test076-passage-unsent': 'late complete0/begin/tick retire only a proven-unsent clear passage ticket while retaining pose, original episode, preparation and all authority guards',
                  'test076-related-gate': 'the original closed-door refresh still needs independent proof and rejects geometry, protection, goods and known-motion drift',
                  'test076-related-terrain': 'the original opened-terrain refresh keeps independent proof, original clocks and the fifty millisecond preparation margin',
                  'test076-related-observation': 'ordinary clear-floor refresh remains independent and shares the once-per-progress and eight-per-session limits',
                  'test076-related-passage': 'new gold retires unsent exploration and goods, protection and unknown sent input preserve priority',
                  'test076-related-unsent': 'the prior gold-candidate unsent recovery keeps all three late entrypoints and never retries started, unknown or cancelled input',
                  'test076-related-recovery': 'unchanged public ABI confirmed through actual C queries'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci', ('DeviceHostSelectionTests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test062-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST076 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
