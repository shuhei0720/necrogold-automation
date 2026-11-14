#!/usr/bin/env python3
"""One TEST100 Runtime partial-rebind component callback, macOS only.

Default: exact old Controller assertion Red, then current Controller Green,
with the same unchanged production Runtime. Historical walking/opening is an
explicit HOST precondition seed; procedural Scene/outcome injection is not
Perception, classifier accuracy, a public ACK reproduction, or iPhone evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE_CODE = '39851a45f5327ba5611c7c6bf57211f04eddf3e0'
BASELINE_CONTROLLER_SHA = 'b562f8d0e8f82aed46bf293f077f25e8af00ff43c3d445d3e4fc22eb5d60a192'
CASES = ('new remote ITEM/protection binds job2 and immutable latest RGBA reaches ordinary Runtime worker',)
PASS = 'PASS TEST100 one partial rebind Runtime callback; declared historical seed, procedural Scenes/RGBA/results, real workers'
RED_ASSERTION = 'FAIL partial100_latest_item_exposure_binds_job2_before_new_worker'
SOURCE_FILES = ('check_runtime_partial100.py', 'ngg2_runtime_partial100_tests.swift',
                'ngg2_runtime_partial100_fixture.c', 'ngg2_runtime_partial100_fixture.h',
                'ngg2_runtime_fakes.swift', 'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h')
FIXTURE_CONTROLS = ('ng2_partial100_reset', 'ng2_partial100_proof', 'ng2_partial100_pixels',
                    'ng2_partial100_expected_scene_hash', 'ng2_partial100_result',
                    'partial100_gate', 'partial100_proof', 'partial100_a_prefix')
HOST_ALIASES = ('ng2_partial100_observe_real', 'ng2_analyze_rgba_production_unused', 'ng2_ring_assess_rgba_real')
HELPERS = ('NG2CycleWire.swift', 'NG2CycleSpool.swift', 'NG2CycleExport.swift')
NATIVE = ('NG2Beat.c', 'NG2Navigation.c', 'NG2Perception.c', 'NG2Ring.c',
          'NG2RingKernel/observe.c', 'NG2RingKernel/icon.c', 'NG2RingKernel/word.c')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture_source():
    return (HERE/'ngg2_runtime_partial100_tests.swift').read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--red-only', action='store_true')
    mode.add_argument('--green-only', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin' or not shutil.which('swiftc'):
        raise SystemExit('macOS Swift unavailable; no TEST100 Runtime compile, semantic Red, or Green executed')
    upstream = args.upstream.resolve(); native = upstream/'LoopCtrlUITests'
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    installed = {}
    for destination, spec in json.loads((HERE/'ngg2-manifest.json').read_text())['additions'].items():
        source = (ROOT/'tools/ring_native' if spec.get('source_root') == 'ring_native' else HERE/'ngg2')/spec['source']
        raw = source.read_bytes()
        if digest(raw) != spec['sha256'] or (upstream/destination).read_bytes() != raw:
            raise ValueError('exact installed sealed source differs: '+destination)
        installed[destination] = digest(raw)
    baseline = subprocess.check_output(['git', 'show', BASELINE_CODE+':patches/loopctrl/ngg2/NG2Controller.c'], cwd=ROOT)
    if digest(baseline) != BASELINE_CONTROLLER_SHA:
        raise ValueError('frozen baseline Controller differs')
    current = (native/'NG2Controller.c').read_bytes()
    if current == baseline:
        raise ValueError('current Controller has no TEST100 rebind change')
    (output/'baseline-controller.c').write_bytes(baseline)
    fixture_identity = {name:digest((HERE/name).read_bytes()) for name in SOURCE_FILES}
    commands, proofs = [], {}
    with tempfile.TemporaryDirectory(prefix='runtime-partial100-') as temporary:
        stage = Path(temporary)
        types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n')
        if len(types) != 2:
            raise ValueError('RPCTypes boundary')
        (stage/'RPCTypes.swift').write_text(types[0])
        (stage/'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
            '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_runtime_partial100_fixture.h"\n')
        (stage/'main.swift').write_text(fixture_source())
        common = []
        def compile_c(source, target, flags, extra=()):
            command = ['clang', '-std=c11', *flags, *extra, '-I', str(target.parent), '-I', str(native),
                       '-I', str(HERE), '-c', str(source), '-o', str(target)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (output/(target.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            commands.append(command)
            if result.returncode:
                raise SystemExit('TEST100 C compile failure is not semantic Red:\n'+result.stdout+result.stderr)
        for index, source in enumerate([native/name for name in NATIVE]+[HERE/'ngg2_runtime_scene_fixtures.c']):
            target = stage/('common-'+str(index)+'.o')
            flags = ['-O0'] if source.name == 'NG2Beat.c' else ['-O2', '-fno-fast-math', '-ffp-contract=off']
            extra = []
            if source.name == 'NG2Perception.c': extra = ['-Dng2_analyze_rgba=ng2_analyze_rgba_production_unused']
            if source.name == 'NG2Ring.c': extra = ['-Dng2_ring_assess_rgba=ng2_ring_assess_rgba_real']
            compile_c(source,target,flags,extra);common.append(target)
        sources = [stage/'RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
                   *(native/name for name in HELPERS), HERE/'ngg2_runtime_fakes.swift',
                   native/'NG2Runtime.swift', stage/'main.swift']
        def execute(controller, name):
            selected = stage/name; selected.mkdir()
            (selected/'NG2Controller.c').write_bytes(controller)
            obj = selected/'selected-controller-host.o'
            compile_c(HERE/'ngg2_runtime_partial100_fixture.c',obj,['-O0'])
            command = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094',
                       '-D', 'NG2_PREPARATION_TEST058_GREEN', '-Xcc', '-I'+str(native), '-Xcc', '-I'+str(HERE),
                       '-import-objc-header', str(stage/'Bridge.h'), *map(str,sources),
                       *map(str,common), str(obj), '-o', str(selected/'callback')]
            built = subprocess.run(command,capture_output=True,text=True,timeout=180)
            (output/(name+'-compile.txt')).write_text(built.stdout+built.stderr)
            if built.returncode:
                raise SystemExit('TEST100 Swift compile failure is not semantic Red:\n'+built.stdout+built.stderr)
            result = subprocess.run([str(selected/'callback')],capture_output=True,text=True,timeout=180)
            (output/(name+'-tests.txt')).write_text(result.stdout+result.stderr)
            proof = dict(returncode=result.returncode, controller_sha256=digest(controller),
                         runtime_sha256=digest((native/'NG2Runtime.swift').read_bytes()),
                         fixture_sha256=digest(fixture_source().encode()),swift_command=command,
                         expected_assertion=RED_ASSERTION if name == 'baseline-red' else None)
            (output/(name+'-result.json')).write_text(json.dumps(proof,indent=2)+'\n');proofs[name]=proof
            return result
        if not args.green_only:
            red = execute(baseline,'baseline-red')
            if red.returncode != 1 or RED_ASSERTION not in red.stdout:
                raise SystemExit('TEST100 named old-C assertion Red missing:\n'+red.stdout+red.stderr)
            print(RED_ASSERTION+' (expected old Controller assertion; compilation succeeded)')
        if not args.red_only:
            green = execute(current,'production-green')
            if green.returncode or not green.stdout.strip().endswith(PASS):
                raise SystemExit('TEST100 current-C Runtime callback Green failed:\n'+green.stdout+green.stderr)
            print(green.stdout,end='')
    for destination, expected in installed.items():
        if digest((upstream/destination).read_bytes()) != expected:
            raise ValueError('installed source changed during callback: '+destination)
    value = dict(schema='test100-runtime-partial-v1',cases=CASES,pass_line=PASS,expected_red=RED_ASSERTION,
                 mode='red-only' if args.red_only else 'green-only' if args.green_only else 'red-and-green',
                 scope=__doc__,baseline_code=BASELINE_CODE,baseline_controller_sha256=BASELINE_CONTROLLER_SHA,
                 installed_source_sha256=installed,fixture_source_sha256=fixture_identity,
                 fixture_controls=FIXTURE_CONTROLS,host_aliases=HOST_ALIASES,
                 native_commands=commands,proofs=proofs,original_perception_calls=0)
    (output/'runtime-partial100-evidence.json').write_text(json.dumps(value,indent=2)+'\n')


if __name__ == '__main__':
    main()
