#!/usr/bin/env python3
"""Four selected TEST111 actual macOS Runtime callbacks; no full TEST110 suite."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

import check_runtime_cycle094 as base

HERE = Path(__file__).resolve().parent
GREEN_CASES = ('negative', 'retention', 'candidate', 'fresh_deadline')
EXPECTED_RED = 'FAIL test111_expired_worker_drains_before_job_change_or_ui'
IMMUTABLE_FIXTURES = (
    'ngg2_runtime_tests.swift', 'ngg2_dispatch_preparation_tests.swift',
    'ngg2_cycle_runtime_tests.swift', 'ngg2_runtime_irregular110_tests.swift',
    'ngg2_runtime110_tests.swift', 'ngg2_runtime_fakes.swift',
    'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h',
    'ngg2_cycle_runtime_fixture.c', 'ngg2_cycle_runtime_fixture.h',
    'ngg2_runtime110_fixture.c',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_source():
    # The exact legacy function bodies and assertions are reused. Only the
    # old executable entrypoint is excluded; no helper text is rewritten.
    import check_runtime110 as prior
    source = prior.fixture_source()
    boundary = '\nlet root110 = FileManager.default.temporaryDirectory'
    if source.count(boundary) != 1:
        raise ValueError('exact TEST110 executable boundary')
    return source.split(boundary)[0] + '\n' + (HERE / 'ngg2_runtime111_tests.swift').read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expect-red', action='store_true', help='Only qualify the exact fresh_deadline assertion; never product pass')
    parser.add_argument('--baseline-controller', type=Path, help='Optional old C for --expect-red; current Swift Runtime stays exact')
    args = parser.parse_args()
    if args.baseline_controller and not args.expect_red:
        parser.error('--baseline-controller requires --expect-red')
    for compiler in ('swiftc', 'clang'):
        if not shutil.which(compiler):
            raise SystemExit(compiler + ' unavailable; no TEST111 Runtime assertion executed')
    native = args.upstream.resolve() / 'LoopCtrlUITests'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = ('NG2Runtime.swift', 'NG2Ticket.swift', 'NG2Raster.swift', 'NG2Templates.h', 'NG2Controller.c', 'NG2Controller.h', 'NG2Core.h', 'NG2Ring.c',
             'NG2Ring.h', *base.HELPERS, *base.NATIVE)
    identities = {}
    for name in sorted(set(names)):
        actual = native / name
        reference = (HERE.parent.parent / 'tools/ring_native' / Path(name).name) if name.startswith('NG2RingKernel/') else (HERE / 'ngg2' / name)
        if actual.read_bytes() != reference.read_bytes():
            raise ValueError('patched production source differs: ' + name)
        identities[name] = digest(actual)
    compiler_identity = {}
    for name in ('swiftc', 'clang'):
        answer = subprocess.run([name, '--version'], capture_output=True, text=True, check=True)
        compiler_identity[name] = answer.stdout + answer.stderr
    with tempfile.TemporaryDirectory(prefix='runtime111-') as temporary:
        stage = Path(temporary)
        types = (args.upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('RPCTypes boundary')
        (stage / 'RPCTypes.swift').write_text(types[0])
        fixture = fixture_source()
        (stage / 'main.swift').write_text(fixture)
        (output / 'runtime111-selected-fixture.swift').write_text(fixture)
        (stage / 'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
            '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_cycle_runtime_fixture.h"\n'
            'void ng2_fixture_partial_unknown110(const NG2Scene *,uint64_t,uint64_t,NG2RingResult *);\n'
            'void ng2_test_pause(uint8_t *,size_t);\n'
            'int ng2_fixture_irregular110(uint8_t *,size_t,int,int,int);\n')
        perception = (native / 'NG2Perception.c').read_text()
        masks = []
        for kind, name, count in (('uint32_t', 'ng2_depleted_rows', 25), ('uint16_t', 'ng2_actor_heart_rows', 13)):
            pattern = r'static const ' + kind + r'\s+' + name + r'\[' + str(count) + r'\]\s*=\s*\{[^}]+\};'
            found = re.findall(pattern, perception, flags=re.S)
            if len(found) != 1:
                raise ValueError('exact Perception fixture mask source: ' + name)
            masks.extend(found)
        (stage / 'runtime110_masks.h').write_text('#define NG2_RUNTIME110_MASKS ' + str(int(len(masks) == 2)) + '\n' + '\n'.join(masks) + '\n')
        (stage / 'pause.c').write_text('''#include "NG2Core.h"
#include "NG2Templates.h"
#include <string.h>
void ng2_test_pause(uint8_t *out,size_t length){
 const NG2Template *templates[2]={&ng2_template_continue,&ng2_template_restart};
 if(!out||length!=896u*414u*4u)return;
 memset(out,0,length);for(size_t i=3;i<length;i+=4)out[i]=255;
 for(int n=0;n<2;++n){const NG2Template *t=templates[n];
  for(int y=0;y<t->h;++y)for(int x=0;x<t->w;++x)
   if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1){
    size_t p=((t->y+y)*896u+t->x+x)*4u;out[p]=out[p+1]=out[p+2]=255;
   }
 }
}
''')
        commands, objects = [], []
        sources_c = [(args.baseline_controller.resolve() if name == 'NG2Controller.c' and args.baseline_controller
                      else native / name) for name in base.NATIVE] + [HERE / 'ngg2_runtime_scene_fixtures.c',
            HERE / 'ngg2_cycle_runtime_fixture.c', HERE / 'ngg2_runtime110_fixture.c', stage / 'pause.c']
        for index, source in enumerate(sources_c):
            obj = stage / ('native-' + str(index) + '.o')
            flags = ['-O0'] if source.name in ('NG2Controller.c', 'NG2Beat.c') or (
                args.baseline_controller and source == args.baseline_controller.resolve()) else [
                '-O2', '-fno-fast-math', '-ffp-contract=off']
            cmd = ['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE),
                   '-I', str(stage), '-c', str(source), '-o', str(obj)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            (output / (source.stem + '-compile.txt')).write_text(result.stdout + result.stderr)
            if result.returncode:
                raise SystemExit('C compile failure is not assertion Red:\n' + result.stdout + result.stderr)
            commands.append(cmd); objects.append(obj)
        sources = [stage / 'RPCTypes.swift', native / 'NG2Ticket.swift', native / 'NG2Raster.swift',
            *(native / name for name in base.HELPERS), HERE / 'ngg2_runtime_fakes.swift',
            native / 'NG2Runtime.swift', stage / 'main.swift']
        cmd = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094',
            '-D', 'NG2_PREPARATION_TEST058_GREEN', '-Xcc', '-I' + str(native), '-Xcc', '-I' + str(HERE),
            '-import-objc-header', str(stage / 'Bridge.h'), *map(str, sources), *map(str, objects),
            '-o', str(stage / 'runtime111')]
        cmd.insert(1, 'NG2_IRREGULAR_TEST110_GREEN'); cmd.insert(1, '-D')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (output / 'runtime111-swift-compile.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('Swift compile failure is not assertion Red:\n' + result.stdout + result.stderr)
        commands.append(cmd)
        fixture_inputs = {name: digest(HERE / name) for name in IMMUTABLE_FIXTURES}
        fixture_inputs['ngg2_runtime111_tests.swift'] = digest(HERE / 'ngg2_runtime111_tests.swift')
        fixture_inputs['check_runtime111.py'] = digest(Path(__file__).resolve())
        fixture_inputs['RPCTypes.swift'] = digest(stage / 'RPCTypes.swift')
        fixture_inputs['Bridge.h'] = digest(stage / 'Bridge.h')
        fixture_inputs['pause.c'] = digest(stage / 'pause.c')
        fixture_inputs['runtime110_masks.h'] = digest(stage / 'runtime110_masks.h')
        fixture_inputs['check_runtime110.py'] = digest(HERE / 'check_runtime110.py')
        fixture_inputs['check_runtime_cycle094.py'] = digest(HERE / 'check_runtime_cycle094.py')
        compiled_sources = {str(path): digest(path) for path in [*sources_c, *sources]}
        results = {}
        cases = ('fresh_deadline',) if args.expect_red else GREEN_CASES
        for case in cases:
            try:
                result = subprocess.run([str(stage / 'runtime111'), case], capture_output=True, text=True, timeout=240)
                stdout, stderr, code = result.stdout, result.stderr, result.returncode
                timed_out = False
            except subprocess.TimeoutExpired as error:
                stdout = error.stdout or b''
                stderr = error.stderr or b''
                if isinstance(stdout, bytes): stdout = stdout.decode(errors='replace')
                if isinstance(stderr, bytes): stderr = stderr.decode(errors='replace')
                code, timed_out = None, True
            (output / ('runtime111-' + case + '.txt')).write_text(stdout + stderr)
            failures = [line for line in stdout.splitlines() if line.startswith('FAIL ')]
            markers = [line for line in stdout.splitlines() if line.startswith('PASS TEST111 CASE ')]
            qualified = (not timed_out and code == 1 and failures == [EXPECTED_RED] and not markers) if args.expect_red else (
                not timed_out and code == 0 and not failures and markers == ['PASS TEST111 CASE ' + case])
            results[case] = {'returncode': code, 'timed_out': timed_out, 'assertion_failures': failures,
                             'markers': markers, 'qualification': 'expected_assertion_red' if args.expect_red else 'green',
                             'qualified': qualified}
            print(case + ': ' + ('qualified expected assertion Red' if args.expect_red and qualified else
                                'Green' if qualified else 'FAILED qualification'), flush=True)
            if not qualified:
                print(stdout + stderr or 'Unexpected Runtime111 result', flush=True)
        # This guard has no product case marker and cannot substitute for one
        # of the four required cases.
        try:
            unknown = subprocess.run([str(stage / 'runtime111'), '__unknown111__'], capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            unknown = subprocess.CompletedProcess(['runtime111', '__unknown111__'], None, '', 'unknown-case timeout')
        (output / 'runtime111-unknown-case.txt').write_text(unknown.stdout + unknown.stderr)
        unknown_rejected = (unknown.returncode == 1 and
            [line for line in unknown.stdout.splitlines() if line.startswith('FAIL ')] ==
            ['FAIL test111_unknown_case_is_not_another_fixture'] and
            not any(line.startswith('PASS TEST111 CASE ') for line in unknown.stdout.splitlines()))
        product_pass = (not args.expect_red and tuple(results) == GREEN_CASES and
                        all(row['qualified'] for row in results.values()) and unknown_rejected)
        proof = {
            'scope': 'actual current Swift Runtime/C host callbacks; procedural pixels/clock/classifier/UI; no phone acceptance or e5bb replay',
            'required_cases': list(GREEN_CASES), 'product_pass': product_pass,
            'expected_assertion_red': args.expect_red,
            'expected_red_qualified': args.expect_red and all(row['qualified'] for row in results.values()),
            'compile_errors': 0, 'unknown_case_rejected': unknown_rejected,
            'fixture_sha256': hashlib.sha256(fixture.encode()).hexdigest(),
            'production_sources': identities, 'fixture_inputs': fixture_inputs,
            'compiled_sources': compiled_sources, 'compilers': compiler_identity,
            'commands': commands, 'cases': results,
        }
        (output / 'runtime111-result.json').write_text(json.dumps(proof, indent=2) + '\n')
        failed = [case for case, row in results.items() if not row['qualified']]
        if failed or not unknown_rejected:
            raise SystemExit('TEST111 Runtime qualification failed: ' + ', '.join(failed + ([] if unknown_rejected else ['unknown_case'])))
        print('TEST111 assertion Red captured; this is not a product pass' if args.expect_red else
              'PASS TEST111 selected current Runtime callbacks')


if __name__ == '__main__':
    main()
