#!/usr/bin/env python3
"""Two TEST101 Mac components; independent old Runtime/C Reds, then both Green.

Retention uses procedural read-only component snapshots and normal spool/export.
Framing declares historical ACK/HUD preconditions, then requires production C
and ordinary Runtime dispatch/classification. No original Perception/classifier
replay, full world suite, public prior-door proof, or iPhone acceptance.
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
BASELINE_CODE = 'b731edfa40a273b2a2045eba39dacbfe31cc0bfc'
BASELINE_RUNTIME_SHA = '31d82f3854a2554b6746bdc215e9ffd36902b16ee72ccac56242be3d5b5280e9'
BASELINE_CONTROLLER_SHA = 'ac437fdb9c4c200bf34e4848173c971c3e443c51ed87db8d9db6d0eeb36cbdc1'
CASES = ('coherent rejection pair and bounded normal cycle export',
         'full UNKNOWN one local observational MOVE and latest immutable classification')
RED_ASSERTIONS = {
    'retention-baseline-red': 'FAIL retention101_coherent_source_and_observed_survive_recent_eviction',
    'framing-baseline-red': 'FAIL framing101_full_unknown_mints_fresh_observational_move',
}
PROOF_SPECS = {
    'retention-baseline-red': {'runtime': 'baseline', 'controller': 'current', 'cases': ['retention'],
        'expected_assertion': 'FAIL retention101_coherent_source_and_observed_survive_recent_eviction'},
    'framing-baseline-red': {'runtime': 'current', 'controller': 'baseline', 'cases': ['framing'],
        'expected_assertion': 'FAIL framing101_full_unknown_mints_fresh_observational_move'},
    'observation-production-green': {'runtime': 'current', 'controller': 'current', 'cases': ['retention','framing'],
        'expected_assertion': None},
}
PASS = 'PASS TEST101 retention/export and full-UNKNOWN framing components; procedural/historical fixtures, real production paths'
SOURCE_FILES = ('check_runtime_observation101.py', 'ngg2_runtime_observation101_tests.swift',
                'ngg2_runtime_retention101_tests.swift', 'ngg2_runtime_framing101_fixture.c',
                'ngg2_runtime_framing101_fixture.h', 'ngg2_runtime_fakes.swift',
                'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h')
FIXTURE_CONTROLS = ('test101Retention', 'ng2_framing101_reset', 'ng2_framing101_proof',
                    'ng2_framing101_pixels', 'ng2_framing101_result', 'ng2_framing101_clock',
                    'framing101_', 'NG2Framing101Proof', 'require101', 'wait101', 'pump101',
                    'startup101', 'failure101', 'Framing101Clock', 'framing101Proof',
                    'framing101Hash', 'framing101Pixels', 'testFullFraming101')
HOST_ALIASES = ('ng2_framing101_observe_real', 'ng2_framing101_complete_real',
                'ng2_framing101_tick_real', 'ng2_analyze_rgba_production_unused', 'ng2_ring_assess_rgba_real')
HELPERS = ('NG2CycleWire.swift', 'NG2CycleSpool.swift', 'NG2CycleExport.swift')
NATIVE = ('NG2Beat.c', 'NG2Navigation.c', 'NG2Perception.c', 'NG2Ring.c',
          'NG2RingKernel/observe.c', 'NG2RingKernel/icon.c', 'NG2RingKernel/word.c')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path); parser.add_argument('output', type=Path)
    select = parser.add_mutually_exclusive_group()
    select.add_argument('--red-retention-only', action='store_true')
    select.add_argument('--red-framing-only', action='store_true')
    select.add_argument('--green-only', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin' or not shutil.which('swiftc'):
        raise SystemExit('macOS Swift unavailable; no TEST101 compiler, assertion Red, or Green executed')
    upstream = args.upstream.resolve(); native = upstream/'LoopCtrlUITests'
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    installed = {}
    for destination, entry in json.loads((HERE/'ngg2-manifest.json').read_text())['additions'].items():
        source = (ROOT/'tools/ring_native' if entry.get('source_root') == 'ring_native' else HERE/'ngg2')/entry['source']
        raw = source.read_bytes()
        if digest(raw) != entry['sha256'] or (upstream/destination).read_bytes() != raw:
            raise ValueError('exact installed sealed source differs: '+destination)
        installed[destination] = digest(raw)
    old = {}
    for filename, expected in (('NG2Runtime.swift',BASELINE_RUNTIME_SHA), ('NG2Controller.c',BASELINE_CONTROLLER_SHA)):
        raw = subprocess.check_output(['git','show',BASELINE_CODE+':patches/loopctrl/ngg2/'+filename],cwd=ROOT)
        if digest(raw) != expected: raise ValueError('frozen baseline identity: '+filename)
        old[filename] = raw; (output/('baseline-'+filename)).write_bytes(raw)
    current_runtime = (native/'NG2Runtime.swift').read_bytes(); current_c = (native/'NG2Controller.c').read_bytes()
    fixtures = {name:digest((HERE/name).read_bytes()) for name in SOURCE_FILES}
    tail = (HERE/'ngg2_runtime_retention101_tests.swift').read_bytes()
    main_source = (HERE/'ngg2_runtime_observation101_tests.swift').read_bytes()
    selected_names = (['retention-baseline-red'] if args.red_retention_only else ['framing-baseline-red']
        if args.red_framing_only else ['observation-production-green'] if args.green_only else list(PROOF_SPECS))
    commands, proofs = [], {}
    with tempfile.TemporaryDirectory(prefix='runtime-observation101-') as temporary:
        stage = Path(temporary)
        types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n')
        if len(types) != 2: raise ValueError('RPCTypes boundary')
        (stage/'RPCTypes.swift').write_text(types[0]); (stage/'main.swift').write_bytes(main_source)
        (stage/'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
            '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_runtime_framing101_fixture.h"\n')
        def compile_c(source, target, flags, extra=()):
            command = ['clang','-std=c11',*flags,*extra,'-I',str(target.parent),'-I',str(native),
                       '-I',str(HERE),'-c',str(source),'-o',str(target)]
            result = subprocess.run(command,capture_output=True,text=True,timeout=180); commands.append(command)
            (output/(target.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            if result.returncode: raise SystemExit('TEST101 C build failure is not semantic Red:\n'+result.stdout+result.stderr)
        common = []
        for index, source in enumerate([native/name for name in NATIVE]+[HERE/'ngg2_runtime_scene_fixtures.c']):
            target = stage/('common-'+str(index)+'.o')
            flags = ['-O0'] if source.name == 'NG2Beat.c' else ['-O2','-fno-fast-math','-ffp-contract=off']
            alias = ['-Dng2_analyze_rgba=ng2_analyze_rgba_production_unused'] if source.name == 'NG2Perception.c' else (
                ['-Dng2_ring_assess_rgba=ng2_ring_assess_rgba_real'] if source.name == 'NG2Ring.c' else [])
            compile_c(source,target,flags,alias); common.append(target)
        controller_objects = {}
        for mode in {PROOF_SPECS[name]['controller'] for name in selected_names}:
            directory = stage/(mode+'-controller'); directory.mkdir()
            raw = old['NG2Controller.c'] if mode == 'baseline' else current_c
            (directory/'NG2Controller.c').write_bytes(raw)
            target = directory/(mode+'-controller-host.o')
            compile_c(HERE/'ngg2_runtime_framing101_fixture.c',target,['-O0']); controller_objects[mode] = target
        for name in selected_names:
            spec = PROOF_SPECS[name]; directory = stage/name; directory.mkdir()
            runtime = old['NG2Runtime.swift'] if spec['runtime'] == 'baseline' else current_runtime
            staged_runtime = runtime+b'\n'+tail
            (directory/'NG2Runtime.swift').write_bytes(staged_runtime)
            sources = [stage/'RPCTypes.swift',native/'NG2Ticket.swift',native/'NG2Raster.swift',
                       *(native/file for file in HELPERS),HERE/'ngg2_runtime_fakes.swift',
                       directory/'NG2Runtime.swift',stage/'main.swift']
            command = ['swiftc','-Onone','-D','NG2_RUNTIME_HOST_TEST','-D','NG2_CYCLE_TEST094',
                       '-D','NG2_PREPARATION_TEST058_GREEN','-Xcc','-I'+str(native),'-Xcc','-I'+str(HERE),
                       '-import-objc-header',str(stage/'Bridge.h'),*map(str,sources),*map(str,common),
                       str(controller_objects[spec['controller']]),'-o',str(directory/'callback')]
            built = subprocess.run(command,capture_output=True,text=True,timeout=180)
            (output/(name+'-compile.txt')).write_text(built.stdout+built.stderr)
            if built.returncode: raise SystemExit('TEST101 Swift build failure is not semantic Red:\n'+built.stdout+built.stderr)
            execute = [str(directory/'callback'),','.join(spec['cases'])]
            result = subprocess.run(execute,capture_output=True,text=True,timeout=240)
            (output/(name+'-tests.txt')).write_text(result.stdout+result.stderr)
            controller = old['NG2Controller.c'] if spec['controller'] == 'baseline' else current_c
            proof = dict(returncode=result.returncode,selected_cases=spec['cases'],runtime_mode=spec['runtime'],
                controller_mode=spec['controller'],controller_sha256=digest(controller),runtime_sha256=digest(runtime),
                staged_runtime_sha256=digest(staged_runtime),fixture_sha256=digest(main_source),
                swift_command=command,execute_command=execute,expected_assertion=spec['expected_assertion'])
            (output/(name+'-result.json')).write_text(json.dumps(proof,indent=2)+'\n'); proofs[name] = proof
            if spec['expected_assertion']:
                if result.returncode != 1 or spec['expected_assertion'] not in result.stdout:
                    raise SystemExit('TEST101 named baseline assertion Red missing:\n'+result.stdout+result.stderr)
                print(spec['expected_assertion']+' (expected semantic assertion; compilation succeeded)')
            elif result.returncode or not result.stdout.strip().endswith(PASS):
                raise SystemExit('TEST101 current-source Green failed:\n'+result.stdout+result.stderr)
            else: print(result.stdout,end='')
    for destination, expected in installed.items():
        if digest((upstream/destination).read_bytes()) != expected:
            raise ValueError('installed source changed during selected components: '+destination)
    evidence = dict(schema='test101-runtime-observation-v1',scope=__doc__,cases=CASES,proof_specs=PROOF_SPECS,
        selected_proofs=selected_names,expected_red=RED_ASSERTIONS,pass_line=PASS,baseline_code=BASELINE_CODE,
        baseline_runtime_sha256=BASELINE_RUNTIME_SHA,baseline_controller_sha256=BASELINE_CONTROLLER_SHA,
        installed_source_sha256=installed,fixture_source_sha256=fixtures,fixture_controls=FIXTURE_CONTROLS,
        host_aliases=HOST_ALIASES,native_commands=commands,proofs=proofs,
        original_perception_calls=0,original_classifier_calls=0)
    (output/'runtime-observation101-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')


if __name__ == '__main__':
    main()
