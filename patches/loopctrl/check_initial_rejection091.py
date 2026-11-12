"""Focused Runtime initial-rejection retention: immutable Red then current Green.

Only HOST raster/snapshot setup is injected. Real Runtime validation, bounded
pin retention, cache eviction, ownership and public paged export are exercised.
The six unchanged TEST081 cases share the Green executable and current C objects.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import check_ngg2 as existing
import check_initial_evidence081 as legacy

HERE = Path(__file__).resolve().parent
BASELINE_COMMIT = 'c9e087050f5d6c7c30d8385014ea0909e534c963'
BASELINE_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
LEGACY_FIXTURE_SHA256 = '302c4875593c2bf9c33ab2d9f6d6b1b17198ba791a1203a62075db876bb3d205'
LEGACY_CHECKER_SHA256 = '27be3b7c0be9c53e8df78f92f34c2fa9abb522efa9c17f99c51148eb813c9db7'
CASES = (
    'test091InitialRejectionSurvivesPressure',
    'test091InitialRejectionMetadataAndDeferred',
    'test091InitialRejectionGuards',
    'test091InitialRejectionReplacementAndMissing',
    'test091InitialRejectionBudgetsAndOwner',
)
RED_ASSERT = 'FAIL test091_initial_rejection_source_survives_pressure'
FOOTER = 'PASS production Runtime public API/TEST091 initial rejection and TEST081 retained evidence'
GREEN_LINES = (
    'PASS TEST091 initial rejection preserves seven critical twelve map and one spare',
    'PASS TEST091 original metadata and immediate deferred terminal or recovering snapshots',
    'PASS TEST091 precise snapshot owner prefix ID begin0 SCREEN and zero input guards',
    'PASS TEST091 single bounded replacement and honest missing raster',
    'PASS TEST091 full paged 10MiB owner fence and unchanged legacy 4MiB',
    *legacy.GREEN_LINES[:-1],
    FOOTER,
)
HOST_BEGIN = '// TEST091 INITIAL REJECTION HOST METHOD BEGIN.\n'
HOST_END = '// TEST091 INITIAL REJECTION HOST METHOD END.\n'
FIXTURE_BEGIN = '// TEST091 INITIAL REJECTION FIXTURE BEGIN.\n'
FIXTURE_END = '// TEST091 INITIAL REJECTION FIXTURE END.\n'
DIGEST = lambda raw: hashlib.sha256(raw).hexdigest()


def fixture_source(tests, old_fixture, fixture, *, baseline):
    marker = '// This public request is intentionally runnable'
    begin = '// TEST051 PUBLIC FIXTURES BEGIN.\n'
    end = 'func testContinuousRevalidationCallbacksPublic()'
    if tests.count(marker) != 1 or tests.count(begin) != 1 or tests.count(end) != 1:
        raise ValueError('test091_shared_public_fixture_boundary')
    export_helpers = tests.split(begin, 1)[1].split(end, 1)[0]
    # Both fixed c9 and current Runtime already support v2. No baseline profile
    # or product behavior shim is needed; only the case list differs.
    calls = CASES[:1] if baseline else CASES+legacy.CASES
    return (tests.split(marker, 1)[0]+export_helpers
            +'let test081EvidenceProfile = true\n'+old_fixture+'\n'+fixture+'\n'
            +''.join(name+'()\n' for name in calls)
            +'print('+json.dumps(FOOTER)+')\n')


def run_mode(upstream, output, original, raw_fixture, raw_legacy, objects, native_sources, *, baseline):
    output.mkdir(parents=True, exist_ok=False)
    text = raw_fixture.decode()
    host = legacy.region(text, HOST_BEGIN, HOST_END)
    fixture = legacy.region(text, FIXTURE_BEGIN, FIXTURE_END)
    old_text = raw_legacy.decode()
    old_host = legacy.region(old_text, legacy.HOST_BEGIN, legacy.HOST_END)
    old_fixture = legacy.region(old_text, legacy.FIXTURE_BEGIN, legacy.FIXTURE_END)
    generated = fixture_source((HERE/'ngg2_runtime_tests.swift').read_text(), old_fixture, fixture, baseline=baseline)
    seam_native = output/'native-with-host-seam'
    shutil.copytree(upstream/'LoopCtrlUITests', seam_native)
    marker = '    // TEST056 HOST METHOD BEGIN.\n'
    source = original.decode()
    if source.count(marker) != 1 or HOST_BEGIN in source or legacy.HOST_BEGIN in source:
        raise ValueError('test091_Runtime_HOST_seam_boundary')
    instrumented = source.replace(marker, legacy.HOST_BEGIN+old_host+legacy.HOST_END
        +HOST_BEGIN+host+HOST_END+marker, 1)
    (seam_native/'NG2Runtime.swift').write_text(instrumented)
    (output/'api').mkdir()
    types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
    if len(types) != 2:
        raise ValueError('test091_RPC_types_boundary')
    (output/'api/RPCTypes.swift').write_text(types[0])
    actual = []
    compile_run = existing.compile_run
    old_fixture_source = existing.test056_public_fixture_source
    label = 'test091-initial-rejection-baseline-red' if baseline else 'test091-initial-rejection-production-green'

    def run(sources, executable, destination, ignored_label, extra=(), *, run_timeout=60):
        result = compile_run(sources, executable, destination, label, extra, run_timeout=300)
        actual.append(result)
        return result

    existing.compile_run = run
    existing.test056_public_fixture_source = lambda _: generated
    try:
        try:
            existing.runtime_contract(upstream, output, baseline_native=seam_native,
                                      public056_only=True, native_objects=objects)
        except subprocess.CalledProcessError:
            if not baseline or len(actual) != 1:
                raise
        except RuntimeError as error:
            # This focused executable has its own exact stdout contract. The
            # historical shared footer check must not rewrite process results.
            if not (not baseline and len(actual) == 1
                    and error.args == ('runtime_production_contract_missing',)):
                raise
    finally:
        existing.compile_run = compile_run
        existing.test056_public_fixture_source = old_fixture_source
    if len(actual) != 1:
        raise RuntimeError('test091_exactly_one_compiled_execution_per_mode')
    result = actual[0]
    if baseline:
        existing.require_red(result, RED_ASSERT)
    else:
        existing.checked(result)
        if result.stderr or result.stdout != '\n'.join(GREEN_LINES)+'\n':
            raise RuntimeError('test091_exact_five_new_and_six_unchanged_green_cases')
    report = {
        'mode': 'baseline_red' if baseline else 'production_green',
        'compiled': True, 'returncode': result.returncode,
        'baseline_commit': BASELINE_COMMIT if baseline else None,
        'runtime_source_sha256': DIGEST(original),
        'host_instrumented_runtime_sha256': DIGEST(instrumented.encode()),
        'new_host_seam_sha256': DIGEST(host.encode()),
        'legacy_host_seam_sha256': DIGEST(old_host.encode()),
        'fixture_file_sha256': DIGEST(raw_fixture),
        'legacy_fixture_file_sha256': DIGEST(raw_legacy),
        'executed_fixture_sha256': DIGEST(generated.encode()),
        'entrypoints': list(CASES[:1] if baseline else CASES+legacy.CASES),
        'semantic_red_assertion': RED_ASSERT if baseline else None,
        'profile_input': 'normal-1-1-evidence-v2',
        'native_sources': native_sources,
        'stdout': result.stdout, 'stderr': result.stderr,
        'device_test': 'not_run',
    }
    (output/'ngg2-test091-initial-rejection-mode.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--red-only', action='store_true')
    mode.add_argument('--green-only', action='store_true')
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    upstream, output = args.upstream.resolve(), args.output.resolve()
    if output.exists():
        raise ValueError('test091_output_must_be_fresh')
    output.mkdir(parents=True)
    native = upstream/'LoopCtrlUITests'
    current = (native/'NG2Runtime.swift').read_bytes()
    baseline = subprocess.check_output(['git', 'show', BASELINE_COMMIT+
        ':patches/loopctrl/ngg2/NG2Runtime.swift'], cwd=HERE)
    if DIGEST(baseline) != BASELINE_RUNTIME_SHA256:
        raise ValueError('test091_immutable_c9_Runtime_hash')
    raw_fixture = (HERE/'ngg2_initial_rejection091_tests.swift').read_bytes()
    raw_legacy = (HERE/'ngg2_initial_evidence081_tests.swift').read_bytes()
    legacy_checker = (HERE/'check_initial_evidence081.py').read_bytes()
    if DIGEST(raw_legacy) != LEGACY_FIXTURE_SHA256 or DIGEST(legacy_checker) != LEGACY_CHECKER_SHA256:
        raise ValueError('test091_TEST081_fixture_and_checker_must_remain_unchanged')
    native_output = output/'native-current'; native_output.mkdir()
    objects, native_sources = existing.test061_native_objects(native, native_output)
    reports = []
    if not args.green_only:
        reports.append(run_mode(upstream, output/'baseline-red', baseline, raw_fixture, raw_legacy,
                                objects, native_sources, baseline=True))
    if not args.red_only:
        reports.append(run_mode(upstream, output/'production-green', current, raw_fixture, raw_legacy,
                                objects, native_sources, baseline=False))
    if (raw_fixture != (HERE/'ngg2_initial_rejection091_tests.swift').read_bytes()
            or raw_legacy != (HERE/'ngg2_initial_evidence081_tests.swift').read_bytes()
            or legacy_checker != (HERE/'check_initial_evidence081.py').read_bytes()
            or current != (native/'NG2Runtime.swift').read_bytes()):
        raise ValueError('test091_sources_changed_during_focused_execution')
    value = {
        'schema': 'test091-initial-rejection-contract-v1', 'status': 'pass',
        'mode': 'baseline_red' if args.red_only else 'production_green' if args.green_only else 'baseline_red_then_production_green',
        'compiled': True, 'baseline_commit': BASELINE_COMMIT,
        'baseline_runtime_sha256': BASELINE_RUNTIME_SHA256,
        'current_runtime_sha256': DIGEST(current),
        'fixture_file_sha256': DIGEST(raw_fixture),
        'checker_file_sha256': DIGEST(Path(__file__).read_bytes()),
        'legacy_fixture_file_sha256': DIGEST(raw_legacy),
        'legacy_checker_file_sha256': DIGEST(legacy_checker),
        'native_sources': native_sources, 'results': reports,
        'new_entrypoints': list(CASES), 'legacy_entrypoints': list(legacy.CASES),
        'retention_limits': {'critical': 7, 'restart_decisions': 12, 'initial_rejection': 1,
                             'maximum_images': 20, 'maximum_bytes': 10*1024*1024},
        'device_test': 'not_run',
        'temporal_baseline_red_before_product_edit': False,
        'temporal_limitation': 'Fixture and hash were frozen before the Runtime pin product edit in an authoring environment without Swift. The immutable-baseline assertion Red and current assertion Green are executed later in the same Mac job, not claimed as a pre-edit semantic Red.',
        'scope': 'HOST-only coherent snapshot/raster seeds through actual Runtime retention/eviction/public paged PNG export. No C decision, iPhone input, received capture175 reconstruction, or game progress is asserted.',
    }
    (output/'ngg2-test091-initial-rejection-contract.json').write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps({key:value[key] for key in ('schema','status','mode','compiled','fixture_file_sha256','baseline_runtime_sha256','current_runtime_sha256')}, indent=2))


if __name__ == '__main__':
    main()
