"""Actual Python 3.9 client/publication contracts for the TEST111 device lane.

This is a separate interpreter execution from the native C host selector.
It sends no device traffic and does not claim phone acceptance.
"""
import argparse
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SCOPE_FINALIZED = True  # Final author actual-Python3.9 inventory: 7 new + 14 directly related retained.
CASES = (
    ('tests.test_client111', 'ImagePriceClient111Tests', 'test111-python-ImagePriceClient111Tests', frozenset({
        'test_capability_is_advertised_without_changing_api_or_profile',
        'test_entry_check_identifies_new_client_and_keeps_test110_default',
        'test_entry_client_must_match_explicit_protocol_identity',
        'test_entry_selects_only_new_explicit_client',
        'test_new_cap_is_additional_and_uses_one_schema_request',
        'test_old_clients_keep_their_default_capability_contract',
        'test_old_ipa_is_rejected_before_trial_support_or_game_start',
    }), True),
    ('tests.test_native_cycle_client094', 'CycleClient094Tests', 'test111-python-CycleClient094Tests', frozenset({
        'test_schema_requires_current_api_new_capability_and_integer_protocol',
    }), False),
    ('tests.test_campaign099', 'Campaign099Tests', 'test111-python-Campaign099Tests', frozenset({
        'test_trial_client_reads_feature_every_preflight_and_rejects_old_or_malformed',
        'test_unsupported_trial_feature_stops_before_any_native_start',
    }), False),
    ('tests.test_native_irregular_client110', 'IrregularClient110Tests', 'test111-python-IrregularClient110Tests', frozenset({
        'test_api16_schema_requires_both_caps_and_keeps_unrelated_tags',
        'test_old_and_new_admission_do_not_follow_reply_selected_profiles',
        'test_trial_preflight_uses_only_selected_sibling_query',
    }), False),
    ('tests.test_native_irregular_client110', 'IrregularPublication110Tests', 'test111-python-IrregularPublication110Tests', frozenset({
        'test_missing_capability_starts_zero_and_no_game_identity_is_replaced',
        'test_test110_entry_selects_new_protocol_and_old_entry_stays_default',
    }), False),
    ('tests.test_client100', 'Client100Tests', 'test111-python-Client100Tests', frozenset({
        'test_default_test099_labels_and_recovery_stay_unchanged',
        'test_test100_archive_index_and_nested_run_use_separate_label',
        'test_test100_entry_routes_own_spool_and_preserves_closed_test_number',
        'test_test100_interrupted_collection_recovers_same_uuid_and_label',
    }), True),
    ('tests.test_client101', 'Client101Tests', 'test111-python-Client101Tests', frozenset({
        'test_entry101_isolates_labels_and_recovers_same_uuid_without_continuing',
        'test_shell101_checks_own_module_and_rejects_conflicting_modes_before_start',
    }), True),
)
PRODUCT_PATHS = (
    'necroprobe/native_cycle.py', 'necroprobe/irregular.py',
    'necroprobe/cycle_publication.py', 'necroprobe/campaign099.py',
    'necroprobe/trial_evidence099.py', 'necroprobe/test099.py',
    'necroprobe/test110.py', 'test_110.sh',
    'necroprobe/test111.py', 'test_111.sh',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_suite(driver):
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST111 Python 3.9 author scope is pending')
    spec = importlib.util.spec_from_file_location('test111_host_source_utils', HERE / 'run_test111_host.py')
    host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
    host.reject_fixture_overrides()
    selected = []
    for module_name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(module_name)
        if Path(module.__file__).resolve() != driver / (module_name.replace('.', '/') + '.py'):
            raise ValueError('Python 3.9 fixture import escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    return host.selected_cases(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(); driver = args.driver.resolve(); output = args.output.resolve()
    if sys.version_info[:2] != (3, 9) or hasattr(0, 'bit_count'):
        raise SystemExit('Actual Python 3.9 is required; another interpreter is not compatibility proof')
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver / 'tests'), str(HERE)]
    selected = selected_suite(driver)
    paths = (*PRODUCT_PATHS, 'patches/loopctrl/run_test111_python39.py',
        'patches/loopctrl/run_test111_host.py',
        *(row[0].replace('.', '/') + '.py' for row in CASES))
    before = {name: sha(driver / name) for name in dict.fromkeys(paths)}
    code = subprocess.check_output(['git', '-C', str(driver), 'rev-parse', 'HEAD'], text=True).strip()
    for name, digest in before.items():
        pinned = subprocess.check_output(['git', '-C', str(driver), 'show', code + ':' + name])
        if hashlib.sha256(pinned).hexdigest() != digest:
            raise ValueError('Python 3.9 source differs from pinned CODE: ' + name)
    syntax = subprocess.run(['sh', '-n', str(driver / 'test_111.sh')], capture_output=True, text=True)
    check = subprocess.run([sys.executable, '-m', 'necroprobe.test111', '--check'], cwd=driver,
        capture_output=True, text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-image-price-trial-v1 / 1.98.16-ngg2')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(selected))
    log = stream.getvalue(); (output / 'test111-python39.txt').write_text(log)
    print(sys.version); print(log, end='', flush=True)
    after = {name: sha(driver / name) for name in before}
    success = entry_ok and before == after and result.testsRun == len(selected) and (
        result.wasSuccessful() and not result.skipped and not result.expectedFailures)
    evidence = dict(driver_commit=code, scope='actual Python 3.9 selected client/publication contracts',
        interpreter_version=sys.version, interpreter=platform.python_implementation(),
        interpreter_executable_sha256=sha(Path(sys.executable).resolve()),
        python_version=list(sys.version_info[:3]), selected=[case.id() for case in selected],
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
        source_sha256=before, sources_unchanged=before == after, product_pass=success,
        shell_syntax=dict(returncode=syntax.returncode, stdout=syntax.stdout, stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr),
        device_test='not_run')
    (output / 'test111-python39-scope.json').write_text(json.dumps(evidence, indent=2) + '\n')
    if not success:
        raise SystemExit('TEST111 Python 3.9 selected methods/entry must all execute Green')


if __name__ == '__main__':
    main()
