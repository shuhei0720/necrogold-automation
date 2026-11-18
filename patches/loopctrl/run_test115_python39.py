"""Actual Python 3.9 entry and the explicitly selected TEST115 client contracts."""
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
SCOPE_FINALIZED = False
CASES = (
    ('patches.loopctrl.test_device_ci115', 'DeviceHostSelection115Tests',
     'test115-python39-entry', frozenset({'test_entry_inherits_114_without_new_authority'}), False),
    ('tests.test_campaign_diagnostics114', 'CampaignDiagnostics114Tests',
     'test115-python39-retained-diagnostics', frozenset({
        'test_fixed_rpc_aggregates_bound_runs_and_store_no_request_bodies',
        'test_readonly_observation_runs_once_only_after_real_drain_before_collection',
     }), False),
    ('tests.test_campaign099', 'Campaign099Tests', 'test115-python39-retained-handoff',
     frozenset({'test_negative_handoff_publishes_before_new_uuid_and_stops_at_target'}), False),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_suite(driver):
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST115 actual Python 3.9 author scope is pending')
    spec = importlib.util.spec_from_file_location('test115_host_source_utils', HERE/'run_test115_host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    host.reject_fixture_overrides()
    selected = []
    for name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST115 Python fixture import escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    return host, host.selected_cases(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not SCOPE_FINALIZED:
        raise SystemExit('TEST115 actual Python 3.9 author scope is pending; no test executed')
    if sys.version_info[:2] != (3, 9) or platform.python_implementation() != 'CPython' or hasattr(0, 'bit_count'):
        raise SystemExit('Actual CPython 3.9 is required')
    driver, output = args.driver.resolve(), args.output.resolve()
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    host, selected = selected_suite(driver)
    host.ensure_scope()
    paths = (*host.PRODUCT_PATHS, *sorted(host.CLIENT_PRODUCT_CHANGES),
        'patches/loopctrl/run_test115_python39.py', 'patches/loopctrl/run_test115_host.py',
        *(row[0].replace('.', '/')+'.py' for row in CASES))
    code = subprocess.check_output(['git', '-C', str(driver), 'rev-parse', 'HEAD'], text=True).strip()
    before = {path: hashlib.sha256(host.pinned_bytes(driver, path, code)).hexdigest() for path in dict.fromkeys(paths)}
    syntax = subprocess.run(['sh', '-n', str(driver/'test_115.sh')], capture_output=True, text=True)
    check = subprocess.run([sys.executable, '-m', 'necroprobe.test115', '--check'], cwd=driver,
        capture_output=True, text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-device-failures-trial-v115 / 1.98.16-ngg2')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(selected))
    output.mkdir(parents=True, exist_ok=True)
    log = stream.getvalue()
    (output/'test115-python39.txt').write_text(log)
    print(sys.version)
    print(log, end='', flush=True)
    after = {name: sha(driver/name) for name in before}
    success = entry_ok and before == after and result.testsRun == len(selected) and (
        result.wasSuccessful() and not result.skipped and not result.expectedFailures)
    evidence = dict(driver_commit=code, scope='actual Python 3.9 selected TEST115 client contracts',
        interpreter_version=sys.version, interpreter=platform.python_implementation(),
        interpreter_executable_sha256=sha(Path(sys.executable).resolve()),
        python_version=list(sys.version_info[:3]), selected=[case.id() for case in selected],
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
        source_sha256=before, sources_unchanged=before == after, product_pass=success,
        shell_syntax=dict(returncode=syntax.returncode, stdout=syntax.stdout, stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr),
        device_test='not_run')
    (output/'test115-python39-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if not success:
        raise SystemExit('TEST115 actual Python 3.9 selected methods/entry must all execute Green')


if __name__ == '__main__':
    main()
