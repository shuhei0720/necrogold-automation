"""Execute only TEST081 initial decision retention in the real Runtime cache/export.

The fixed previous Runtime receives the same HOST-only raster/snapshot seeding
methods as Green. Production pin/selection/export bytes are never stubbed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import check_ngg2 as existing

HERE = Path(__file__).resolve().parent
BASELINE_COMMIT = 'acf684bd0eb7b73ac5239e02f0879f9474470b35'
BASELINE_RUNTIME_SHA256 = 'bfb0f271ca4504b7c428661a597c0fc070db29d993904f70c9020abb76b549f7'
CASES = (
    'test081InitialDecisionSurvivesPressure',
    'test081InitialDecisionFirstOnlyAndMetadata',
    'test081InitialDecisionInvalidEvidence',
    'test081InitialDecisionBothCachePaths',
    'test081InitialDecisionBudgetsAndPriority',
    'test081InitialDecisionOwnershipAndMissing',
)
RED_ASSERT = 'FAIL test081_initial_decision_source_survives_pressure'
HOST_BEGIN = '// TEST081 RETENTION HOST METHOD BEGIN.\n'
HOST_END = '// TEST081 RETENTION HOST METHOD END.\n'
FIXTURE_BEGIN = '// TEST081 RETENTION FIXTURE BEGIN.\n'
FIXTURE_END = '// TEST081 RETENTION FIXTURE END.\n'
DIGEST = lambda raw: hashlib.sha256(raw).hexdigest()


def region(source, begin, end):
    if source.count(begin) != 1 or source.count(end) != 1:
        raise ValueError('test081_fixture_boundary')
    return source.split(begin, 1)[1].split(end, 1)[0]


def instrument_runtime(source, host):
    marker = '    // TEST056 HOST METHOD BEGIN.\n'
    if source.count(marker) != 1 or HOST_BEGIN in source:
        raise ValueError('test081_runtime_host_seam_boundary')
    return source.replace(marker, HOST_BEGIN + host + HOST_END + marker, 1)


def fixture_source(tests, fixture, *, baseline):
    marker = '// This public request is intentionally runnable'
    if tests.count(marker) != 1:
        raise ValueError('test081_common_declaration_boundary')
    begin = '// TEST051 PUBLIC FIXTURES BEGIN.\n'
    end = 'func testContinuousRevalidationCallbacksPublic()'
    if tests.count(begin) != 1 or tests.count(end) != 1:
        raise ValueError('test081_export_fixture_boundary')
    export_helpers = tests.split(begin, 1)[1].split(end, 1)[0]
    calls = CASES[:1] if baseline else CASES
    return (tests.split(marker, 1)[0] + export_helpers + fixture + '\n'
            + ''.join(name+'()\n' for name in calls)
            + 'print("PASS production Runtime public API/TEST081 bounded initial decision evidence")\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--red-only', action='store_true')
    mode.add_argument('--green-only', action='store_true')
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    upstream, output = args.upstream.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    native = upstream/'LoopCtrlUITests'
    original = (native/'NG2Runtime.swift').read_bytes()
    if args.red_only:
        original = subprocess.check_output(['git', 'show', BASELINE_COMMIT+':patches/loopctrl/ngg2/NG2Runtime.swift'], cwd=HERE)
        if DIGEST(original) != BASELINE_RUNTIME_SHA256:
            raise ValueError('test081_fixed_previous_Runtime_hash')
    raw_fixture = (HERE/'ngg2_initial_evidence081_tests.swift').read_bytes()
    text = raw_fixture.decode()
    host = region(text, HOST_BEGIN, HOST_END)
    fixture = region(text, FIXTURE_BEGIN, FIXTURE_END)
    generated = fixture_source((HERE/'ngg2_runtime_tests.swift').read_text(), fixture, baseline=args.red_only)
    seam_native = output/'native-with-host-seam'
    if seam_native.exists():
        raise ValueError('test081_output_must_be_fresh')
    shutil.copytree(native, seam_native)
    instrumented = instrument_runtime(original.decode(), host)
    (seam_native/'NG2Runtime.swift').write_text(instrumented)
    (output/'api').mkdir()
    types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
    if len(types) != 2:
        raise ValueError('test081_rpc_types_boundary')
    (output/'api/RPCTypes.swift').write_text(types[0])
    objects, native_sources = existing.test061_native_objects(native, output)
    existing.test056_public_fixture_source = lambda _: generated
    actual = []
    compile_run = existing.compile_run
    label = 'test081-retention-baseline-red' if args.red_only else 'test081-retention-production-green'

    def run(sources, executable, destination, ignored_label, extra=(), *, run_timeout=60):
        result = compile_run(sources, executable, destination, label, extra, run_timeout=120)
        actual.append(result)
        return result

    existing.compile_run = run
    try:
        existing.runtime_contract(upstream, output, baseline_native=seam_native,
                                  public056_only=True, native_objects=objects)
    except subprocess.CalledProcessError:
        if not args.red_only or len(actual) != 1:
            raise
    if len(actual) != 1:
        raise RuntimeError('test081_exactly_one_compiled_execution_required')
    result = actual[0]
    if args.red_only:
        existing.require_red(result, RED_ASSERT)
    else:
        existing.checked(result)
        passes = [line for line in result.stdout.splitlines() if line.startswith('PASS TEST081 ')]
        if len(passes) != 6 or result.stderr or not result.stdout.strip().endswith(
                'PASS production Runtime public API/TEST081 bounded initial decision evidence'):
            raise RuntimeError('test081_exact_six_green_cases_required')
    report = {
        'schema': 'test081-retention-contract-v1', 'status': 'pass',
        'mode': 'baseline_red' if args.red_only else 'production_green',
        'compiled': True, 'returncode': result.returncode,
        'baseline_commit': BASELINE_COMMIT if args.red_only else None,
        'runtime_source_sha256': DIGEST(original),
        'host_instrumented_runtime_sha256': DIGEST(instrumented.encode()),
        'host_seam_sha256': DIGEST(host.encode()),
        'fixture_file_sha256': DIGEST(raw_fixture),
        'executed_fixture_sha256': DIGEST(generated.encode()),
        'entrypoints': list(CASES[:1] if args.red_only else CASES),
        'semantic_red_assertion': RED_ASSERT if args.red_only else None,
        'native_sources': native_sources,
        'stdout': result.stdout, 'stderr': result.stderr, 'device_test': 'not_run',
        'scope': 'HOST-only synthetic raster/metadata pressure through production cache, pin and PNG export; no C decision, input or game progress asserted',
    }
    (output/'ngg2-test081-retention-contract.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status','mode','compiled','returncode','runtime_source_sha256','fixture_file_sha256','entrypoints')}, indent=2))


if __name__ == '__main__':
    main()
