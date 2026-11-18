"""Actual CPython 3.9; TEST117 methods plus the unchanged TEST116 40 cases."""
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
_spec = importlib.util.spec_from_file_location('test117_python39_shared116', HERE/'run_test116_python39.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
SCOPE_FINALIZED = True
CASES = shared.CASES + (
    ('tests.test_continuous_client117', 'ContinuousClientNamespace117Tests', 'test117-python39-namespace', frozenset({
        'test_117_schema_is_a_distinct_supported_collection_namespace',
        'test_old_default_retains_116_schema_and_number_is_a_closed_set',
        'test_selector_and_selectorless_history_refuse_another_requested_number',
        'test_selected_history_cannot_swap_to_another_schema_at_the_same_root',
        'test_number_mismatch_and_wrong_spool_make_no_native_requests',
        'test_117_live_chain_uses_117_names_and_retains_every_published_child',
        'test_117_uncertain_start_recovers_same_root_without_another_post',
        'test_117_orphan_remains_diagnostic_and_retains_original_scope',
        'test_117_closed_recovery_rechecks_saved_publication_without_new_start',
    }), True),
    ('tests.test_continuous_client117', 'ContinuousClientCapability117Tests', 'test117-python39-capability', frozenset({
        'test_117_client_requires_visible_goods_implementation',
        'test_both_modes_require_new_capability_without_changing_old_client',
        'test_old_ipa_schema_blocks_before_continuous_native_start',
    }), True),
    ('tests.test_continuous_client117', 'ContinuousClientEntry117Tests', 'test117-python39-entry', frozenset({
        'test_check_and_finite_routing_have_117_identity',
        'test_continuous_and_saved_recovery_pass_exact_namespace_and_no_mode_mix',
    }), True),
    ('tests.test_initial_restart117', 'InitialRestartClient117Tests', 'test117-python39-initial-restart', frozenset({
        'test_both_117_modes_explicitly_request_initial_restart',
        'test_117_true_only_closed_start_shape_is_admitted',
        'test_117_does_not_silently_omit_the_initial_reset',
        'test_continuous_pipeline_posts_the_flag_once',
        'test_finite_pipeline_posts_the_flag_once',
        'test_116_keeps_omitting_and_rejecting_the_new_mode',
        'test_false_untyped_flags_other_profiles_and_extra_fields_are_rejected',
        'test_start_and_cancel_reply_mode_must_match_exactly',
        'test_trait_is_boolean_and_only_uses_the_irregular_protocol',
        'test_uncertain_initial_start_is_never_resent_in_either_pipeline',
        'test_provenance_true_is_read_only_and_false_numeric_or_foreign_is_rejected',
    }), True),
)


def selected_suite(driver):
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST117 actual Python 3.9 author scope is pending')
    spec = importlib.util.spec_from_file_location('test117_python39_host', HERE/'run_test117_host.py')
    host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
    host.ensure_scope(); host.reject_fixture_overrides()
    selected = []
    for name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST117 Python fixture escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    return host, host.selected_cases(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not SCOPE_FINALIZED:
        raise SystemExit('TEST117 actual Python 3.9 scope is pending; no tests executed')
    if sys.version_info[:2] != (3, 9) or platform.python_implementation() != 'CPython' or hasattr(0, 'bit_count'):
        raise SystemExit('Actual CPython 3.9 is required')
    driver, output = args.driver.resolve(), args.output.resolve()
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    host, selected = selected_suite(driver)
    paths = (*host.PRODUCT_PATHS, 'patches/loopctrl/run_test117_python39.py',
        'patches/loopctrl/run_test117_host.py', 'patches/loopctrl/run_test116_python39.py',
        *(row[0].replace('.', '/')+'.py' for row in CASES))
    code = subprocess.check_output(['git', '-C', str(driver), 'rev-parse', 'HEAD'], text=True).strip()
    before = {path: hashlib.sha256(host.pinned_bytes(driver, path, code)).hexdigest() for path in dict.fromkeys(paths)}
    syntax = subprocess.run(['sh', '-n', str(driver/'test_117.sh')], capture_output=True, text=True)
    check = subprocess.run([sys.executable, '-m', 'necroprobe.test117', '--check'], cwd=driver, capture_output=True, text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-device-failures-trial-v117 / 1.98.16-ngg2')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(driver_commit=code, scope='actual Python 3.9 TEST117 and TEST116 client contracts',
        interpreter_version=sys.version, interpreter=platform.python_implementation(),
        interpreter_executable_sha256=shared.sha(Path(sys.executable).resolve()), python_version=list(sys.version_info[:3]),
        source_sha256=before, shell_syntax=dict(returncode=syntax.returncode, stdout=syntax.stdout, stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr), device_test='not_run')
    host.run_scope('test117-python39', selected, output, evidence)
    after = {name: shared.sha(driver/name) for name in before}
    evidence.update(sources_unchanged=before == after, product_pass=entry_ok and before == after)
    (output/'test117-python39-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if not evidence['product_pass']:
        raise SystemExit('TEST117 actual Python 3.9 entry/source identity must pass')


if __name__ == '__main__':
    main()
