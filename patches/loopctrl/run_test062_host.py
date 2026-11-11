"""Run TEST079 gold reveal and unsent dirt reservation units with named related regressions.

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


REVEALED_GATE079_METHODS = frozenset({
    'test_public_four_direction_reveal_is_a_unit_then_nav_approaches_without_entry',
    'test_revealed_gate_requires_old_singleton_exact_pair_and_unknown_projections',
    'test_only_old_noncollinear_stone_anchors_count_and_other_losses_are_not_evidence',
    'test_all_nine_translations_include_different_anchor_pair_ambiguity',
    'test_scope_requires_unknown_candidate_unprotected_item_free_observed_endpoints',
    'test_raw_normal_side_unit_gap_and_known_output_boundaries',
    'test_stationary_reverse_two_cells_and_partial_pixels_never_become_a_unit',
    'test_shared_fixed_axis_strength_bands_and_all73_competitor_rules_remain_required',
})

DIRT_TICKET079_METHODS = frozenset({
    'test_verified_four_direction_dig_keeps_ticket_then_counts_only_terrain_opening',
    'test_closed_gate_unit_target_unknown_goods_and_verified_lead_are_required',
    'test_local_gold_protected_material_item_and_nonpalette_changes_are_rejected',
    'test_unknown_tween_or_nonzero_motion_cannot_preserve_dig_authority',
    'test_original_actual_deadline_and_stable_current_prefix_are_kept',
    'test_goods_cancel_owner_and_started_or_unknown_input_never_gain_another_send',
})

RELATED_NAVIGATION_METHODS = frozenset({
    'test_structural_partial_gold_and_all_geometric_aliases',
    'test_closed_gate_high_intensity_rescue_and_repeated_texture_rejection',
    'test_signed_texture_thresholds_exact75_95_and15point_lead',
})

RELATED_CLOSED_GATE_METHODS = frozenset({
    'test_public_four_direction_arrival_returns_next_door_without_entry',
    'test_support_strength_two_bands_and_sufficient_competitor_lead_boundaries',
})

RELATED_SHOP_METHODS = frozenset({
    'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker',
    'test_exception_does_not_allow_other_local_cells_materials_or_missing_open_ack',
    'test_original_actual_deadline_and_matching_stable_prefix_remain_required',
    'test_goods_cancel_and_control_guards_preempt_preserved_entry',
    'test_unknown_entry_synth_never_reuses_the_quiet_permission',
})

RELATED_TERRAIN_METHODS = frozenset({
    'test_trigger_requires_a_never_started_unit_action_and_original_commit_deadline',
    'test_independent_proof_and_issued_ticket_reject_motion_geometry_and_invalid_prefix',
})

RELATED_CONTROLLER_METHODS = frozenset({
    'test_door_and_dirt_opening_count_operation_without_step',
    'test_goods_frame_preserves_evidenced_move_before_holding_pause',
})

RELATED_PASSAGE_METHODS = frozenset({
    'test_moved_gold_reveal_uses_normal_shop_without_restart',
    'test_unknown_sent_exploration_and_restart_cannot_issue_or_reset',
})

RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})

NATIVE_CASES = (
    ('tests.test_native_revealed_gate079', 'NativeRevealedGate079Tests', 'test079-revealed-gate', REVEALED_GATE079_METHODS, True),
    ('tests.test_native_dirt_ticket079', 'NativeDirtTicket079Tests', 'test079-dirt-ticket', DIRT_TICKET079_METHODS, True),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test079-related-navigation', RELATED_NAVIGATION_METHODS, False),
    ('tests.test_native_closed_gate078', 'NativeClosedGate078Tests', 'test079-related-closed-gate', RELATED_CLOSED_GATE_METHODS, False),
    ('tests.test_native_shop071', 'NativeShop071Tests', 'test079-related-shop', RELATED_SHOP_METHODS, True),
    ('tests.test_native_terrain071', 'NativeTerrain071Tests', 'test079-related-terrain', RELATED_TERRAIN_METHODS, False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test079-related-controller', RELATED_CONTROLLER_METHODS, False),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test079-related-passage', RELATED_PASSAGE_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test079-related-recovery', RECOVERY_METHODS, False),
)

CLIENT_CASES = ()
PACKAGE_CASES = ()
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception',
                'tests.test_native_motion067', 'tests.test_native_blocked067',
                'tests.test_native_observation072', 'test_native_perception')
NATIVE_BASELINE = '5e9a9bbdb0e16157c995d04e42066006b20c8313'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Controller.c'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test079',
                         'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_',
                             'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_',
                             'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_',
                             'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_',
                             'NECRO_TEST079_BASELINE_')

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
        if name != 'necroprobe.test079' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST079 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test079')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST079 entry is not bound to the actual driver publication wrapper')
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
        raise ValueError('TEST079 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST079 native change scope differs')
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
    record = {'scope': 'TEST079 gold reveal and unsent dirt reservation units with named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'fixture_source_policy': {'baseline_override_env_prefixes': list(FIXTURE_OVERRIDE_PREFIXES),
                  'baseline_override_env_names': ['BASELINE_NAV'],
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unchanged Perception and JSON suites (same TEST078 bytes; historical results are not current TEST079 executions)',
                          'unchanged client and RPC suites', 'unchanged package/profile and client version unit suites',
                          'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test079-revealed-gate': 'only previously UNKNOWN unit arrival with newly revealed gold and a uniquely anchored closed gate may use the existing fixed-axis feature proof; known outputs and original score/support limits remain unchanged',
                  'test079-dirt-ticket': 'a verified unstarted dirt ticket below the same closed gate retains its original authority only for remote palette changes proven strictly stationary',
                  'test079-related-navigation': 'old partial geometry, high-intensity closed-gate rescue and signed texture thresholds remain unchanged',
                  'test079-related-closed-gate': 'the prior closed-gate unit proof keeps arrival separate from entry and retains independent bands and competitor limits',
                  'test079-related-shop': 'all prior opened-entry flicker, missing opening ACK, original deadline, goods, owner and unknown-input boundaries remain intact',
                  'test079-related-terrain': 'terrain recovery still requires a never-started unit action, independent proof, original deadline and matching geometry and prefix',
                  'test079-related-controller': 'opening does not credit displacement and visible goods preserve evidenced movement before pausing',
                  'test079-related-passage': 'revealed gold returns to normal shop planning while unknown sent exploration and restart input cannot issue or reset another command',
                  'test079-related-recovery': 'unchanged public ABI confirmed through actual C queries'}}
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
    print('PASS TEST079 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
