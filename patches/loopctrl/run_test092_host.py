"""TEST092 selected units bound to the exact sealed IPA source.

Reuse TEST090 inventory helpers, without its historical pins or exceptions.
Runtime's startup boundary has its own selected Mac fixture; old full suites are not dispatched.
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
    'test092_shared090', Path(__file__).with_name('run_test090_host.py'))
shared = importlib.util.module_from_spec(_shared_spec)
_shared_spec.loader.exec_module(shared)

NATIVE_BASELINE = '5ddb6c6a38ccab8dc49bcfe518560ceadb99144f'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c',
                           'LoopCtrlUITests/NG2Navigation.c',
                           'LoopCtrlUITests/NG2Runtime.swift'}
SCOPE_FINALIZED = True
# Author method inventories are completed only after meaningful Red/Green.
NATIVE_CASES = (
    ('tests.test_native_gold_stationary092', 'NativeGoldStationary092Tests', 'test092-gold-stationary',
     frozenset({'test_lighting_drift_with_stable_gold_confirms_only_zero',
                'test_complete_nonhud_old_terrain_gold_and_safe_floor_are_required',
                'test_raw_finite_zero_and_independent_texture_competition_are_required',
                'test_known_motion_and_nonzero_surfaces_cannot_be_overwritten'}), True),
    ('tests.test_native_unlocalized_passage092', 'NativeUnlocalizedPassage092Tests', 'test092-unlocalized-passage',
     frozenset({'test_positive_clipped_gold_approaches_only_an_independently_supported_passage',
                'test_hint_without_a_supported_mouth_or_safe_surface_never_authorizes_input',
                'test_independent_pair_rejects_crossing_and_changing_hint_classification',
                'test_first_positive_hint_survives_later_clear_and_local_goal_without_restart',
                'test_observed_gold_handoff_releases_the_local_passage_for_shop_navigation',
                'test_positive_mode_preserves_cancellation_unknown_ack_and_original_budgets',
                'test_gold_stationary_proof_keeps_unsent_ticket_timing_and_credit'}), True),
    ('tests.test_native_stationary_texture085', 'NativeStationaryTexture085Tests', 'test092-related-stationary085',
     frozenset({'test_public_clear_floor_zero_requires_independent_stationary_evidence'}), False),
    ('tests.test_native_terrain_axis091', 'NativeTerrainAxis091Tests', 'test092-related-unit091',
     frozenset({'test_public_unit_requires_new_independent_axis_proof'}), False),
    ('tests.test_native_passage072', 'NativePassage072Tests', 'test092-related-passage072',
     frozenset({'test_gold_clear_passage_moves_on_observed_floor_instead_of_restarting',
                'test_moved_gold_reveal_uses_normal_shop_without_restart',
                'test_final_vantage_requires_independent_clear_before_restart'}), False),
    ('tests.test_native_view074', 'NativeView074Tests', 'test092-related-view074',
     frozenset({'test_faded_candidate_closes_before_first_move_only_after_two_wall_frames',
                'test_unknown_or_inconsistent_support_cannot_discard_a_candidate'}), False),
    ('tests.test_native_initial_scene091', 'NativeInitialScene091Tests', 'test092-related-initial091',
     frozenset({'test_unknown_gold_withdraws_and_requires_two_new_clear_frames',
                'test_recovery_allowance_is_two_and_initial_deadline_never_restarts'}), False),
)
PYTHON_CASES = (
    ('tests.test_ring_status092', 'RingStatus092Tests', 'test092-ring-status',
     frozenset({'test_completed_and_unavailable_assessment_have_distinct_execution_status',
                'test_target_candidate_and_unknown_keep_their_existing_meaning',
                'test_unreadable_product_row_is_evaluated_but_never_confirmed_absent',
                'test_early_and_final_display_share_the_completed_label_without_extra_work',
                'test_engine_failure_never_reports_a_completed_or_absent_result'}), True),
    ('tests.test_target_publication087', 'TargetPublication087Tests', 'test092-related-display087',
     frozenset({'test_new_entry_connects_prepare_and_displays_only_target_candidate_or_unknown'}), False),
)
CORE_MODULES = shared.CORE_MODULES
CLIENT_MODULES = shared.CLIENT_MODULES + ('necroprobe.ring_status',)
RETAINED_PATHS = shared.RETAINED_PATHS + (
    'necroprobe/test090.py', 'test_090.sh', 'patches/loopctrl/run_test090_host.py',
    'necroprobe/test091.py', 'test_091.sh', 'patches/loopctrl/run_test091_host.py',
    'patches/loopctrl/check_initial_rejection091.py',
    'patches/loopctrl/ngg2_initial_rejection091_tests.swift')
NEW_UI_SHA256 = {'necroprobe/ring_status.py':
    '9a2cf63d49628564092c3dac978b1f549fb29f7ce6c99ac2a32d9589aad4c53d'}
MODIFIED_DISPLAY_FIXTURE_SHA256 = 'ee28c025454984282eb2b29f98e991251734dafe7b15a06ce035a5d1df5fee2f'
selected_cases = shared.selected_cases
method_cases = shared.method_cases
git = shared.git
pinned_bytes = shared.pinned_bytes


UI_REPLACEMENTS = {
    'necroprobe/test087.py': (
        ('from .target_assessment import AssessmentError, prepare_assessment\n', 'from .target_assessment import AssessmentError, prepare_assessment\nfrom .ring_status import assessment_label\n'),
        ('指輪判定中。保存済みの画像を確認しています。', '指輪判定中。商品画像の有無と保存状態を確認しています。'),
        ("    label = {'target': 'のろいのゆびわ（アイコンと名前が一致）',\n             'candidate': '指輪候補（保持して目視確認してください）',\n             'unknown': 'のろいのゆびわとの一致は未確認（対象なしとは未確定）'}[value['outcome']]", "    label = assessment_label(value['outcome'], has_sources=bool(value['sources']))"),
    ),
    'necroprobe/ring_early.py': (
        ('from . import native_walk as native, ring_native, target_assessment as target\n', 'from . import native_walk as native, ring_native, target_assessment as target\nfrom .ring_status import assessment_label\n'),
        ("            label = {'target': 'のろいのゆびわ（アイコンと名前が一致）',\n                     'candidate': '指輪候補（保持して目視確認してください）',\n                     'unknown': 'のろいのゆびわとの一致は未確認（対象なしとは未確定）'}[outcome]", '            label = assessment_label(outcome, has_sources=bool(self._cache))'),
    ),
}

def reject_fixture_overrides():
    shared.reject_fixture_overrides()
    if any(name.startswith(('NECRO_TEST091_', 'NECRO_TEST092_')) for name in os.environ):
        raise ValueError('sealed TEST092 fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not NATIVE_CASES:
        raise ValueError('TEST092 author inventories are not frozen')
    labels = [row[2] for row in (*NATIVE_CASES, *PYTHON_CASES)]
    if len(labels) != len(set(labels)) or not any(row[4] for row in NATIVE_CASES):
        raise ValueError('TEST092 scope is empty or duplicated')


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


def python_suites():
    return [(label, method_cases(getattr(importlib.import_module(name), klass), methods, exact=exact))
            for name, klass, label, methods, exact in PYTHON_CASES]


def expected_retained_bytes(path, baseline):
    for old, new in UI_REPLACEMENTS.get(path, ()):
        old, new = old.encode(), new.encode()
        if baseline.count(old) != 1:
            raise ValueError('display baseline is not unique: '+path)
        baseline = baseline.replace(old, new, 1)
    return baseline


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    retained = {}
    for path in RETAINED_PATHS:
        raw = pinned_bytes(driver, path, code)
        if raw != expected_retained_bytes(path, git(driver, 'show', NATIVE_BASELINE+':'+path)):
            raise ValueError('retained TEST091 source changed: '+path)
        retained[path] = hashlib.sha256(raw).hexdigest()
    new_ui = {}
    for path, digest in NEW_UI_SHA256.items():
        raw = pinned_bytes(driver, path, code)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('reviewed UI formatter changed: '+path)
        new_ui[path] = digest
    display_fixture = 'tests/test_target_publication087.py'
    if hashlib.sha256(pinned_bytes(driver, display_fixture, code)).hexdigest() != MODIFIED_DISPLAY_FIXTURE_SHA256:
        raise ValueError('reviewed display fixture metadata changed')
    for name in CLIENT_MODULES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('client import escaped pinned driver: '+name)
    thin = {}
    for old, new in (('necroprobe/test091.py', 'necroprobe/test092.py'),
                     ('test_091.sh', 'test_092.sh')):
        raw = pinned_bytes(driver, new, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+old).replace(b'091', b'092'):
            raise ValueError('new entry differs beyond the test number: '+new)
        thin[new] = hashlib.sha256(raw).hexdigest()
    before = json.loads(git(driver, 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    changed = {name for name in current if current[name] != old.get(name)}
    if set(current) != set(old) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('unexpected TEST092 native change scope')
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
        added_ui_source_sha256=new_ui, modified_display_fixture_sha256=MODIFIED_DISPLAY_FIXTURE_SHA256,
        changed_native_sources=sorted(changed), repository_native_source_sha256=repository,
        ring_manifest=manifest, runtime_validation='selected TEST092 startup fixture; historical full suites not run')


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
    (output/'test092-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
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
    evidence = dict(scope='TEST092 selected startup/stationary/unlocalized/display cases', source_identity=before,
        production_source_binding=source_before, abi_bytes=abi, device_test='not_run',
        not_run=['historical full native/client/package/Runtime synthetic suites',
                 'private device replay corpus', 'unchanged TEST091 classifier/kernel/collection semantics'])
    suites += python_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    for name, cases in suites:
        run_scope(name, cases, output, evidence)
    selector = importlib.import_module('test_device_ci092')
    run_scope('test092-selector', unittest.defaultTestLoader.loadTestsFromTestCase(
        selector.DeviceHostSelection092Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != before or source_identity(driver, before) != source_before:
        raise ValueError('selected tests changed production source')
    reject_fixture_overrides()
    evidence['sealed_sources_unchanged_after_tests'] = True
    evidence['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test092-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST092 selected units against exact IPA sources')


if __name__ == '__main__':
    main()
