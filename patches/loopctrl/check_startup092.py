"""Focused Runtime startup portrait handoff: fixed previous Red/current Green.

The original raster, capture bridge and input machinery are used. Only HOST
capture replies, clocks and negative guard state are supplied by the fixture.
One unchanged TEST091 priority/pin case shares the current executable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import check_ngg2 as existing
import check_initial_evidence081 as legacy081
import check_initial_rejection091 as legacy091

HERE = Path(__file__).resolve().parent
BASELINE_COMMIT = '5ddb6c6a38ccab8dc49bcfe518560ceadb99144f'
BASELINE_RUNTIME_SHA256 = 'a2f6b36fdf3998d895e69b49ccfe272ad12767d2863db4c0f5bdf73a65c687c1'
CASES = (
    'test092FirstPortraitWaitsForLandscape',
    'test092StartupBounds',
    'test092LateAdmittedNormalKeepsCaptureContract',
    'test092OtherFailuresRemainImmediate',
    'test092NormalAndAnalysisFailuresEndWait',
    'test092AuthorityFences',
    'test092QueuedQueryCancelRetainsLease',
    'test092TimeoutStillDrainsExactCallback',
    'test092StableInitialGuards',
)
RELATED_CASES = ('test091InitialRejectionSurvivesPressure',)
RED_ASSERT = 'FAIL test092_first_portrait_waits_for_landscape_without_rotation_input_or_relaunch'
FOOTER = 'PASS production Runtime public API/TEST092 bounded startup and TEST091 pin preservation'
GREEN_LINES = (
    'PASS TEST092 initial portrait waits for independently normal landscape without input',
    'PASS TEST092 original three second deadline and sixty four portrait limit',
    'PASS TEST092 already admitted normal reply retains original capture completion contract',
    'PASS TEST092 square source reply and other EXIF failures retain immediate stop',
    'PASS TEST092 normal raster permanently ends wait and analysis failure remains immediate',
    'PASS TEST092 fresh query rejects cancellation owner lock foreground generation and stale time',
    'PASS TEST092 queued foreground query cancellation retains lease until main returns',
    'PASS TEST092 timeout retains exact callback drain and original capture stop',
    'PASS TEST092 initial prefix inflight and expected PID boundaries remain strict',
    legacy091.GREEN_LINES[0],
    FOOTER,
)
HOST_BEGIN = '// TEST092 STARTUP HOST METHOD BEGIN.\n'
HOST_END = '// TEST092 STARTUP HOST METHOD END.\n'
FIXTURE_BEGIN = '// TEST092 STARTUP FIXTURE BEGIN.\n'
FIXTURE_END = '// TEST092 STARTUP FIXTURE END.\n'
DIGEST = lambda raw: hashlib.sha256(raw).hexdigest()
LEGACY_FILES = ('ngg2_initial_evidence081_tests.swift', 'ngg2_initial_rejection091_tests.swift',
                'check_initial_evidence081.py', 'check_initial_rejection091.py')


def declarations(raw, begin, end):
    return legacy081.region(raw.decode(), begin, end)


def parts(raw_fixture, old081, old091):
    return (
        (declarations(old081, legacy081.HOST_BEGIN, legacy081.HOST_END),
         declarations(old091, legacy091.HOST_BEGIN, legacy091.HOST_END),
         declarations(raw_fixture, HOST_BEGIN, HOST_END)),
        (declarations(old081, legacy081.FIXTURE_BEGIN, legacy081.FIXTURE_END),
         declarations(old091, legacy091.FIXTURE_BEGIN, legacy091.FIXTURE_END),
         declarations(raw_fixture, FIXTURE_BEGIN, FIXTURE_END)),
    )


def fixture_source(tests, fixtures, *, baseline):
    marker = '// This public request is intentionally runnable'
    begin = '// TEST051 PUBLIC FIXTURES BEGIN.\n'
    end = 'func testContinuousRevalidationCallbacksPublic()'
    if tests.count(marker) != 1 or tests.count(begin) != 1 or tests.count(end) != 1:
        raise ValueError('test092_shared_public_fixture_boundary')
    export_helpers = tests.split(begin, 1)[1].split(end, 1)[0]
    calls = CASES[:1] if baseline else CASES+RELATED_CASES
    return (tests.split(marker, 1)[0]+export_helpers
            +'let test081EvidenceProfile = true\n'+'\n'.join(fixtures)+'\n'
            +''.join(name+'()\n' for name in calls)+'print('+json.dumps(FOOTER)+')\n')


def instrument_runtime(original, hosts):
    marker = '    // TEST056 HOST METHOD BEGIN.\n'
    if original.count(marker) != 1 or HOST_BEGIN in original or legacy081.HOST_BEGIN in original:
        raise ValueError('test092_original_Runtime_HOST_seam_boundary')
    return original.replace(marker, '\n'.join(hosts)+'\n'+marker, 1)


def run_mode(upstream, output, original, raw_fixture, old081, old091, objects, native_sources, *, baseline):
    output.mkdir(parents=True, exist_ok=False)
    hosts, fixtures = parts(raw_fixture, old081, old091)
    generated = fixture_source((HERE/'ngg2_runtime_tests.swift').read_text(), fixtures, baseline=baseline)
    seam_native = output/'native-with-host-seam'
    shutil.copytree(upstream/'LoopCtrlUITests', seam_native)
    instrumented = instrument_runtime(original.decode(), hosts)
    (seam_native/'NG2Runtime.swift').write_text(instrumented)
    (output/'api').mkdir()
    types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
    if len(types) != 2:
        raise ValueError('test092_RPC_types_boundary')
    (output/'api/RPCTypes.swift').write_text(types[0])
    actual = []
    compile_run, old_fixture_source = existing.compile_run, existing.test056_public_fixture_source
    label = 'test092-startup-baseline-red' if baseline else 'test092-startup-production-green'

    def run(sources, executable, destination, ignored_label, extra=(), *, run_timeout=60):
        result = compile_run(sources, executable, destination, label, extra, run_timeout=180)
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
            if not (not baseline and len(actual) == 1
                    and error.args == ('runtime_production_contract_missing',)):
                raise
    finally:
        existing.compile_run, existing.test056_public_fixture_source = compile_run, old_fixture_source
    if len(actual) != 1:
        raise RuntimeError('test092_one_compiled_execution_per_mode')
    result = actual[0]
    if baseline:
        existing.require_red(result, RED_ASSERT)
    else:
        existing.checked(result)
        if result.stderr or result.stdout != '\n'.join(GREEN_LINES)+'\n':
            raise RuntimeError('test092_exact_nine_new_and_one_related_green_cases')
    value = {
        'mode': 'baseline_red' if baseline else 'production_green',
        'compiled': True, 'returncode': result.returncode,
        'baseline_commit': BASELINE_COMMIT if baseline else None,
        'runtime_source_sha256': DIGEST(original),
        'host_instrumented_runtime_sha256': DIGEST(instrumented.encode()),
        'host_seams_sha256': [DIGEST(part.encode()) for part in hosts],
        'fixture_declarations_sha256': [DIGEST(part.encode()) for part in fixtures],
        'fixture_file_sha256': DIGEST(raw_fixture),
        'executed_fixture_sha256': DIGEST(generated.encode()),
        'entrypoints': list(CASES[:1] if baseline else CASES+RELATED_CASES),
        'semantic_red_assertion': RED_ASSERT if baseline else None,
        'native_sources': native_sources,
        'stdout': result.stdout, 'stderr': result.stderr,
        'device_test': 'not_run',
    }
    (output/'ngg2-test092-startup-mode.json').write_text(json.dumps(value, indent=2)+'\n')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    upstream, output = args.upstream.resolve(), args.output.resolve()
    if output.exists():
        raise ValueError('test092_output_must_be_fresh')
    output.mkdir(parents=True)
    native = upstream/'LoopCtrlUITests'
    current = (native/'NG2Runtime.swift').read_bytes()
    baseline = subprocess.check_output(['git', 'show', BASELINE_COMMIT+
        ':patches/loopctrl/ngg2/NG2Runtime.swift'], cwd=HERE)
    if DIGEST(baseline) != BASELINE_RUNTIME_SHA256:
        raise ValueError('test092_immutable_previous_Runtime_hash')
    raw_fixture = (HERE/'ngg2_startup092_tests.swift').read_bytes()
    legacy = {name:(HERE/name).read_bytes() for name in LEGACY_FILES}
    for name, raw in legacy.items():
        if raw != subprocess.check_output(['git', 'show', BASELINE_COMMIT+':patches/loopctrl/'+name], cwd=HERE):
            raise ValueError('test092_old_fixtures_and_checkers_unchanged: '+name)
    native_output = output/'native-current'; native_output.mkdir()
    objects, native_sources = existing.test061_native_objects(native, native_output)
    reports = [run_mode(upstream, output/directory, original, raw_fixture,
                       legacy['ngg2_initial_evidence081_tests.swift'],
                       legacy['ngg2_initial_rejection091_tests.swift'], objects, native_sources,
                       baseline=is_baseline)
               for directory, original, is_baseline in (
                   ('baseline-red', baseline, True), ('production-green', current, False))]
    if (current != (native/'NG2Runtime.swift').read_bytes()
            or raw_fixture != (HERE/'ngg2_startup092_tests.swift').read_bytes()
            or any(raw != (HERE/name).read_bytes() for name, raw in legacy.items())):
        raise ValueError('test092_sources_changed_during_focused_execution')
    value = {
        'schema': 'test092-startup-contract-v1', 'status': 'pass',
        'mode': 'baseline_red_then_production_green', 'compiled': True,
        'baseline_commit': BASELINE_COMMIT, 'baseline_runtime_sha256': BASELINE_RUNTIME_SHA256,
        'current_runtime_sha256': DIGEST(current), 'fixture_file_sha256': DIGEST(raw_fixture),
        'checker_file_sha256': DIGEST(Path(__file__).read_bytes()),
        'legacy_source_sha256': {name:DIGEST(raw) for name, raw in legacy.items()},
        'native_sources': native_sources, 'results': reports,
        'new_entrypoints': list(CASES), 'related_entrypoints': list(RELATED_CASES),
        'startup_limits': {'activation_ns': 3_000_000_000, 'maximum_portraits': 64, 'wait_ns': 50_000_000},
        'deadline_policy': 'The original three second activation deadline bounds new request admission after a portrait. A normal reply already admitted before it retains the original two second capture timeout and drain contract, even if its reply/decode ends later. The deadline is never renewed.',
        'temporal_baseline_red_before_product_edit': False,
        'temporal_limitation': 'New fixture/checker frozen before Runtime product edit; Swift is absent in the authoring environment. Immutable-baseline assertion Red and current Green are executed later in this same Mac job.',
        'device_test': 'not_run',
        'scope': 'HOST procedural capture replies and clocks through real Runtime bootstrap/capture/foreground cancellation/drain. No device pixels, game launch or goods arrival acceptance is asserted.',
    }
    (output/'ngg2-test092-startup-contract.json').write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps({key:value[key] for key in ('schema','status','mode','compiled','baseline_runtime_sha256','current_runtime_sha256','fixture_file_sha256')}))


if __name__ == '__main__':
    main()
