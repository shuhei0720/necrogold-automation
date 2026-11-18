#!/usr/bin/env python3
"""Selected TEST114 actual Runtime callbacks with the current Controller and Ring."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

import check_runtime_cycle094 as base

HERE = Path(__file__).resolve().parent
GREEN_CASES = ('current_view', 'current_cancel')
BEFORE_CONTROLLER_SHA256 = '1df5c2df744e154e0af8be29c862bb48743d516daa97858f9575be35017d8fc3'
EXPECTED_RED_ASSERTION = 'FAIL test114_old_unknown_queues_independent_current_data_without_old_authority'
HOST_ALIASES = ('NG2RuntimeTestHooks', 'NG2RuntimeCycleTestHooks', 'NG2Fake',
    'testRestartYieldState', 'testRestartYieldPinPressure', 'testRestartYieldSaturatePins112',
    'testIrregularRetentionIDs', 'testOriginalFrameEvidence', 'ng2_fixture_upper112_rgba',
    'ng2_fixture_floor_pixels_rgba', 'ng2_fixture_cycle_search_rgba', 'ng2_fixture_cycle_result',
    'ng2_fixture_partial_unknown110', 'ng2_fixture_irregular110', 'ng2_test_pause')
SCOPE_FINALIZED = True  # Exact author-frozen callback scope; actual execution is separate.
IMMUTABLE_FIXTURES = (
    'ngg2_runtime_tests.swift', 'ngg2_dispatch_preparation_tests.swift',
    'ngg2_cycle_runtime_tests.swift', 'ngg2_runtime_irregular110_tests.swift',
    'ngg2_runtime110_tests.swift', 'ngg2_runtime_fakes.swift',
    'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h',
    'ngg2_cycle_runtime_fixture.c', 'ngg2_cycle_runtime_fixture.h',
    'ngg2_runtime110_fixture.c', 'ngg2_runtime111_tests.swift',
    'check_runtime111.py',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_source():
    # Compile every old function/assertion unchanged; replace only the old
    # executable entrypoint with the explicitly selected TEST114 cases.
    import check_runtime112 as prior
    source = prior.fixture_source()
    boundary = '\nlet root112 = FileManager.default.temporaryDirectory'
    if source.count(boundary) != 1:
        raise ValueError('exact TEST114 executable boundary')
    return source.split(boundary)[0] + '\n' + (HERE / 'ngg2_runtime114_tests.swift').read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expect-red', action='store_true')
    parser.add_argument('--before-controller', type=Path)
    args = parser.parse_args()
    if args.expect_red != (args.before_controller is not None):
        parser.error('TEST114 before-Controller assertion requires both explicit options')
    if not SCOPE_FINALIZED or not GREEN_CASES:
        raise SystemExit('TEST114 Runtime scope is pending; no fixture executed')
    for compiler in ('swiftc', 'clang'):
        if not shutil.which(compiler):
            raise SystemExit(compiler + ' unavailable; no TEST114 Runtime assertion executed')
    native = args.upstream.resolve() / 'LoopCtrlUITests'
    before_controller = args.before_controller.resolve() if args.before_controller is not None else None
    if before_controller is not None and (before_controller.is_symlink()
            or digest(before_controller) != BEFORE_CONTROLLER_SHA256):
        raise ValueError('TEST114 before-Controller differs from the pinned TEST113 C')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    headers = tuple(path.name for path in sorted((HERE / 'ngg2').glob('*.h')))
    kernel_headers = tuple('NG2RingKernel/' + name for name in ('ring.h', 'features.h', 'word_features.h', 'feature_sha.h'))
    names = ('NG2Runtime.swift', 'NG2Ticket.swift', 'NG2Raster.swift', *headers, *kernel_headers,
             *base.HELPERS, *base.NATIVE)
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
    with tempfile.TemporaryDirectory(prefix='runtime114-') as temporary:
        stage = Path(temporary)
        types = (args.upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('RPCTypes boundary')
        (stage / 'RPCTypes.swift').write_text(types[0])
        fixture = fixture_source()
        (stage / 'main.swift').write_text(fixture)
        (output / 'runtime114-selected-fixture.swift').write_text(fixture)
        (stage / 'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
            '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_cycle_runtime_fixture.h"\n'
            'int ng2_fixture_upper112_rgba(uint8_t *,size_t,int32_t,int32_t,double);\n'
            'void ng2_fixture_partial_unknown110(const NG2Scene *,uint64_t,uint64_t,NG2RingResult *);\n'
            'void ng2_test_pause(uint8_t *,size_t);\n'
            'int ng2_fixture_irregular110(uint8_t *,size_t,int,int,int);\n'
            'int ng2_fixture_current114_rgba(uint8_t *,size_t,int32_t,double);\n')
        perception = (native / 'NG2Perception.c').read_text()
        masks = []
        for kind, name, count in (('uint32_t', 'ng2_depleted_rows', 25), ('uint16_t', 'ng2_actor_heart_rows', 13)):
            pattern = r'static const ' + kind + r'\s+' + name + r'\[' + str(count) + r'\]\s*=\s*\{[^}]+\};'
            found = re.findall(pattern, perception, flags=re.S)
            if len(found) != 1:
                raise ValueError('exact Perception fixture mask source: ' + name)
            masks.extend(found)
        (stage / 'runtime110_masks.h').write_text('#define NG2_RUNTIME110_MASKS ' + str(int(len(masks) == 2)) + '\n' + '\n'.join(masks) + '\n')
        import generate_upper112_pixels as upper_pixels
        upper_generation = upper_pixels.generate(stage / 'runtime112_upper_shop.h', output / 'runtime114-upper-generation.json')
        shutil.copyfile(stage / 'runtime112_upper_shop.h', output / 'runtime112_upper_shop.h')
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
        sources_c = [native / name for name in base.NATIVE] + [HERE / 'ngg2_runtime_scene_fixtures.c',
            HERE / 'ngg2_cycle_runtime_fixture.c', HERE / 'ngg2_runtime110_fixture.c',
            HERE / 'ngg2_runtime112_upper_fixture.c', HERE / 'ngg2_runtime114_current_fixture.c', stage / 'pause.c']
        if before_controller is not None:
            sources_c = [before_controller if source == native/'NG2Controller.c' else source for source in sources_c]
        compiled_native_sha256 = {name: digest(sources_c[index]) for index, name in enumerate(base.NATIVE)}
        for index, source in enumerate(sources_c):
            obj = stage / ('native-' + str(index) + '.o')
            flags = ['-O0'] if source.name in ('NG2Controller.c', 'NG2Beat.c') or source == before_controller else [
                '-O2', '-fno-fast-math', '-ffp-contract=off']
            cmd = ['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE),
                   '-I', str(stage), '-c', str(source), '-o', str(obj)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            (output / (source.stem + '-compile.txt')).write_text(result.stdout + result.stderr)
            if result.returncode:
                raise SystemExit('C compile failure is not assertion Red:\n' + result.stdout + result.stderr)
            commands.append(cmd); objects.append(obj)
        runtime_source = native / 'NG2Runtime.swift'
        sources = [stage / 'RPCTypes.swift', native / 'NG2Ticket.swift', native / 'NG2Raster.swift',
            *(native / name for name in base.HELPERS), HERE / 'ngg2_runtime_fakes.swift',
            runtime_source, stage / 'main.swift']
        cmd = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094',
            '-D', 'NG2_PREPARATION_TEST058_GREEN', '-Xcc', '-I' + str(native), '-Xcc', '-I' + str(HERE),
            '-import-objc-header', str(stage / 'Bridge.h'), *map(str, sources), *map(str, objects),
            '-o', str(stage / 'runtime114')]
        cmd.insert(1, 'NG2_IRREGULAR_TEST110_GREEN'); cmd.insert(1, '-D')
        cmd.insert(1, 'NG2_RESTART_YIELD_TEST112_GREEN'); cmd.insert(1, '-D')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (output / 'runtime114-swift-compile.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('Swift compile failure is not assertion Red:\n' + result.stdout + result.stderr)
        commands.append(cmd)
        fixture_inputs = {name: digest(HERE / name) for name in IMMUTABLE_FIXTURES}
        fixture_inputs['ngg2_runtime114_tests.swift'] = digest(HERE / 'ngg2_runtime114_tests.swift')
        fixture_inputs['ngg2_runtime114_current_fixture.c'] = digest(HERE / 'ngg2_runtime114_current_fixture.c')
        fixture_inputs['ngg2_runtime112_tests.swift'] = digest(HERE / 'ngg2_runtime112_tests.swift')
        fixture_inputs['check_runtime112.py'] = digest(HERE / 'check_runtime112.py')
        fixture_inputs['ngg2_runtime112_upper_fixture.c'] = digest(HERE / 'ngg2_runtime112_upper_fixture.c')
        fixture_inputs['generate_upper112_pixels.py'] = digest(HERE / 'generate_upper112_pixels.py')
        fixture_inputs.update(upper_generation['source_sha256'])
        fixture_inputs['check_runtime114.py'] = digest(Path(__file__).resolve())
        fixture_inputs['RPCTypes.swift'] = digest(stage / 'RPCTypes.swift')
        fixture_inputs['Bridge.h'] = digest(stage / 'Bridge.h')
        fixture_inputs['pause.c'] = digest(stage / 'pause.c')
        fixture_inputs['runtime110_masks.h'] = digest(stage / 'runtime110_masks.h')
        fixture_inputs['runtime112_upper_shop.h'] = digest(stage / 'runtime112_upper_shop.h')
        fixture_inputs['check_runtime110.py'] = digest(HERE / 'check_runtime110.py')
        fixture_inputs['check_runtime_cycle094.py'] = digest(HERE / 'check_runtime_cycle094.py')
        compiled_sources = {str(path): digest(path) for path in [*sources_c, *sources]}
        generated_inputs = {}
        generated_root = output / 'generated-inputs'
        generated_root.mkdir(exist_ok=True)
        for name in ('RPCTypes.swift', 'Bridge.h', 'pause.c', 'runtime110_masks.h'):
            shutil.copyfile(stage / name, generated_root / name)
            generated_inputs['generated-inputs/' + name] = digest(stage / name)
        results = {}
        cases = ('current_view',) if args.expect_red else GREEN_CASES
        for case in cases:
            try:
                environment = dict(os.environ, NG2_RUNTIME112_EVIDENCE=str(output / 'synthetic-runtime-exports'), NG2_RUNTIME112_CASE=case, NG2_RUNTIME114_EVIDENCE=str(output / 'synthetic-runtime-exports'), NG2_RUNTIME114_CASE=case)
                result = subprocess.run([str(stage / 'runtime114'), case], capture_output=True, text=True, timeout=240, env=environment)
                stdout, stderr, code = result.stdout, result.stderr, result.returncode
                timed_out = False
            except subprocess.TimeoutExpired as error:
                stdout = error.stdout or b''
                stderr = error.stderr or b''
                if isinstance(stdout, bytes): stdout = stdout.decode(errors='replace')
                if isinstance(stderr, bytes): stderr = stderr.decode(errors='replace')
                code, timed_out = None, True
            (output / ('runtime114-' + case + '.txt')).write_text(stdout + stderr)
            failures = [line for line in stdout.splitlines() if line.startswith('FAIL ')]
            markers = [line for line in stdout.splitlines() if line.startswith('PASS TEST114 CASE ')]
            admissions, admission_decode_failed = [], False
            for line in stdout.splitlines():
                if line.startswith(('EVIDENCE TEST112 ADMISSION ', 'EVIDENCE TEST114 ADMISSION ')):
                    try:
                        admissions.append(json.loads(line.split(' ADMISSION ', 1)[1]))
                    except (ValueError, TypeError):
                        admission_decode_failed = True
            ages_qualified = not admission_decode_failed and bool(admissions)
            for row in admissions:
                if type(row) is not dict:
                    ages_qualified = False
                    continue
                values = [row.get(key) for key in ('capture_start_ns', 'worker_started_ns', 'deadline_ns', 'source_age_at_worker_admission_ns')]
                if (not all(type(value) is int for value in values) or not 0 <= values[3] <= 150_000_000
                        or values[3] != values[1] - values[0]
                        or not values[1] <= values[2] <= min(values[0] + 150_000_000, values[1] + 100_000_000)):
                    ages_qualified = False
            qualified = (not timed_out and ages_qualified and
                (code == 1 and failures == [EXPECTED_RED_ASSERTION] and not markers if args.expect_red else
                 code == 0 and not failures and markers == ['PASS TEST114 CASE '+case]))
            results[case] = dict(returncode=code, timed_out=timed_out, assertion_failures=failures,
                markers=markers, qualification='assertion_red' if args.expect_red else 'green', source_admissions=admissions,
                source_admission_ages_qualified=ages_qualified, qualified=qualified)
            print(case+(': expected assertion Red' if args.expect_red and qualified else ': Green' if qualified else ': FAILED qualification'), flush=True)
            if not qualified:
                print(stdout + stderr or 'Unexpected Runtime114 result', flush=True)
        # An unknown case must not execute a different successful fixture.
        unknown_rejected = False
        if not args.expect_red:
            try:
                unknown = subprocess.run([str(stage/'runtime114'), '__unknown114__'],
                    capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired:
                unknown = subprocess.CompletedProcess(['runtime114', '__unknown114__'], None, '', 'unknown-case timeout')
            (output/'runtime114-unknown-case.txt').write_text(unknown.stdout+unknown.stderr)
            unknown_rejected = (unknown.returncode == 1 and
                [line for line in unknown.stdout.splitlines() if line.startswith('FAIL ')] ==
                ['FAIL test114_unknown_case_is_not_another_fixture'] and
                not any(line.startswith('PASS TEST114 CASE ') for line in unknown.stdout.splitlines()))
        product_pass = not args.expect_red and tuple(results) == GREEN_CASES and all(row['qualified'] for row in results.values()) and unknown_rejected
        expected_red_qualified = args.expect_red and tuple(results) == ('current_view',) and all(row['qualified'] for row in results.values())
        status_snapshots = {str(path.relative_to(output)): digest(path) for path in sorted((output / 'status-snapshots').glob('status-*.json'))}
        proof = {
            'schema': 'ngg2-runtime114-host-proof-v1',
            'scope': 'actual current Swift Runtime/C callbacks and normal Ring producer; procedural pixels/clock/UI; no phone acceptance or captured-game replay',
            'required_cases': list(cases), 'product_pass': product_pass,
            'before_runtime_api_assertion_executed': False,
            'expected_assertion_red': args.expect_red, 'expected_red_qualified': expected_red_qualified,
            'before_controller_sha256': digest(before_controller) if before_controller is not None else None,
            'current_controller_sha256': identities['NG2Controller.c'],
            'compile_errors': 0, 'unknown_case_rejected': unknown_rejected,
            'fixture_sha256': hashlib.sha256(fixture.encode()).hexdigest(),
            'upper_pixel_generation': upper_generation,
            'synthetic_exports': {str(path.relative_to(output)): digest(path)
                                  for path in sorted((output / 'synthetic-runtime-exports').rglob('receipt.json'))},
            'status_snapshots': status_snapshots,
            'production_sources': identities, 'fixture_inputs': fixture_inputs,
            'compiled_native_sha256': compiled_native_sha256, 'generated_inputs': generated_inputs,
            'compiled_sources': compiled_sources, 'compilers': compiler_identity,
            'commands': commands, 'cases': results,
            'host_aliases': list(HOST_ALIASES) + ['ng2_fixture_current114_rgba'],
        }
        (output / 'runtime114-result.json').write_text(json.dumps(proof, indent=2) + '\n')
        failed = [case for case, row in results.items() if not row['qualified']]
        if failed or (not args.expect_red and not unknown_rejected):
            raise SystemExit('TEST114 Runtime qualification failed: '+', '.join(failed+([] if args.expect_red or unknown_rejected else ['unknown_case'])))
        print('PASS TEST114 pinned before-Controller assertion Red' if args.expect_red else 'PASS TEST114 selected current Runtime callbacks')


if __name__ == '__main__':
    main()
