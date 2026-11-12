"""TEST090 units against the exact sealed IPA sources; no private/world suite.

Unchanged TEST089 client and Runtime fixtures are bound by bytes. Their earlier
execution is retained evidence, not a current pass. The ring icon-only refactor
is independently validated and its complete shipped sources are verified here.
"""
import argparse
import ctypes
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

NATIVE_BASELINE = '169eb67bc4906c83e6bedf30678b99a240b44522'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
                           'LoopCtrlUITests/NG2Perception.c'}
RETAINED_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
# A partly prepared selector must not dispatch before author inventories freeze.
SCOPE_FINALIZED = True
NATIVE_CASES = (('tests.test_native_hud_unit090',
  'NativeHudUnit090Tests',
  'test090-hud-unit',
  frozenset({'test_exact_new_hud_occlusion_and_independent_old_terrain_are_required',
             'test_independent_axis_all_competitors_and_blur_dependencies_remain_required',
             'test_public_unit_retains_visible_stones_when_one_moves_into_heart_hud',
             'test_raw_unit_finite_phases_and_original_numeric_thresholds_are_unchanged',
             'test_scope_safe_observed_endpoints_and_known_motion_results_are_preserved'}),
  True),
 ('tests.test_native_revealed_route090',
  'NativeRevealedRoute090Tests',
  'test090-revealed-route',
  frozenset({'test_new_bracket_exception_rejects_near_palette_lost_anchors_blockers_and_nonstationary_pixels',
             'test_new_bracket_reveal_cannot_bypass_existing_run_or_chain_limits',
             'test_stationary_new_bracket_reissues_same_floor_step_without_extending_frozen_ticket'}),
  True),
 ('tests.test_native_thin_gate090',
  'NativeThinGate090Tests',
  'test090-thin-gate',
  frozenset({'test_existing_state_goods_material_protection_and_entire_sampling_hud_guards_are_required',
             'test_observed_thin_iron_and_open_panel_are_distinct_and_opening_has_no_step_credit',
             'test_short_broad_dim_coloured_or_unbracketed_marks_are_not_closed_gates'}),
  True),
 ('tests.test_native_controller',
  'NativeControllerTests',
  'test090-related-fresh',
  frozenset({'test_fresh_cached_source_five_fields_are_proved_once_without_rescue',
             'test_fresh_latest_source_cannot_restore_frozen_source_phase_walk_session',
             'test_fresh_monotone_relation_all_tile_pairs_and_door_brackets'}),
  False),
 ('tests.test_native_passage_motion082',
  'NativePassageMotion082Tests',
  'test090-related-motion082',
  frozenset({'test_public_four_direction_terrain_blur_unit_keeps_next_navigation_unentered'}),
  False),
 ('tests.test_native_stationary_texture085',
  'NativeStationaryTexture085Tests',
  'test090-related-stationary085',
  frozenset({'test_old_unit_tween_reverse_and_opening_outputs_are_never_overwritten'}),
  False),
 ('tests.test_native_passage072',
  'NativePassage072Tests',
  'test090-related-unknown072',
  frozenset({'test_acknowledged_unknown_visual_motion_never_becomes_another_exploration_step'}),
  False),
 ('tests.test_native_perception',
  'NativePerceptionTests',
  'test090-related-perception',
  frozenset({'test_gold_peak_thresholds_edges_and_colour_inequalities',
             'test_synthetic_state_neutral_and_vertical_guards',
             'test_synthetic_tile_integer_thresholds'}),
  False))
CORE_MODULES = ('tests.test_native_beat',
 'tests.test_native_blocked067',
 'tests.test_native_controller',
 'tests.test_native_navigation',
 'tests.test_native_perception',
 'tests.test_native_recovery',
 'tests.test_native_motion067',
 'tests.test_native_passage_motion082',
 'tests.test_native_first_gold083',
 'tests.test_native_single_gold086',
 'tests.test_native_stationary_texture085',
 'tests.test_native_passage072')
CLIENT_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test087',
                  'necroprobe.target_assessment', 'necroprobe.ring_native', 'necroprobe.ring_early',
                  'necroprobe.protocol', 'necroprobe.validation')
RETAINED_PATHS = tuple(name.replace('.', '/')+'.py' for name in CLIENT_MODULES) + (
    'necroprobe/test089.py', 'test_089.sh', 'necroprobe/target_ring_features.json',
    'tools/build_ring_manifest.py', 'tools/evaluate_device_recording.py',
    'patches/loopctrl/ngg2_runtime_tests.swift', 'patches/loopctrl/ngg2_runtime_scene_fixtures.c',
    'patches/loopctrl/ngg2_runtime_scene_fixtures.h', 'patches/loopctrl/check_ngg2.py',
    'patches/loopctrl/check_initial_evidence081.py')
DISPLAY_LITERAL_CHANGES = {
    'necroprobe/test087.py': ('不明（判定できる証拠が不足しています）',
                            'のろいのゆびわとの一致は未確認（対象なしとは未確定）'),
    'necroprobe/ring_early.py': ('不明（対象なしとは確定しません）',
                               'のろいのゆびわとの一致は未確認（対象なしとは未確定）'),
}
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_',
    'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_', 'NECRO_TEST075_BASELINE_',
    'NECRO_TEST076_BASELINE_', 'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_',
    'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_', 'NECRO_TEST081_BASELINE_',
    'NECRO_TEST082_BASELINE_', 'NECRO_TEST083_BASELINE_', 'NECRO_TEST083_FRAMING_BASELINE_',
    'NECRO_TEST084_BASELINE_', 'NECRO_TEST084_NONFLOOR_', 'NECRO_TEST085_PROOF_',
    'NECRO_TEST085_STATIONARY_', 'NECRO_TEST086_', 'NECRO_TEST087_', 'NECRO_TEST090_')


def reject_fixture_overrides():
    present = sorted(name for name in os.environ
                     if name.startswith(FIXTURE_OVERRIDE_PREFIXES) or name == 'BASELINE_NAV')
    if present: raise ValueError('sealed fixture baseline overrides are forbidden: '+', '.join(present))


def selected_cases(cases):
    cases = list(cases); identifiers = [case.id() for case in cases]
    if not cases or len(identifiers) != len(set(identifiers)):
        raise ValueError('missing or duplicate device cases')
    return cases


def method_cases(case_type, methods, *, exact=False):
    available = set(unittest.defaultTestLoader.getTestCaseNames(case_type))
    if not methods or not methods <= available or (exact and available != set(methods)):
        raise ValueError('device method inventory changed: '+case_type.__name__)
    return selected_cases(case_type(method) for method in sorted(methods))


def native_suites(upstream):
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in NATIVE_CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for module in modules.values(): module.CORE = upstream/'LoopCtrlUITests'
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None: alias.CORE = upstream/'LoopCtrlUITests'
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in NATIVE_CASES]


def git(driver, *args):
    return subprocess.check_output(['git', *args], cwd=driver)


def pinned_bytes(driver, path, code):
    raw = (driver/path).read_bytes()
    if raw != git(driver, 'show', code+':'+path): raise ValueError('source differs from pinned commit: '+path)
    return raw


def expected_retained_bytes(path, baseline):
    if path not in DISPLAY_LITERAL_CHANGES: return baseline
    old, new = (value.encode() for value in DISPLAY_LITERAL_CHANGES[path])
    if baseline.count(old) != 1: raise ValueError('unknown display baseline is not unique: '+path)
    return baseline.replace(old, new)


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip(); retained = {}
    for path in RETAINED_PATHS:
        raw = pinned_bytes(driver, path, code)
        baseline = git(driver, 'show', NATIVE_BASELINE+':'+path)
        if raw != expected_retained_bytes(path, baseline):
            raise ValueError('retained TEST089 source changed: '+path)
        retained[path] = hashlib.sha256(raw).hexdigest()
    for name in CLIENT_MODULES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('client import escaped pinned driver: '+name)
    thin_entry = {}
    for old, new in (('necroprobe/test089.py', 'necroprobe/test090.py'), ('test_089.sh', 'test_090.sh')):
        raw = pinned_bytes(driver, new, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+old).replace(b'089', b'090'):
            raise ValueError('new entry differs beyond the test number: '+new)
        thin_entry[new] = hashlib.sha256(raw).hexdigest()
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
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    changed = {name for name in current if current[name] != old.get(name)}
    if set(current) != set(old) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('unexpected TEST090 native change scope')
    if current['LoopCtrlUITests/NG2Runtime.swift'] != RETAINED_RUNTIME_SHA256:
        raise ValueError('retained Runtime changed')
    names = ('NG2Controller.c', 'NG2Navigation.c', 'NG2Perception.c', 'NG2Beat.c',
             'NG2Controller.h', 'NG2Core.h', 'NG2Templates.h', 'NG2CaptureBridge.h')
    repository = {}
    for name in names:
        path = 'patches/loopctrl/ngg2/'+name; raw = pinned_bytes(driver, path, code)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != current['LoopCtrlUITests/'+name]: raise ValueError('repo C differs from IPA source: '+name)
        repository[name] = digest
    manifest = json.loads(pinned_bytes(driver, 'necroprobe/ring_native_manifest.json', code))
    old_manifest = json.loads(git(driver, 'show', NATIVE_BASELINE+':necroprobe/ring_native_manifest.json'))
    if set(manifest['sources']) != set(old_manifest['sources']): raise ValueError('ring source inventory changed')
    for path, digest in manifest['sources'].items():
        raw = pinned_bytes(driver, path, code)
        if hashlib.sha256(raw).hexdigest() != digest: raise ValueError('ring source hash mismatch: '+path)
        if path != 'tools/ring_native/icon.c' and raw != git(driver, 'show', NATIVE_BASELINE+':'+path):
            raise ValueError('unplanned ring source change: '+path)
    engine = pinned_bytes(driver, 'necroprobe/bin/ring-i386', code)
    if len(engine) != manifest['binary_bytes'] or hashlib.sha256(engine).hexdigest() != manifest['binary_sha256']:
        raise ValueError('ring executable differs from manifest')
    importlib.import_module('necroprobe.ring_native')._elf(engine)
    return dict(driver_commit=code, retained_source_sha256=retained,
        thin_entry_sha256=thin_entry,
        display_literal_only_changes=DISPLAY_LITERAL_CHANGES,
        native_baseline=NATIVE_BASELINE, changed_native_sources=sorted(changed),
        repository_native_source_sha256=repository, ring_manifest=manifest,
        reused_runtime_evidence=dict(status='not_run', baseline=NATIVE_BASELINE,
            source_sha256=RETAINED_RUNTIME_SHA256,
            reason='unchanged Runtime and fixture bytes; earlier execution is not a current pass'))


def run_scope(name, cases, output, evidence):
    cases = selected_cases(cases); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue(); (output/(name+'.txt')).write_text(log); print(log, end='', flush=True)
    evidence[name] = dict(selected=[case.id() for case in cases], tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures))
    (output/'test090-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if (result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures):
        raise RuntimeError(name+': every selected method must execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args(); driver, upstream, output = (
        getattr(args, name).resolve() for name in ('driver', 'upstream', 'output'))
    if not SCOPE_FINALIZED: raise ValueError('author inventories are not frozen')
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver/'tests'), str(driver/'patches/loopctrl')]
    verifier = importlib.import_module('verify_package'); before = verifier.inspect_native_sources(upstream, driver)
    if (before['api_version'], before['client_capability'], len(before['native_source_sha256'])) != (
            '1.98.16-ngg2', 'necrogold_native_v15', 22): raise ValueError('sealed source identity changed')
    source_before = source_identity(driver, before)
    suites = native_suites(upstream); selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name)) for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456):
        raise ValueError('native ABI changed')
    evidence = dict(scope='TEST090 observed HUD unit, revealed route and thin iron door',
        source_identity=before, production_source_binding=source_before, abi_bytes=abi, device_test='not_run',
        not_run=['historical full native/client/package/Runtime synthetic suites',
                 'private device replay corpus', 'unchanged TEST089 ring/collection semantics'],
        retained_runtime='prior evidence bound by unchanged bytes; not a current execution')
    for name, cases in suites: run_scope(name, cases, output, evidence)
    selector = importlib.import_module('test_device_ci090')
    run_scope('test090-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection090Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != before or source_identity(driver, before) != source_before:
        raise ValueError('selected tests changed production source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    evidence['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test090-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST090 selected units against exact IPA sources')


if __name__ == '__main__': main()
