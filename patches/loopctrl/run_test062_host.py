"""Run TEST077 passage palette and opened shop visibility units with named related regressions.

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


PALETTE077_METHODS = frozenset({
    'test_off_step_local_palette_retires_ticket_and_later_strict_proof_moves',
    'test_adjacent_blocked_palette_frames_cannot_replace_original_anchor',
    'test_local_change_is_still_rejected_for_shop_wait',
    'test_origin_next_protected_route_goods_and_unsafe_materials_remain_guards',
    'test_palette_wait_uses_fixed_wait_and_parent_deadlines',
    'test_palette_proof_still_requires_stable_current_prefix_and_new_capture',
})

OPEN_ENTRY077_METHODS = frozenset({
    'test_opened_entry_reveal_preserves_ticket_then_enters_on_original_beat',
    'test_interior_partial_reveals_continue_after_verified_entry_and_next_step',
    'test_geometry_old_gold_and_protected_material_changes_cannot_use_reveal',
    'test_no_open_ack_or_partial_entrance_permission_is_created_by_new_gold',
    'test_accepted_new_gold_cannot_disappear_or_shift_within_same_ticket',
    'test_original_deadline_prefix_goods_and_control_priority_remain',
})

RELATED_STATIONARY_METHODS = frozenset({
    'test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit',
    'test_adjacent_blocked_frames_cannot_replace_the_original_anchor',
    'test_proof_requires_independent_current_prefix_and_increasing_capture',
    'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority',
    'test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it',
    'test_ready_or_issued_unknown_does_not_reopen_the_same_wait',
    'test_unsafe_changed_scene_and_unproven_or_expired_ticket_cannot_start_wait',
    'test_goods_priority_and_unproven_new_gold_hold_without_moving',
})

RELATED_SHOP_METHODS = frozenset({
    'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker',
    'test_exception_does_not_allow_other_local_cells_materials_or_missing_open_ack',
    'test_original_actual_deadline_and_matching_stable_prefix_remain_required',
    'test_goods_cancel_and_control_guards_preempt_preserved_entry',
    'test_unknown_entry_synth_never_reuses_the_quiet_permission',
})

RELATED_GATE_METHODS = frozenset({
    'test_new_independent_stationary_pair_and_fresh_hud_open_then_enter',
    'test_geometry_protection_goods_and_known_motion_drift_end_refresh',
})

RELATED_CONTROLLER_METHODS = frozenset({
    'test_goods_frame_preserves_evidenced_move_before_holding_pause',
})

RELATED_PASSAGE_METHODS = frozenset({
    'test_unknown_sent_exploration_and_restart_cannot_issue_or_reset',
})

RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})

NATIVE_CASES = (
    ('tests.test_native_passage_palette077', 'NativePassagePalette077Tests', 'test077-passage-palette', PALETTE077_METHODS, True),
    ('tests.test_native_open_entry077', 'NativeOpenEntry077Tests', 'test077-open-entry', OPEN_ENTRY077_METHODS, True),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test077-related-stationary', RELATED_STATIONARY_METHODS, True),
    ('tests.test_native_shop071', 'NativeShop071Tests', 'test077-related-shop', RELATED_SHOP_METHODS, True),
    ('tests.test_native_gate069', 'NativeGate069Tests', 'test077-related-gate', RELATED_GATE_METHODS, False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test077-related-controller', RELATED_CONTROLLER_METHODS, False),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test077-related-passage', RELATED_PASSAGE_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test077-related-recovery', RECOVERY_METHODS, False),
)

CLIENT_CASES = ()
PACKAGE_CASES = ()
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception',
                'tests.test_native_device066', 'tests.test_native_blocked067',
                'tests.test_native_observation072', 'tests.test_native_passage_unsent076',
                'test_native_perception')
NATIVE_BASELINE = 'd3e9bbde44ceb41dac43beaf818043c588cc3aab'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test077',
                         'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_',
                             'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_',
                             'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_',
                             'NECRO_TEST077_BASELINE_')


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
        if name != 'necroprobe.test077' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST077 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test077')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST077 entry is not bound to the actual driver publication wrapper')
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
        raise ValueError('TEST077 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST077 native change scope differs')
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
    record = {'scope': 'TEST077 passage palette and opened shop visibility units with named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'fixture_source_policy': {'baseline_override_env_prefixes': list(FIXTURE_OVERRIDE_PREFIXES),
                  'baseline_override_env_names': ['BASELINE_NAV'],
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unchanged Nav and JSON suites (same TEST075/TEST076 bytes; historical results are not current TEST077 executions)',
                          'unchanged client and RPC suites', 'unchanged package/profile and client version unit suites',
                          'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test077-passage-palette': 'off-step local palette changes may retire unsent passage authority, but only direct strict proof against the original anchor can authorize a future ticket',
                  'test077-open-entry': 'opened-entry and verified-interior PARTIAL reveals preserve the original ticket only for distant additive GOLD while retaining accepted GOLD, route, protection, motion and clock guards',
                  'test077-related-stationary': 'all prior shop-local, fixed-anchor, prefix, parent/wait deadline and UNKNOWN no-retry boundaries remain intact',
                  'test077-related-shop': 'all prior opened-entry flicker, missing opening ACK, original deadline, goods, owner and unknown-input boundaries remain intact',
                  'test077-related-gate': 'closed-door refresh remains independent and rejects geometry, protection, goods and known-motion drift',
                  'test077-related-controller': 'visible goods preserve evidenced movement before pausing without authorizing another input',
                  'test077-related-passage': 'unknown sent exploration and restart input cannot issue or reset another command',
                  'test077-related-recovery': 'unchanged public ABI confirmed through actual C queries'}}
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
    print('PASS TEST077 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
