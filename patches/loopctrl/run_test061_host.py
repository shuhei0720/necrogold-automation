"""Run TEST061's selected host contracts against sealed patched IPA sources.

Private PNG replays remain required local checks. This lane does not execute
the historical Runtime mutation inventory or native world160.
"""
import argparse
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import unittest


PRIVATE_CONTROLLER = frozenset({
    'test_required_test057_actual055_classification_and_original_down_motion',
    'test_required_test051_actual77_79_reissue_same_up_after_synthetic_lead_in',
    'test_required_test052_three_flickers_before_initial_publication',
    'test_required_test053_original_reference_after_reissue',
    'test_required_test057_actual053_identical_tiles_keep_original_authority',
})
NATIVE_CASES = (
    ('tests.test_native_controller', 'NativeControllerTests', 'test061-controller'),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test061-recovery'),
    ('tests.test_native_beat', 'NativeBeatTests', 'test061-beat'),
    ('tests.test_native_recovery_world', 'NativeRecoveryWorldTests', 'test061-world'),
)
WORLD_METHODS = frozenset({
    'test_slow_camera_all_directions_wood_and_iron_reach_full_goods',
    'test_turn_left_then_up_open_enter_and_hold_goods',
    'test_same_service_without_camera_tween_reaches_full_goods',
})


def flatten(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite):
            yield from flatten(case)
        else:
            yield case


def selected_cases(suite, excluded=frozenset()):
    cases = list(flatten(suite))
    identifiers = [case.id() for case in cases]
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError('missing or duplicate selected cases')
    found = {case.id().rsplit('.', 1)[-1] for case in cases
             if case.id().rsplit('.', 1)[-1] in excluded}
    if found != set(excluded):
        raise ValueError('explicit private replay inventory changed: ' + repr(found))
    selected = [case for case in cases
                if case.id().rsplit('.', 1)[-1] not in excluded]
    if not selected:
        raise ValueError('no public cases selected')
    return selected


def native_suites(upstream):
    # Bind every module before loading or running classes. Recovery helpers
    # import the same qualified Controller module, avoiding a second CORE.
    modules = {name: importlib.import_module(name) for name, _, _ in NATIVE_CASES}
    for module in modules.values():
        module.CORE = upstream / 'LoopCtrlUITests'
    # The focused world imports this independent oracle using its historical
    # bare module name. Bind that exact object without loading its world160 class.
    modules['tests.test_native_recovery_world'].base.CORE = upstream / 'LoopCtrlUITests'
    suites = []
    for name, class_name, label in NATIVE_CASES:
        cases = selected_cases(unittest.defaultTestLoader.loadTestsFromTestCase(
            getattr(modules[name], class_name)),
            PRIVATE_CONTROLLER if label == 'test061-controller' else frozenset())
        if label == 'test061-world':
            actual = {case.id().rsplit('.', 1)[-1] for case in cases}
            if actual != WORLD_METHODS:
                raise ValueError('explicit focused world method inventory changed: ' + repr(actual))
        suites.append((label, cases))
    return suites


def run_scope(name, cases, output, record):
    cases = selected_cases(unittest.TestSuite(cases))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestSuite(cases))
    log = stream.getvalue()
    (output / (name + '.txt')).write_text(log)
    print(log, end='', flush=True)
    record[name] = {
        'selected': [case.id() for case in cases],
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'expected_failures': len(result.expectedFailures),
    }
    (output / 'test061-host-scope.json').write_text(json.dumps(record, indent=2) + '\n')
    if (result.testsRun != len(cases) or not result.wasSuccessful()
            or result.skipped or result.expectedFailures):
        raise RuntimeError(name + ': selected tests must execute without failures/errors/skips')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    driver = args.driver.resolve()
    upstream = args.upstream.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver / 'tests'), str(driver / 'patches/loopctrl')]
    verifier = importlib.import_module('verify_package')
    before = verifier.inspect_native_sources(upstream, driver)
    if (before['api_version'] != '1.98.15-ngg2'
            or before['client_capability'] != 'necrogold_native_v13'
            or len(before['native_source_sha256']) != 22):
        raise ValueError('TEST061 sealed source identity is not installed')
    record = {
        'scope': 'all public Controller methods, new recovery, Beat, focused world and package contracts',
        'excluded_private_controller': sorted(PRIVATE_CONTROLLER),
        'source_identity': before,
        'device_test': 'not_run',
        'not_run': ['Runtime historical 59 mutations', 'native world160',
                    'private PNG replays (required local checks)',
                    'client contracts (separate native-client workflow; same-commit result required)'],
    }
    for name, cases in native_suites(upstream):
        run_scope(name, cases, output, record)
    packages = unittest.defaultTestLoader.discover(
        str(driver / 'patches/loopctrl'), pattern='test_*.py')
    run_scope('test061-package', flatten(packages), output, record)
    after = verifier.inspect_native_sources(upstream, driver)
    if after != before:
        raise ValueError('selected tests changed the sealed production source inputs')
    record['sealed_sources_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256(
        (driver / 'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output / 'test061-host-scope.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS TEST061 selected host contracts against patched upstream; no private skips')


if __name__ == '__main__':
    main()
