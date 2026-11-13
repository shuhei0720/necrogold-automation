#!/usr/bin/env python3
"""Focused TEST096 bounded PAUSE/adoption callbacks; macOS execution only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import check_runtime_target_only095 as ring_prior
import check_runtime_cycle094 as prior

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE_CODE = 'c071f41d4a38b4b513d342ea3f3c68f5db8ec067'
BASELINE_RUNTIME_SHA = 'a4a0f54182cb70850a5bd22cb6a5c60763b024acbd49567ad0734155cc424bd0'
CASES = ['on-time candidate and synchronous 275ms pause', 'on-time negative and synchronous 275ms pause',
         'hung worker original deadline', 'durable intent cancellation independent of pause ordering']
RELATED_CASES = ['old worker cancellation and actual drain', 'old target-only wire',
                 'old target-only negative restart', 'old visible candidate', 'old partial candidate',
                 'old preparation identities', 'old prepared prefix', 'old prepared cancellation']
PASS = ('PASS TEST096 bounded PAUSE ordering four new cases, worker cancellation, four target-only and three legacy callbacks; '
        'procedural clock/pixels/classifier')
RED_ASSERTION = 'FAIL cycle096_pause_does_not_expire_completed_worker'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def fixture_source(selected=None):
    prefix = ring_prior.fixture_source()
    boundary = '// TEST095 ENTRYPOINTS BEGIN.\n'
    if prefix.count(boundary) != 1:
        raise ValueError('target-only helper boundary')
    own = (HERE/'ngg2_pause_adoption096_tests.swift').read_text()
    calls = '// TEST096 CASE CALLS BEGIN.\n'
    if own.count(calls) != 1:
        raise ValueError('pause096 fixture boundary')
    if selected is not None:
        if selected != 'slow':
            raise ValueError('pause096 Red case')
        own = own.split(calls)[0] + 'testCycle096SlowPause(cycle096Root, negative: false)\n'
    return prefix.split(boundary)[0] + own


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fault-red', action='store_true')
    args = parser.parse_args()
    if not shutil.which('swiftc'):
        raise SystemExit('Swift unavailable; no TEST096 callback or semantic Red executed')
    native = args.upstream.resolve()/'LoopCtrlUITests'
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE/'ngg2-manifest.json').read_text())
    installed = {}
    for destination, entry in manifest['additions'].items():
        source_dir = ROOT/'tools/ring_native' if entry.get('source_root') == 'ring_native' else HERE/'ngg2'
        source = source_dir/entry['source']; target = args.upstream.resolve()/destination
        raw = source.read_bytes()
        if digest(raw) != entry['sha256'] or target.read_bytes() != raw:
            raise ValueError('exact sealed source differs: '+destination)
        installed[destination] = digest(raw)
    baseline = subprocess.check_output(['git', 'show', BASELINE_CODE+':patches/loopctrl/ngg2/NG2Runtime.swift'], cwd=ROOT).decode()
    if digest(baseline.encode()) != BASELINE_RUNTIME_SHA:
        raise ValueError('baseline Runtime source identity')
    (output/'baseline-runtime.swift').write_text(baseline)
    with tempfile.TemporaryDirectory(prefix='runtime-pause096-') as temporary:
        stage = Path(temporary)
        (stage/'RPCTypes.swift').write_text((args.upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)[0])
        (stage/'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_cycle_runtime_fixture.h"\nvoid ng2_test_pause(uint8_t *,size_t);\n')
        (stage/'pause.c').write_text(ring_prior.pause_source())
        objects, commands, native_objects = [], [], {}
        for index, source in enumerate([native/name for name in prior.NATIVE] +
                                      [HERE/'ngg2_runtime_scene_fixtures.c', HERE/'ngg2_cycle_runtime_fixture.c', stage/'pause.c']):
            target = stage/('native-'+str(index)+'.o')
            flags = ['-O0'] if source.name in ('NG2Controller.c', 'NG2Beat.c') else ['-O2', '-fno-fast-math', '-ffp-contract=off']
            command = ['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE), '-c', str(source), '-o', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            (output/(source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            if result.returncode:
                raise SystemExit(result.stdout+result.stderr)
            objects.append(target); commands.append(command); native_objects[source.name] = target
        library = stage/'ring-direct.dylib'
        direct_command = ['clang', '-dynamiclib', *[str(native_objects[name]) for name in
                          ('NG2Perception.c', 'NG2Ring.c', 'observe.c', 'icon.c', 'word.c')], '-o', str(library)]
        subprocess.run(direct_command, check=True)
        ring_prior.direct_classifier(library, output)
        runtime, wire = (native/'NG2Runtime.swift').read_text(), (native/'NG2CycleWire.swift').read_text()
        sources = [stage/'RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
                   native/'NG2CycleWire.swift', native/'NG2CycleSpool.swift', native/'NG2CycleExport.swift',
                   HERE/'ngg2_runtime_fakes.swift', stage/'NG2Runtime.swift', stage/'main.swift']
        proofs = {}
        def execute(runtime_source, name, selected=None):
            fixture = fixture_source(selected)
            for path, content in ((stage/'NG2Runtime.swift', runtime_source), (stage/'main.swift', fixture),
                                  (output/(name+'-fixture.swift'), fixture)):
                path.write_text(content)
            command = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094', '-D', 'NG2_PREPARATION_TEST058_GREEN',
                       '-Xcc', '-I'+str(native), '-Xcc', '-I'+str(HERE), '-import-objc-header', str(stage/'Bridge.h'),
                       *map(str, sources), *map(str, objects), '-o', str(stage/name)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (output/(name+'-compile.txt')).write_text(result.stdout+result.stderr)
            if result.returncode:
                raise SystemExit(result.stdout+result.stderr)
            result = subprocess.run([str(stage/name)], capture_output=True, text=True, timeout=180)
            (output/(name+'-tests.txt')).write_text(result.stdout+result.stderr)
            proof = dict(returncode=result.returncode, selected=selected, fixture_sha256=digest(fixture.encode()),
                         runtime_sha256=digest(runtime_source.encode()), wire_sha256=digest(wire.encode()),
                         stdout_bytes=len(result.stdout.encode()), stderr_bytes=len(result.stderr.encode()), swift_command=command,
                         expected_assertion=RED_ASSERTION if selected else None)
            (output/(name+'-result.json')).write_text(json.dumps(proof, indent=2)+'\n'); proofs[name] = proof
            return result
        if args.fault_red:
            red = execute(baseline, 'pause-baseline-red', 'slow')
            if red.returncode != 1 or RED_ASSERTION not in red.stdout:
                raise SystemExit('meaningful baseline TEST096 Runtime Red missing (returncode='+str(red.returncode)+'):\n'+red.stdout+red.stderr)
        green = execute(runtime, 'pause-production-green')
        print(green.stdout, end='')
        if green.returncode or not green.stdout.strip().endswith(PASS):
            raise SystemExit(green.stderr or 'TEST096 Runtime Green failed (returncode='+str(green.returncode)+')')
        for destination, entry in manifest['additions'].items():
            if digest((args.upstream.resolve()/destination).read_bytes()) != installed[destination]:
                raise ValueError('installed source changed during callbacks: '+destination)
        (output/'runtime-pause096-evidence.json').write_text(json.dumps(dict(
            scope='actual Runtime bounded pre-PAUSE adoption with synchronous 275ms tap; procedural clock/pixels and injected lifecycle results, no game/phone acceptance',
            new_cases=CASES, old_cases=RELATED_CASES,
            superseded_old_case='testCycle094TwoShopsAndIntentCancel(cancelIntent:true) waits for PAUSE before releasing classifier; replaced by independent-release intent cancellation with all authority/recovery assertions retained',
            mutation_red=args.fault_red, expected_red=RED_ASSERTION, pass_line=PASS,
            baseline_code=BASELINE_CODE, baseline_runtime_sha256=BASELINE_RUNTIME_SHA,
            runtime_sha256=digest(runtime.encode()), wire_sha256=digest(wire.encode()), fixture_sha256=digest(fixture_source().encode()),
            installed_source_sha256=installed, native_commands=commands, direct_command=direct_command, proofs=proofs), indent=2)+'\n')


if __name__ == '__main__':
    main()
