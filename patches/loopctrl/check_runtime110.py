#!/usr/bin/env python3
"""Selected TEST110 actual Runtime callbacks; assertion Red is distinct from Green."""
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
GREEN_CASES = ('profile', 'retention', 'candidate', 'prefix', 'negative', 'death_lifecycle', 'death_partial_floor', 'death_later_goods', 'death_third_menu', 'death_unknown_menu', 'death_unknown_continue', 'death_pin24', 'death_cancel_pin24', 'death_cancel_continue', 'death_cancel_restart', 'death_owner_checkpoint', 'death_late_checkpoint', 'death_storage_checkpoint', 'death_recovery_lifecycle', 'death_decode_park', 'death_outcome_storage', 'invalid_companion', 'prompt_only', 'pending_candidate', 'pending_invalid', 'pending_unknown', 'pending_negative', 'enemy_retention', 'recovery_unknown_profile')


EXPECTED = {
    'profile': 'FAIL test110_new_profile_prepare_accepted_with_own_closed_envelope',
    'retention': 'FAIL test110_queue_first_source_transferred_to_actual_worker',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_source():
    original = (HERE / 'ngg2_runtime_tests.swift').read_text()
    prior = (HERE / 'ngg2_dispatch_preparation_tests.swift').read_text()
    cycle = (HERE / 'ngg2_cycle_runtime_tests.swift').read_text()
    boundaries = ('// This public request is intentionally runnable',
                  '\ntest058PreparedContinuousDeadlinePublic()\n', '// TEST094 ENTRYPOINTS BEGIN.')
    for value, boundary in zip((original, prior, cycle), boundaries):
        if value.count(boundary) != 1:
            raise ValueError('shared fixture boundary: ' + boundary)
    return (original.split(boundaries[0])[0] + prior.split(boundaries[1])[0] +
            cycle.split(boundaries[2])[0] + (HERE / 'ngg2_runtime_irregular110_tests.swift').read_text() +
            (HERE / 'ngg2_runtime110_tests.swift').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expect-red', action='store_true')
    args = parser.parse_args()
    for compiler in ('swiftc', 'clang'):
        if not shutil.which(compiler):
            raise SystemExit(compiler + ' unavailable; no TEST110 Runtime assertion executed')
    native = args.upstream.resolve() / 'LoopCtrlUITests'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = ('NG2Runtime.swift', 'NG2Controller.c', 'NG2Controller.h', 'NG2Core.h', 'NG2Ring.c',
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
    with tempfile.TemporaryDirectory(prefix='runtime110-') as temporary:
        stage = Path(temporary)
        types = (args.upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('RPCTypes boundary')
        (stage / 'RPCTypes.swift').write_text(types[0])
        fixture = fixture_source()
        (stage / 'main.swift').write_text(fixture)
        (output / 'runtime110-selected-fixture.swift').write_text(fixture)
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
            if len(found) != 1 and not args.expect_red:
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
        sources_c = [native / name for name in base.NATIVE] + [HERE / 'ngg2_runtime_scene_fixtures.c',
            HERE / 'ngg2_cycle_runtime_fixture.c', HERE / 'ngg2_runtime110_fixture.c', stage / 'pause.c']
        for index, source in enumerate(sources_c):
            obj = stage / ('native-' + str(index) + '.o')
            flags = ['-O0'] if source.name in ('NG2Controller.c', 'NG2Beat.c') else [
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
            '-o', str(stage / 'runtime110')]
        if not args.expect_red:
            cmd.insert(1, 'NG2_IRREGULAR_TEST110_GREEN'); cmd.insert(1, '-D')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (output / 'runtime110-swift-compile.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('Swift compile failure is not assertion Red:\n' + result.stdout + result.stderr)
        commands.append(cmd)
        results = {}
        cases = ('profile', 'retention') if args.expect_red else GREEN_CASES
        for case in cases:
            result = subprocess.run([str(stage / 'runtime110'), case], capture_output=True, text=True, timeout=180)
            (output / ('runtime110-' + case + '.txt')).write_text(result.stdout + result.stderr)
            failures = [line for line in result.stdout.splitlines() if line.startswith('FAIL ')]
            markers = [line for line in result.stdout.splitlines() if line.startswith('PASS TEST110 CASE ')]
            qualified = (result.returncode == 1 and failures == [EXPECTED[case]]) if args.expect_red else (
                result.returncode == 0 and not failures and markers == ['PASS TEST110 CASE ' + case])
            results[case] = {'returncode': result.returncode, 'assertion_failures': failures,
                             'qualification': 'expected_assertion_red' if args.expect_red else 'green',
                             'qualified': qualified}
            (output / 'runtime110-result.json').write_text(json.dumps({
                'scope': 'actual current Runtime/C host callbacks; procedural pixels/clock/classifier; no phone acceptance',
                'product_pass': not args.expect_red and len(results) == len(cases) and all(x['qualified'] for x in results.values()),
                'expected_assertion_red': args.expect_red, 'compile_errors': 0,
                'fixture_sha256': hashlib.sha256(fixture.encode()).hexdigest(),
                'production_sources': identities, 'compilers': compiler_identity,
                'commands': commands, 'cases': results}, indent=2) + '\n')
            print(case + ': ' + ('qualified expected assertion Red' if args.expect_red and qualified else
                                'Green' if qualified else 'FAILED qualification'))
            if not qualified:
                raise SystemExit(result.stdout + result.stderr or 'Unexpected Runtime110 result')
        print('TEST110 assertion Red captured; this is not a product pass' if args.expect_red else
              'PASS TEST110 selected current Runtime callbacks')


if __name__ == '__main__':
    main()
