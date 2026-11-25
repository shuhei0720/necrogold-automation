"""Actual CPython3.9: TEST121 and directly related retained client contracts.

75 selected methods =12111 +12011 +11911 +11811 +11725 +1166. The remaining34 methods
from the unchanged116 transport/forensic scope are not replayed or claimed.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test121_python39_shared120', HERE/'run_test120_python39.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
SCOPE_FINALIZED = True
RETAINED_CASES = shared.CASES
NEW_CASES = (
    ('tests.test_continuous_client121', 'ContinuousClient121Tests', 'test121-python39-client', frozenset({
        'test_116_117_118_119_120_121_histories_remain_isolated_with_or_without_selector',
        'test_121_schema_is_distinct_and_only_supported_numbers_are_admitted',
        'test_both_modes_require_121_implementation_without_changing_old_clients',
        'test_check_and_finite_entry_use_121_identity',
        'test_continuous_and_saved_recovery_entry_keep_121_namespace',
        'test_finite_mode_keeps_the_single_initial_restart_post',
        'test_live_chain_keeps_121_archives_and_posts_initial_restart_once',
        'test_old_ipa_is_blocked_before_either_pipeline_sends_native_requests',
        'test_shell_has_121_identity_and_rejects_conflicting_modes_before_device_use',
        'test_uncertain_start_recovers_same_root_without_a_second_post',
        'test_wrong_history_or_spool_makes_no_native_request',
    }), True),
)
CASES = RETAINED_CASES + NEW_CASES


def host_module():
    spec = importlib.util.spec_from_file_location('test121_python39_host', HERE/'run_test121_host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    return host


def selected_suite(driver):
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST121 actual Python3.9 author scope is pending')
    host = host_module()
    host.ensure_scope()
    host.reject_fixture_overrides()
    selected = []
    for name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST121 Python fixture escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    return host, host.selected_cases(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not SCOPE_FINALIZED:
        raise SystemExit('TEST121 actual Python3.9 author scope is pending; no tests executed')
    if sys.version_info[:2] != (3,9) or platform.python_implementation() != 'CPython' or hasattr(0,'bit_count'):
        raise SystemExit('Actual CPython3.9 is required')
    driver, output = args.driver.resolve(), args.output.resolve()
    sys.path[:0] = [str(driver),str(driver/'tests'),str(HERE)]
    host, selected = selected_suite(driver)
    paths = (*host.PRODUCT_PATHS, '.github/workflows/loopctrl-geometry.yml',
        'patches/loopctrl/run_test121_python39.py','patches/loopctrl/run_test121_host.py',
        'patches/loopctrl/run_test120_python39.py','patches/loopctrl/run_test119_python39.py',
        'patches/loopctrl/run_test118_python39.py',
        'patches/loopctrl/run_test117_python39.py',
        'patches/loopctrl/run_test116_python39.py',
        'patches/loopctrl/run_test094_host.py','patches/loopctrl/run_test116_host.py',
        'patches/loopctrl/run_test117_host.py','tests/test_protocol.py',*(row[0].replace('.','/')+'.py' for row in CASES))
    code = subprocess.check_output(['git','-C',str(driver),'rev-parse','HEAD'],text=True).strip()
    before = {name:hashlib.sha256(host.pinned_bytes(driver,name,code)).hexdigest() for name in dict.fromkeys(paths)}
    syntax = subprocess.run(['sh','-n',str(driver/'test_121.sh')],capture_output=True,text=True)
    check = subprocess.run([sys.executable,'-m','necroprobe.test121','--check'],cwd=driver,capture_output=True,text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-device-failures-trial-v121 / 1.98.16-ngg2')
    output.mkdir(parents=True,exist_ok=True)
    evidence = dict(driver_commit=code,scope='actual Python3.9 TEST121 and selected retained client contracts',
        interpreter_version=sys.version,interpreter=platform.python_implementation(),
        interpreter_executable_sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
        python_version=list(sys.version_info[:3]),source_sha256=before,
        shell_syntax=dict(returncode=syntax.returncode,stdout=syntax.stdout,stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode,stdout=check.stdout,stderr=check.stderr),
        not_run=['TEST116 remaining34 unchanged transport/forensic methods; prior evidence only',
            'Runtime/spool/Mac worlds are outside this client step; no new Runtime boundary changed',
            'iPhone acceptance'],device_test='not_run')
    host.run_scope('test121-python39',selected,output,evidence,receipt_name='test121-python39-scope.json')
    after = {name:hashlib.sha256((driver/name).read_bytes()).hexdigest() for name in before}
    evidence.update(sources_unchanged=before == after,product_pass=entry_ok and before == after)
    (output/'test121-python39-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if not evidence['product_pass']:
        raise SystemExit('TEST121 actual Python3.9 entry/source identity must pass')


if __name__ == '__main__':
    main()
