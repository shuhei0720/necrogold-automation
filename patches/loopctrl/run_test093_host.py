"""TEST093 selected Controller units bound to the exact sealed IPA source.

Reuse TEST090 stateless inventory helpers. Unchanged client and Runtime092
bytes retain historical evidence; no Runtime or UI suite is dispatched here.
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
    'test093_shared090', Path(__file__).with_name('run_test090_host.py'))
shared = importlib.util.module_from_spec(_shared_spec)
_shared_spec.loader.exec_module(shared)

NATIVE_BASELINE = '732a3d33a5c7512b0185ec2430aed187cdd0ec78'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c'}
# Frozen after the author's six-method Red/Green; related methods stay intact.
SCOPE_FINALIZED = True
NATIVE_CASES = (
    ('tests.test_native_opened_entry093', 'NativeOpenedEntry093Tests',
     'test093-opened-entry', frozenset({
         'test_projected_top_goods_growth_and_shrink_use_latest_separate_ticket',
         'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
         'test_projection_surface_gold_and_motion_counterexamples_reject_revalidation',
         'test_original_ticket_windows_epochs_and_actual_begin_boundaries_are_frozen',
         'test_expired_partial_entry_reacquires_independent_future_permission',
         'test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative'}), True),
    ('tests.test_native_clipped_entry081', 'NativeClippedEntry081Tests',
     'test093-related-clipped081', frozenset({
         'test_clipped_partial_goods_preserve_original_up_entry_then_real_move_and_goods_hold',
         'test_source_mask_and_top_gold_quarantine_survive_mask_zero_return',
         'test_new_protection_nonedge_items_gold_or_near_changes_cannot_use_quarantine'}), False),
    ('tests.test_native_shop071', 'NativeShop071Tests',
     'test093-related-shop071', frozenset({
         'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker',
         'test_exception_does_not_allow_other_local_cells_materials_or_missing_open_ack'}), False),
    ('tests.test_native_open_entry077', 'NativeOpenEntry077Tests',
     'test093-related-open077', frozenset({
         'test_opened_entry_reveal_preserves_ticket_then_enters_on_original_beat',
         'test_accepted_new_gold_cannot_disappear_or_shift_within_same_ticket'}), False),
    ('tests.test_native_device065', 'NativeDevice065Tests',
     'test093-related-expiry065', frozenset({
         'test_pending_same_and_fresh_expiry_reacquire_without_rewriting_retired_ticket'}), False))
PYTHON_CASES = ()
CORE_MODULES = shared.CORE_MODULES
CLIENT_MODULES = shared.CLIENT_MODULES + ('necroprobe.ring_status',)
RETAINED_PATHS = shared.RETAINED_PATHS + (
    'necroprobe/test090.py', 'test_090.sh', 'patches/loopctrl/run_test090_host.py',
    'necroprobe/test091.py', 'test_091.sh', 'patches/loopctrl/run_test091_host.py',
    'patches/loopctrl/check_initial_rejection091.py',
    'patches/loopctrl/ngg2_initial_rejection091_tests.swift',
    'necroprobe/test092.py', 'test_092.sh', 'patches/loopctrl/run_test092_host.py',
    'patches/loopctrl/test_device_ci092.py',
    'patches/loopctrl/check_startup092.py', 'patches/loopctrl/ngg2_startup092_tests.swift',
    'necroprobe/ring_status.py', 'tests/test_target_publication087.py',
    'tests/test_native_gold_stationary092.py', 'tests/test_native_unlocalized_passage092.py',
    'tests/test_ring_status092.py')
RETAINED_RUNTIME_SHA256 = 'd18e74419ab557d86a9514ced3de5dc5aaa3f8efcfa9fac2e71208b01fa0ff0a'
selected_cases = shared.selected_cases
method_cases = shared.method_cases
git = shared.git
pinned_bytes = shared.pinned_bytes


def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith(('NECRO_TEST091_', 'NECRO_TEST092_', 'NECRO_TEST093_')) for name in os.environ):
        raise ValueError('sealed TEST093 fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not NATIVE_CASES:
        raise ValueError('TEST093 author inventories are not frozen')
    labels = [row[2] for row in (*NATIVE_CASES, *PYTHON_CASES)]
    if len(labels) != len(set(labels)) or not any(row[4] for row in NATIVE_CASES):
        raise ValueError('TEST093 scope is empty or duplicated')


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
            raise ValueError('retained TEST092 baseline source changed: '+path)
        retained[path] = hashlib.sha256(raw).hexdigest()
    for name in CLIENT_MODULES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('client import escaped pinned driver: '+name)
    thin = {}
    for old, new in (('necroprobe/test092.py', 'necroprobe/test093.py'),
                     ('test_092.sh', 'test_093.sh')):
        raw = pinned_bytes(driver, new, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+old).replace(b'092', b'093'):
            raise ValueError('new entry differs beyond the test number: '+new)
        thin[new] = hashlib.sha256(raw).hexdigest()
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    changed = {name for name in current if current[name] != old.get(name)}
    if set(current) != set(old) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('unexpected TEST093 native change scope')
    if current.get('LoopCtrlUITests/NG2Runtime.swift') != RETAINED_RUNTIME_SHA256:
        raise ValueError('historical TEST092 Runtime evidence no longer applies')
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
        ring_manifest=manifest, runtime_validation='unchanged TEST092 Runtime; historical nine-plus-one receipt only, no current Runtime execution',
        retained_runtime_sha256=RETAINED_RUNTIME_SHA256)


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
    (output/'test093-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
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
    evidence = dict(scope='TEST093 selected Controller door-opening cases', source_identity=before,
        production_source_binding=source_before, abi_bytes=abi, device_test='not_run',
        not_run=['historical full native/client/package/Runtime synthetic suites',
                 'private device replay corpus', 'unchanged TEST092 Runtime startup nine-plus-one and UI semantics',
                 'unchanged classifier/kernel/collection semantics'])
    selected_cases(case for _label, cases in suites for case in cases)
    for name, cases in suites:
        run_scope(name, cases, output, evidence)
    selector = importlib.import_module('test_device_ci093')
    run_scope('test093-selector', unittest.defaultTestLoader.loadTestsFromTestCase(
        selector.DeviceHostSelection093Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != before or source_identity(driver, before) != source_before:
        raise ValueError('selected tests changed production source')
    reject_fixture_overrides()
    evidence['sealed_sources_unchanged_after_tests'] = True
    evidence['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test093-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST093 selected units against exact IPA sources')


if __name__ == '__main__':
    main()
