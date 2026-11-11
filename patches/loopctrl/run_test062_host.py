"""Run only TEST074 rendered-view confirmation and motion evidence changes and related units before device feedback.

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


VIEW074_METHODS = frozenset({
    'test_skip_uses_first_floor_start_and_a_later_independent_capture',
    'test_faded_candidate_closes_before_first_move_only_after_two_wall_frames',
    'test_reserved_false_candidate_retires_and_switches_to_confirmed_new_mouth',
    'test_unknown_or_inconsistent_support_cannot_discard_a_candidate',
    'test_prefix_unstable_overlap_and_old_frames_cannot_confirm_drawing_or_wall',
    'test_new_gold_and_goods_take_priority_over_initial_negative_or_wall_wait',
    'test_genuine_post_ui_passage_reaches_first_move_and_moved_origin_is_not_reclassified',
    'test_initial_wait_retains_original_sync_session_and_unknown_input_limits',
    'test_restart_exploration_and_goods_stay_one_bounded_native_session',
    'test_uncertain_drawing_waits_for_gold_or_two_clear_observations_without_ending',
})
MOTION074_METHODS = frozenset({
    'test_stationary_lighting_opening_has_gradient_evidence_in_four_directions',
    'test_clear_floor_detail_and_unique_terrain_prove_one_move',
    'test_gradient_opening_requires_the_same_bracket_and_safe_endpoints',
    'test_gradient_uses_common_known_terrain_and_two_independent_bands',
    'test_gradient_rejects_opposite_sign_axis_disagreement_and_ambiguous_texture',
    'test_passage_move_requires_all_stones_and_a_noncollinear_dirt_anchor',
    'test_passage_move_requires_clear_unprotected_floor_and_no_goods',
    'test_arrival_proof_does_not_authorize_or_require_a_future_step',
    'test_reverse_partial_two_cells_and_wrong_direction_never_receive_one_move',
    'test_unit_move_detail_rejects_weak_one_region_and_repeated_fields',
    'test_original_primary_classification_and_invalid_abi_remain_unchanged',
})
RELATED_UI_METHODS = frozenset({
    'test_final_begin_rechecks_latest_floor_and_live_control',
})
RELATED_CONTROLLER_METHODS = frozenset({
    'test_twelve_changed_restarts_bound_and_no_thirteenth',
    'test_restart_unchanged_timeout_never_resends',
    'test_goods_frame_preserves_evidenced_move_before_holding_pause',
    'test_unknown_synth_and_started_cancel_freeze_even_pause',
    'test_initial_sync_twelve_second_limit_and_walk_forty_five',
})
RELATED_NAVIGATION_METHODS = frozenset({
    'test_signature_normalization_and_all73_scores_exact_reference',
})
RELATED_MOTION_METHODS = frozenset({
    'test_existing_normal_moves_blocks_openings_and_unexpected_are_preserved',
})
RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})
NATIVE_CASES = (
    ('tests.test_native_view074', 'NativeView074Tests', 'test074-view', VIEW074_METHODS, True),
    ('tests.test_native_motion074', 'NativeMotion074Tests', 'test074-motion', MOTION074_METHODS, True),
    ('tests.test_native_ui073', 'NativeUI073Tests', 'test074-related-ui', RELATED_UI_METHODS, False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test074-related-controller', RELATED_CONTROLLER_METHODS, False),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test074-related-navigation', RELATED_NAVIGATION_METHODS, False),
    ('tests.test_native_motion067', 'NativeMotion067Tests', 'test074-related-motion', RELATED_MOTION_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test074-related-recovery', RECOVERY_METHODS, False),
)
CLIENT_CASES = ()
PACKAGE_CASES = ()
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception', 'tests.test_native_navigation',
                'tests.test_native_ui073', 'test_native_ui073', 'test_native_perception')
NATIVE_BASELINE = '7901c5fd0f1f4d030923aaab1027b8cc38730e0c'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test074')
FIXTURE_OVERRIDE_PREFIX = 'NECRO_TEST074_BASELINE_'


def reject_fixture_overrides():
    present = sorted(name for name in os.environ if name.startswith(FIXTURE_OVERRIDE_PREFIX))
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
        sources[name] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
    if (native.REVISION != 'native-walk-v15' or native.API_VERSION != '1.98.16-ngg2'
            or native.CAPABILITY != 'necrogold_native_v14'):
        raise ValueError('collection client revision/API/capability changed')
    return {'modules': sources, 'driver_commit': code, 'revision': native.REVISION, 'api_version': native.API_VERSION,
            'capability': native.CAPABILITY}


def client_suites():
    modules = {name: importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native = importlib.import_module('necroprobe.native_walk')
    publication = importlib.import_module('necroprobe.test069')
    entry = importlib.import_module('necroprobe.test074')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST074 entry is not bound to the actual driver publication wrapper')
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
        raise ValueError('TEST074 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST074 native change scope differs')
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
    record = {'scope': 'TEST074 rendered-view confirmation and motion evidence units and named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'fixture_source_policy': {'baseline_override_env_prefix': FIXTURE_OVERRIDE_PREFIX,
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime integration and mutations (separate Mac step)', 'synthetic shop/world suites',
                          'unselected client and RPC suites', 'unchanged package/profile and client version unit suites',
                          'unrelated initial/icon/unsent suites',
                          'unselected workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test074-view': 'independent post-drawing confirmation and origin-only unsent candidate refresh preserve uncertain views, goods, prefix and original budgets',
                  'test074-motion': 'supplemental opening and unit-move evidence keeps primary decisions, original thresholds and explicit terrain/region/ambiguity guards',
                  'test074-related-ui': 'final PAUSE begin still checks the latest floor and live control after drawing confirmation',
                  'test074-related-controller': 'retain twelve restart cap, unchanged fingerprint timeout, goods credit, unknown/cancel no retry and original sync/walk clocks',
                  'test074-related-navigation': 'retain exact normalization and all73 original intensity scores',
                  'test074-related-motion': 'retain existing primary normal moves, blocks, openings and unexpected-motion classifications',
                  'test074-related-recovery': 'unchanged public ABI confirmed through actual C queries'}}
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
    print('PASS TEST074 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
