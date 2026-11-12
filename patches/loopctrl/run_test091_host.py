"""TEST091 selected units bound to the exact sealed IPA source.

Reuse TEST090 inventory helpers, without its historical pins or exceptions.
Runtime's changed evidence pin has a separate, selected Mac fixture.
"""
import argparse
import ctypes
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest

_shared_spec = importlib.util.spec_from_file_location(
    'test091_shared090', Path(__file__).with_name('run_test090_host.py'))
shared = importlib.util.module_from_spec(_shared_spec)
_shared_spec.loader.exec_module(shared)

NATIVE_BASELINE = 'c9e087050f5d6c7c30d8385014ea0909e534c963'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c',
                           'LoopCtrlUITests/NG2Navigation.c',
                           'LoopCtrlUITests/NG2Runtime.swift'}
SCOPE_FINALIZED = True
# Author inventories are frozen; current source is checked again in the CI job.
NATIVE_CASES = (('tests.test_native_terrain_axis091',
  'NativeTerrainAxis091Tests',
  'test091-terrain-axis',
  frozenset({'test_blur_axis_ambiguity_and_single_region_cannot_supply_unit',
             'test_complete_nonhud_old_terrain_and_unique_translation_are_required',
             'test_finite_unit_scope_and_original_known_results_are_preserved',
             'test_public_unit_requires_new_independent_axis_proof'}),
  True),
 ('tests.test_native_opening091',
  'NativeOpening091Tests',
  'test091-opening',
  frozenset({'test_blur_is_independent_absolute_quality_and_does_not_override_known',
             'test_independently_blurred_static_opening_is_zero_credit',
             'test_new_proof_requires_complete_safe_opening_geometry',
             'test_raw_winner_runner_and_all_candidate_validity_are_required',
             'test_real_unit_pixels_are_never_recast_as_zero_opening'}),
  True),
 ('tests.test_native_initial_scene091',
  'NativeInitialScene091Tests',
  'test091-initial-scene',
  frozenset({'test_cancel_started_unknown_ack_and_goods_cannot_reacquire',
             'test_changed_gold_cannot_combine_two_different_views_into_authority',
             'test_crossing_stale_and_original_sync_limit_do_not_supply_new_proof',
             'test_hidden_old_mouth_is_not_a_negative_even_after_two_new_frames',
             'test_new_actual_gold_also_needs_two_independent_frames',
             'test_recovery_allowance_is_two_and_initial_deadline_never_restarts',
             'test_signature_only_uncertainty_retires_before_new_source',
             'test_unknown_gold_withdraws_and_requires_two_new_clear_frames'}),
  True),
 ('tests.test_native_hud_unit090',
  'NativeHudUnit090Tests',
  'test091-related-hud090',
  frozenset({'test_exact_new_hud_occlusion_and_independent_old_terrain_are_required',
             'test_independent_axis_all_competitors_and_blur_dependencies_remain_required',
             'test_public_unit_retains_visible_stones_when_one_moves_into_heart_hud',
             'test_raw_unit_finite_phases_and_original_numeric_thresholds_are_unchanged',
             'test_scope_safe_observed_endpoints_and_known_motion_results_are_preserved'}),
  False),
 ('tests.test_native_thin_gate090',
  'NativeThinGate090Tests',
  'test091-related-thin090',
  frozenset({'test_existing_state_goods_material_protection_and_entire_sampling_hud_guards_are_required',
             'test_observed_thin_iron_and_open_panel_are_distinct_and_opening_has_no_step_credit',
             'test_short_broad_dim_coloured_or_unbracketed_marks_are_not_closed_gates'}),
  False),
 ('tests.test_native_door072',
  'NativeDoor072Tests',
  'test091-related-door072',
  frozenset({'test_nonzero_and_existing_primary_motion_results_are_not_reclassified'}),
  False),
 ('tests.test_native_motion074',
  'NativeMotion074Tests',
  'test091-related-motion074',
  frozenset({'test_original_primary_classification_and_invalid_abi_remain_unchanged'}),
  False),
 ('tests.test_native_view074',
  'NativeView074Tests',
  'test091-related-view074',
  frozenset({'test_genuine_post_ui_passage_reaches_first_move_and_moved_origin_is_not_reclassified',
             'test_new_gold_and_goods_take_priority_over_initial_negative_or_wall_wait',
             'test_reserved_false_candidate_retires_and_switches_to_confirmed_new_mouth'}),
  False),
 ('tests.test_native_recovery',
  'NativeRecoveryTests',
  'test091-related-recovery',
  frozenset({'test_initial_replan_budget_survives_unsent_retirement_and_refit',
             'test_initial_sync_budget_equality_and_late_callbacks_do_not_restart_it',
             'test_unknown_synth_never_enters_visual_or_recovery'}),
  False),
 ('tests.test_native_passage072',
  'NativePassage072Tests',
  'test091-related-ack072',
  frozenset({'test_acknowledged_unknown_visual_motion_never_becomes_another_exploration_step'}),
  False))
CORE_MODULES = shared.CORE_MODULES
CLIENT_MODULES = shared.CLIENT_MODULES
RETAINED_PATHS = shared.RETAINED_PATHS + (
    'necroprobe/test090.py', 'test_090.sh', 'patches/loopctrl/run_test090_host.py')
selected_cases = shared.selected_cases
method_cases = shared.method_cases
git = shared.git
pinned_bytes = shared.pinned_bytes


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith('NECRO_TEST091_') for name in os.environ):
        raise ValueError('sealed TEST091 fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not NATIVE_CASES:
        raise ValueError('TEST091 author inventories are not frozen')
    labels = [row[2] for row in NATIVE_CASES]
    if len(labels) != len(set(labels)) or not any(row[4] for row in NATIVE_CASES):
        raise ValueError('TEST091 scope is empty or duplicated')


def native_suites(upstream):
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in NATIVE_CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for module in modules.values():
        module.CORE = upstream/'LoopCtrlUITests'
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream/'LoopCtrlUITests'
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in NATIVE_CASES]


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    retained = {}
    for path in RETAINED_PATHS:
        raw = pinned_bytes(driver, path, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+path):
            raise ValueError('retained TEST090 source changed: '+path)
        retained[path] = hashlib.sha256(raw).hexdigest()
    for name in CLIENT_MODULES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('client import escaped pinned driver: '+name)
    thin = {}
    for old, new in (('necroprobe/test090.py', 'necroprobe/test091.py'),
                     ('test_090.sh', 'test_091.sh')):
        raw = pinned_bytes(driver, new, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+old).replace(b'090', b'091'):
            raise ValueError('new entry differs beyond the test number: '+new)
        thin[new] = hashlib.sha256(raw).hexdigest()
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    changed = {name for name in current if current[name] != old.get(name)}
    if set(current) != set(old) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('unexpected TEST091 native change scope')
    additions = json.loads(pinned_bytes(driver, 'patches/loopctrl/ngg2-manifest.json', code))['additions']
    repository = {}
    for name, row in additions.items():
        path = 'patches/loopctrl/ngg2/'+row['source']
        digest = hashlib.sha256(pinned_bytes(driver, path, code)).hexdigest()
        if digest != current[name]:
            raise ValueError('repository addition differs from IPA source: '+name)
        repository[name] = digest
    for path in ('necroprobe/ring_native_manifest.json', 'necroprobe/bin/ring-i386'):
        if pinned_bytes(driver, path, code) != git(driver, 'show', NATIVE_BASELINE+':'+path):
            raise ValueError('unchanged ring delivery changed: '+path)
    manifest = json.loads(pinned_bytes(driver, 'necroprobe/ring_native_manifest.json', code))
    for path, digest in manifest['sources'].items():
        raw = pinned_bytes(driver, path, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+path) or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('unchanged ring source changed: '+path)
    engine = pinned_bytes(driver, 'necroprobe/bin/ring-i386', code)
    if len(manifest['sources']) != 15 or len(engine) != 56088 or len(engine) != manifest['binary_bytes'] or hashlib.sha256(engine).hexdigest() != manifest['binary_sha256']:
        raise ValueError('ring executable inventory differs from manifest')
    importlib.import_module('necroprobe.ring_native')._elf(engine)
    native = importlib.import_module('necroprobe.native_walk')
    if (native.REVISION, native.API_VERSION, native.CAPABILITY, native.PROFILE) != (
            'native-walk-v16', '1.98.16-ngg2', 'necrogold_native_v15', 'normal-1-1-evidence-v2'):
        raise ValueError('collection identity changed')
    validation = importlib.import_module('necroprobe.validation')
    protocol = importlib.import_module('necroprobe.protocol')
    if (native.Client is not protocol.Client or native.json_object is not validation.json_object
            or protocol.json_object is not validation.json_object
            or protocol.Client._call.__globals__.get('json_object') is not validation.json_object):
        raise ValueError('JSON/RPC binding changed')
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE,
        retained_source_sha256=retained, thin_entry_sha256=thin,
        changed_native_sources=sorted(changed), repository_native_source_sha256=repository,
        ring_manifest=manifest, runtime_validation='selected TEST091 Mac pin fixture; historical full suites not run')


def run_scope(name, cases, output, evidence):
    cases = selected_cases(cases)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue()
    (output/(name+'.txt')).write_text(log)
    print(log, end='', flush=True)
    evidence[name] = dict(selected=[case.id() for case in cases], tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures))
    (output/'test091-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': every selected method must execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    driver, upstream, output = (getattr(args, name).resolve() for name in ('driver', 'upstream', 'output'))
    ensure_scope()
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver/'tests'), str(driver/'patches/loopctrl')]
    verifier = importlib.import_module('verify_package')
    before = verifier.inspect_native_sources(upstream, driver)
    if (before['api_version'], before['client_capability'], len(before['native_source_sha256'])) != (
            '1.98.16-ngg2', 'necrogold_native_v15', 22):
        raise ValueError('sealed source identity changed')
    source_before = source_identity(driver, before)
    suites = native_suites(upstream)
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name)) for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456):
        raise ValueError('native ABI changed')
    evidence = dict(scope='TEST091 selected observed device stops', source_identity=before,
        production_source_binding=source_before, abi_bytes=abi, device_test='not_run',
        not_run=['historical full native/client/package/Runtime synthetic suites',
                 'private device replay corpus', 'unchanged TEST090 ring/collection semantics'])
    for name, cases in suites:
        run_scope(name, cases, output, evidence)
    selector = importlib.import_module('test_device_ci091')
    run_scope('test091-selector', unittest.defaultTestLoader.loadTestsFromTestCase(
        selector.DeviceHostSelection091Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != before or source_identity(driver, before) != source_before:
        raise ValueError('selected tests changed production source')
    reject_fixture_overrides()
    evidence['sealed_sources_unchanged_after_tests'] = True
    evidence['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test091-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST091 selected units against exact IPA sources')


if __name__ == '__main__':
    main()
