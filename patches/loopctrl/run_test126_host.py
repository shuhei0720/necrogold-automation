"""TEST126 narrow source-bound capability checks; no gameplay suite replay."""
import argparse
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test126_source_utils', HERE/'run_test116_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = '1617fd2632b96267f05f1cbf1cfbe14dbb6fe740'
APP_NATIVE_BASELINE = 'c18db303a648571be4b3ff6afdd0e0f86b6458ce'
SCOPE_FINALIZED = True
PENDING_SCOPE_ITEMS = ()
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlUITests/NG2CycleSpool.swift'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset({
    'necroprobe/campaign116.py', 'necroprobe/test116.py',
    'patches/loopctrl/apply_ngg2.py', 'patches/loopctrl/ngg2-manifest.json',
    'patches/loopctrl/ngg2.patch', 'patches/loopctrl/ngg2/NG2CycleSpool.swift',
    'patches/loopctrl/verify_package.py',
    *('tests/test_continuous_client'+str(v)+'.py' for v in range(117, 126)),
})
NEW_PATHS = frozenset({
    '.github/workflows/test126-startup-memory.yml', 'necroprobe/test126.py', 'test_126.sh',
    'tests/test_continuous_client126.py', 'patches/loopctrl/check_cycle_spool126.py',
    'patches/loopctrl/ngg2_cycle_spool126_tests.swift', 'patches/loopctrl/test_device_ci126.py',
    'patches/loopctrl/run_test126_host.py', 'patches/loopctrl/run_test126_python39.py',
})
CAPABILITY_METHODS = frozenset({
    'test_current_patch_adds_126_without_replacing_118_119_120_or_121_or_122_or_123_or_124_or_125',
    'test_sealing_requires_one_real_uncommented_126_array_entry',
    'test_package_has_separate_126_field_and_unchanged_prior_API_and_profile',
    'test_resealed_mismatched_126_metadata_patch_or_rpc_is_rejected',
    'test_historical_125_manifest_gets_no_unrequested_126_field',
    'test_126_cannot_bypass_the_existing_125_package_binding',
})
SELECTOR_METHODS = frozenset({
    'test_native_inventory_accepts_only_spool_and_rpc_changes_among_all37',
    'test_native_inventory_rejects_missing_added_or_unrelated_sources',
    'test_api16_profile3_and_all_historical_caps_remain_required',
    'test_pending_author_scope_fails_closed',
    'test_python39_selects_exact_new14_startup14_and_direct19',
    'test_126_receipts_cannot_overwrite_125_or_each_other',
    'test_standalone_workflow_has_narrow_push_and_standard_runner_scope',
    'test_actual_build_profile_and_distinct_app_number_are_required',
})
EXPECTED_SELECTED_METHOD_COUNT = 14
SPOOL_CASES = ('work', 'retained', 'hash', '116-published_quota', '116-damaged_owner',
    '116-orphan_quota', '116-orphan_accounting', '116-alias_integrity', '116-recovered_quota',
    '116-recovery_namespace', 'snapshot_parity', 'hash_file_safety', 'hash_short', 'hash_growth')
SPOOL_INPUT_PATHS = ('patches/loopctrl/ngg2/NG2CycleSpool.swift',
    'patches/loopctrl/check_cycle_spool126.py', 'patches/loopctrl/ngg2_cycle_spool126_tests.swift',
    'patches/loopctrl/ngg2_cycle_spool116_tests.swift')
PRODUCT_PATHS = ('necroprobe/campaign116.py', 'necroprobe/campaign_forensic116.py',
    'necroprobe/test116.py', 'necroprobe/test125.py', 'necroprobe/test126.py',
    'necroprobe/native_cycle.py', 'necroprobe/protocol.py', 'necroprobe/validation.py',
    'test_125.sh', 'test_126.sh')
PRESERVED_PATHS = ('patches/loopctrl/ngg1.patch', 'patches/loopctrl/source-manifest.json',
    'patches/loopctrl/apply_patch.py', 'patches/loopctrl/check_perception_build.py',
    'patches/loopctrl/ngg2/NG2Controller.c', 'patches/loopctrl/ngg2/NG2Perception.c',
    'patches/loopctrl/ngg2/NG2Navigation.c', 'patches/loopctrl/ngg2/NG2Beat.c',
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2CycleWire.swift', 'patches/loopctrl/ngg2/NG2CycleExport.swift',
    'patches/loopctrl/ngg2_cycle_spool116_tests.swift', 'patches/loopctrl/ngg2_cycle_spool_tests.swift',
    'necroprobe/test125.py', 'test_125.sh', 'necroprobe/bin/ring-i386',
    '.github/workflows/loopctrl-geometry.yml')
EXPECTED_API = dict(shared.EXPECTED_API, visible_goods_capability='necrogold_native_visible_goods_v1',
    initial_restart_start_flag='initial_restart',
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    **{'device_fixes'+str(v)+'_capability': 'necrogold_native_device_fixes'+str(v)+'_v1'
       for v in range(119, 127)})
REPORTED_API_FIELDS = ('api_version', 'client_capability', 'cycle_capability', 'cycle_profile',
    'compiler_profile_version', 'device_fixes_capability',
    *('device_fixes'+str(v)+'_capability' for v in range(119, 127)))


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith(('NECRO_TEST', 'NECRO_NAV', 'NG2_TEST'))
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST126 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or PENDING_SCOPE_ITEMS:
        raise ValueError('TEST126 author inventories are pending; no tests may execute')
    if EXPECTED_SELECTED_METHOD_COUNT != len(CAPABILITY_METHODS)+len(SELECTOR_METHODS) or not all((
            EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, SPOOL_CASES)):
        raise ValueError('TEST126 source/method inventory is incomplete')


def native_inventory(old, current):
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (len(old) != 37 or len(current) != 37 or set(old) != set(current)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added):
        raise ValueError('TEST126 requires exactly two changed and 35 retained native sources')
    return changed, added


def source_identity(driver, sealed, upstream):
    ensure_scope(); reject_fixture_overrides()
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    if os.environ.get('GITHUB_SHA', code) != code:
        raise ValueError('TEST126 checkout differs from requested CODE')
    path = 'patches/loopctrl/ngg2-manifest.json'
    raw = pinned_bytes(driver, path, code); manifest = json.loads(raw)
    old = manifest_sources(json.loads(git(driver, 'show', NATIVE_BASELINE+':'+path)))
    app_old = manifest_sources(json.loads(git(driver, 'show', APP_NATIVE_BASELINE+':'+path)))
    if old != app_old:
        raise ValueError('TEST126 startup baseline differs from build278 native inventory')
    current = sealed['native_source_sha256']; changed, added = native_inventory(old, current)
    if (manifest_sources(manifest) != current
            or any(manifest.get(key) != value for key, value in EXPECTED_API.items())
            or any(sealed.get(key) != EXPECTED_API[key] for key in REPORTED_API_FIELDS)):
        raise ValueError('TEST126 installed source/API16/profile3/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test126_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST126 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST126 exact changed/new repository paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--').strip():
        raise ValueError('TEST126 working source differs from pinned CODE')
    unknown = {p.decode() for p in git(driver, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if p}
    if any(not p.startswith('docs/') for p in unknown):
        raise ValueError('TEST126 unpinned working source exists')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST126 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST126 canonical Ring15/R1240 inventory differs')
    selectors = sorted(p for p in baseline if p.startswith('patches/loopctrl/')
        and ((p.startswith('patches/loopctrl/run_test') and p.endswith(('_host.py', '_python39.py')))
             or p.startswith('patches/loopctrl/test_device_ci')))
    preserved = {}
    for name in dict.fromkeys((*ring['sources'], *r12, *PRESERVED_PATHS, *selectors)):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST126 preserved source changed: '+name)
        preserved[name] = sha(data)
    fixtures = set(SPOOL_INPUT_PATHS) | {p for p in NEW_PATHS if p.endswith(('.py', '.swift', '.yml', '.sh'))}
    return dict(schema='test126-production-source-binding-v1', driver_commit=code,
        native_baseline=NATIVE_BASELINE, app_native_baseline=APP_NATIVE_BASELINE,
        native_manifest_sha256=sha(raw), changed_native_sources=sorted(changed), native_added=sorted(added),
        preserved_native_source_sha256={n: v for n, v in current.items() if n not in changed},
        fixture_source_sha256={p: sha(pinned_bytes(driver, p, code)) for p in sorted(fixtures)},
        product_sha256={p: sha(pinned_bytes(driver, p, code)) for p in PRODUCT_PATHS},
        fixture_compile_source_binding=compile_binding, preserved_source_sha256=preserved,
        changed_repository_paths=sorted(existing), new_repository_paths=sorted(new),
        mac_case_groups=[dict(checker='check_cycle_spool126.py', cases=list(SPOOL_CASES))],
        historical_runtime_replayed=False, historical_spool_reuse=False,
        retained_root_compile_scope='driver additions byte-identical to installed seal; no gameplay C suites replayed',
        limitation='Software checks do not establish iPhone memory peak, completion, reach rate or speed.')


def run_scope(name, cases, output, evidence, *, receipt_name='test126-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test126-host-scope.json', 'test126-python39-scope.json'):
        raise ValueError('TEST126 scope receipt name is not permitted')
    cases = selected_cases(cases); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue(); (output/(name+'.txt')).write_text(log); print(log, end='', flush=True)
    evidence[name] = dict(selected=[c.id() for c in cases], tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures))
    (output/receipt_name).write_text(json.dumps(evidence, indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': selected methods must all execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args(); ensure_scope()
    driver, upstream, output = (getattr(args, n).resolve() for n in ('driver', 'upstream', 'output'))
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    verifier = importlib.import_module('verify_package')
    sealed = verifier.inspect_native_sources(upstream, driver); binding = source_identity(driver, sealed, upstream)
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(schema='test126-host-scope-v1', scope='TEST126 capability/package source boundary',
        source_identity=sealed, production_source_binding=binding, device_test='not_run',
        not_run=['gameplay C suites', 'full Runtime/fault/world collections', 'iPhone acceptance'])
    (output/'test126-source-identity.json').write_text(json.dumps(binding, indent=2)+'\n')
    if args.source_only:
        return
    capability = importlib.import_module('test_device_ci126')
    cases = method_cases(capability.DeviceImplementationCapability126Tests, CAPABILITY_METHODS, exact=True)
    run_scope('test126-capability', cases, output, evidence)
    selector = method_cases(capability.DeviceHostSelection126Tests, SELECTOR_METHODS, exact=True)
    run_scope('test126-selector', selector, output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST126 tests changed sealed source')
    evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test126-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST126 source-bound capability checks; device acceptance is separate')


if __name__ == '__main__':
    main()
