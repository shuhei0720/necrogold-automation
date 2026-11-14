#!/usr/bin/env python3
"""Focused TEST099 Runtime diagnostic/handoff integration; macOS only.

--red-only executes frozen old Runtime with current C/getters and expects the
named missing-record assertion, never a compile/environment failure. Default
runs current Green only, so an already-passed stage1 Red need not be repeated.
--pin-diagnostic runs the corrected single pin/snapshot callback with its
persisted diagnostic values and requires its Green result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import check_runtime_cycle094 as prior
import check_runtime_target_only095 as target_prior

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE_CODE = 'bd5edaa0e2b721926775d75b1004193e5c0e0a85'
BASELINE_RUNTIME_SHA = '9c05faba2a5d0d6c030c709df75e9c144004670eb6e4d332f44cf2597812d2cc'
CASES = ['cycle-only frozen terminal diagnostic schema', 'readonly trial support before start',
         'actual deadline failure snapshot and no handoff', 'readonly diagnostic live anchor and snapshot retention',
         'actual four-negative limit and publish-ACK-before-next-start', 'actual clear-search limit handoff']
RELATED_CASES = ['legacy20 critical pin/export retention']
RED_ASSERTION = 'FAIL cycle099_terminal_has_frozen_stop_and_handoff'
PIN_ASSERTION = 'FAIL cycle099_writer_owns_old_immutable_snapshot_not_later_getter'
PIN_PASS = 'PASS TEST099 readonly POD live anchor and first failure survive recent eviction'
PASS = 'PASS TEST099 six cycle diagnostic/handoff callbacks and legacy20 evidence retention; procedural clock/pixels/results'
HOST_GETTER_ALIAS = 'ng2_controller_stop_detail_real'
FIXTURE_CONTROLS = ('ng2_fixture099_stop_override', 'fixture099_override_enabled', 'fixture099_override', 'fixture099_gate')
SOURCE_FILES = ('check_runtime099.py', 'ngg2_runtime099_fixture.c', 'ngg2_runtime099_fixture.h',
                'ngg2_runtime099_tests.swift', 'check_runtime_cycle094.py', 'check_runtime_target_only095.py',
                'ngg2_cycle_runtime_tests.swift', 'ngg2_target_only_runtime_tests.swift',
                'ngg2_runtime_tests.swift', 'ngg2_dispatch_preparation_tests.swift', 'ngg2_runtime_fakes.swift',
                'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h',
                'ngg2_cycle_runtime_fixture.c', 'ngg2_cycle_runtime_fixture.h')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture_source(selected=None):
    if selected not in (None, 'projection', 'pin-snapshot'):
        raise ValueError('TEST099 fixture selection')
    inherited = target_prior.fixture_source()
    boundary = '// TEST095 ENTRYPOINTS BEGIN.\n'
    if inherited.count(boundary) != 1:
        raise ValueError('TEST095 declaration boundary')
    old = (HERE/'ngg2_runtime_tests.swift').read_text()
    export_begin, export_end = 'func pagedCall(', 'func testContinuousRevalidationCallbacksPublic()'
    if old.count(export_begin) != 1 or old.count(export_end) != 1:
        raise ValueError('old export helper boundaries')
    export_helpers = export_begin + old.split(export_begin)[1].split(export_end)[0]
    evidence_begin, evidence_end = '// TEST056 PUBLIC FIXTURES BEGIN.\n', '// TEST056 PUBLIC FIXTURES END.'
    if old.count(evidence_begin) != 1 or old.count(evidence_end) != 1:
        raise ValueError('old legacy20 evidence boundary')
    evidence_helpers = old.split(evidence_begin)[1].split(evidence_end)[0]
    own = (HERE/'ngg2_runtime099_tests.swift').read_text()
    calls = '// TEST099 CASE CALLS BEGIN.\n'
    if own.count(calls) != 1:
        raise ValueError('TEST099 selected calls boundary')
    if selected == 'projection':
        own = own.split(calls)[0] + 'testCycle099TerminalProjection(cycle099Root)\n'
    elif selected == 'pin-snapshot':
        own = own.split(calls)[0] + 'testCycle099PinAndSnapshot(cycle099Root)\n'
    return inherited.split(boundary)[0] + export_helpers + evidence_helpers + own


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--red-only', action='store_true')
    selection.add_argument('--fault-red', action='store_true')
    selection.add_argument('--pin-diagnostic', action='store_true',
        help='current-source pin/snapshot case only, recording persisted values and requiring Green')
    args = parser.parse_args()
    if not shutil.which('swiftc'):
        raise SystemExit('Swift unavailable; no TEST099 semantic Red or Runtime Green executed')
    upstream = args.upstream.resolve(); native = upstream/'LoopCtrlUITests'
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    installed = {}
    manifest = json.loads((HERE/'ngg2-manifest.json').read_text())
    for destination, entry in manifest['additions'].items():
        source_dir = ROOT/'tools/ring_native' if entry.get('source_root') == 'ring_native' else HERE/'ngg2'
        source, target = source_dir/entry['source'], upstream/destination
        raw = source.read_bytes()
        if digest(raw) != entry['sha256'] or target.read_bytes() != raw:
            raise ValueError('exact sealed source differs: '+destination)
        installed[destination] = digest(raw)
    baseline = subprocess.check_output(['git', 'show', BASELINE_CODE+':patches/loopctrl/ngg2/NG2Runtime.swift'], cwd=ROOT)
    if digest(baseline) != BASELINE_RUNTIME_SHA:
        raise ValueError('frozen old TEST099 Runtime source differs')
    (output/'baseline-runtime.swift').write_bytes(baseline)
    fixture_identity = {name:digest((HERE/name).read_bytes()) for name in SOURCE_FILES}
    with tempfile.TemporaryDirectory(prefix='runtime099-') as temporary:
        stage = Path(temporary)
        types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('RPCTypes declaration boundary')
        (stage/'RPCTypes.swift').write_text(types[0])
        (stage/'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
            '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_cycle_runtime_fixture.h"\n'
            '#include "ngg2_runtime099_fixture.h"\nvoid ng2_test_pause(uint8_t *,size_t);\n')
        (stage/'pause.c').write_text(target_prior.pause_source())
        objects, commands = [], []
        c_sources = [native/name for name in prior.NATIVE] + [HERE/'ngg2_runtime_scene_fixtures.c',
            HERE/'ngg2_cycle_runtime_fixture.c', HERE/'ngg2_runtime099_fixture.c', stage/'pause.c']
        for index, source in enumerate(c_sources):
            target = stage/('native-'+str(index)+'.o')
            flags = ['-O0'] if source.name in ('NG2Controller.c', 'NG2Beat.c') else ['-O2', '-fno-fast-math', '-ffp-contract=off']
            if source.name == 'NG2Controller.c':
                flags += ['-Dng2_controller_stop_detail='+HOST_GETTER_ALIAS]
            command = ['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE), '-c', str(source), '-o', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            (output/(source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            if result.returncode:
                raise SystemExit('TEST099 compile failure is not semantic Red:\n'+result.stdout+result.stderr)
            commands.append(command); objects.append(target)
        runtime_path = stage/'NG2Runtime.swift'
        sources = [stage/'RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
                   *(native/name for name in prior.HELPERS), HERE/'ngg2_runtime_fakes.swift', runtime_path, stage/'main.swift']
        proofs = {}
        def execute(raw, name, selected=None):
            fixture = fixture_source(selected)
            runtime_path.write_bytes(raw); (stage/'main.swift').write_text(fixture)
            (output/(name+'-fixture.swift')).write_text(fixture)
            command = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094', '-D', 'NG2_PREPARATION_TEST058_GREEN',
                       '-Xcc', '-I'+str(native), '-Xcc', '-I'+str(HERE), '-import-objc-header', str(stage/'Bridge.h'),
                       *map(str, sources), *map(str, objects), '-o', str(stage/name)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (output/(name+'-compile.txt')).write_text(result.stdout+result.stderr)
            if result.returncode:
                raise SystemExit('TEST099 compile failure is not semantic Red:\n'+result.stdout+result.stderr)
            result = subprocess.run([str(stage/name)], capture_output=True, text=True, timeout=180)
            (output/(name+'-tests.txt')).write_text(result.stdout+result.stderr)
            proof = dict(returncode=result.returncode, selected=selected, fixture_sha256=digest(fixture.encode()),
                runtime_sha256=digest(raw), swift_command=command,
                expected_assertion=RED_ASSERTION if selected == 'projection' else None)
            (output/(name+'-result.json')).write_text(json.dumps(proof, indent=2)+'\n'); proofs[name] = proof
            return result
        if args.red_only or args.fault_red:
            red = execute(baseline, 'runtime099-baseline-red', 'projection')
            if red.returncode != 1 or RED_ASSERTION not in red.stdout:
                raise SystemExit('TEST099 named baseline assertion Red missing (returncode='+str(red.returncode)+'):\n'+red.stdout+red.stderr)
            print(RED_ASSERTION+' (expected old Runtime assertion; not a build failure)')
        if args.pin_diagnostic:
            diagnostic = execute((native/'NG2Runtime.swift').read_bytes(), 'runtime099-pin-diagnostic', 'pin-snapshot')
            if diagnostic.returncode or not diagnostic.stdout.strip().endswith(PIN_PASS) or 'DIAGNOSTIC cycle099_pin_snapshot ' not in diagnostic.stdout:
                raise SystemExit('TEST099 corrected pin diagnostic Green missing (returncode='+str(diagnostic.returncode)+'):\n'+
                    diagnostic.stdout+diagnostic.stderr)
            print(diagnostic.stdout, end='')
        elif not args.red_only:
            green = execute((native/'NG2Runtime.swift').read_bytes(), 'runtime099-production-green')
            if green.returncode or not green.stdout.strip().endswith(PASS):
                failed = [line for line in green.stdout.splitlines() if line.startswith('FAIL ')]
                raise SystemExit('TEST099 Runtime Green failed (returncode='+str(green.returncode)+'):\n'+
                    '\n'.join(failed[-1:])+'\n'+green.stderr)
            print(green.stdout, end='')
        for destination, expected in installed.items():
            if digest((upstream/destination).read_bytes()) != expected:
                raise ValueError('installed source changed during selected callbacks: '+destination)
        value = dict(schema='test099-runtime-evidence-v1',
            scope='actual Runtime/C callbacks with procedural pixels/clock/classifier; readonly getter POD override only for pin/snapshot case, no game/iPhone acceptance',
            mode='pin-diagnostic' if args.pin_diagnostic else 'red-only' if args.red_only else 'red-and-green' if args.fault_red else 'green-only',
            new_cases=CASES, old_cases=RELATED_CASES, expected_red=RED_ASSERTION, pass_line=PASS,
            baseline_code=BASELINE_CODE, baseline_runtime_sha256=BASELINE_RUNTIME_SHA,
            installed_source_sha256=installed, fixture_source_sha256=fixture_identity,
            fixture_sha256=digest(fixture_source().encode()),
            host_getter_alias=HOST_GETTER_ALIAS, fixture_controls=FIXTURE_CONTROLS,
            readonly_getter_override_case='testCycle099PinAndSnapshot', native_commands=commands, proofs=proofs)
        (output/'runtime099-evidence.json').write_text(json.dumps(value, indent=2)+'\n')


if __name__ == '__main__':
    main()
