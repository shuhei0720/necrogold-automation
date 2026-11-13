#!/usr/bin/env python3
"""Selected TEST094 Runtime callback integration on macOS, no full world suite."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
HELPERS = ('NG2CycleWire.swift', 'NG2CycleSpool.swift', 'NG2CycleExport.swift')
NATIVE = ('NG2Beat.c', 'NG2Controller.c', 'NG2Navigation.c', 'NG2Perception.c', 'NG2Ring.c',
          'NG2RingKernel/observe.c', 'NG2RingKernel/icon.c', 'NG2RingKernel/word.c')


def fixture_source(selected=None):
    original = (HERE / 'ngg2_runtime_tests.swift').read_text()
    boundary = '// This public request is intentionally runnable'
    if original.count(boundary) != 1:
        raise ValueError('shared helper boundary')
    prior = (HERE / 'ngg2_dispatch_preparation_tests.swift').read_text()
    call = '\ntest058PreparedContinuousDeadlinePublic()\n'
    if prior.count(call) != 1:
        raise ValueError('old selected declaration boundary')
    fixture = (HERE / 'ngg2_cycle_runtime_tests.swift').read_text()
    cases = '// TEST094 CASE CALLS BEGIN.\n'
    if fixture.count(cases) != 1:
        raise ValueError('cycle selected mutation fixture boundary')
    prefix = original.split(boundary)[0] + prior.split(call)[0]
    if selected is not None:
        calls = {'lease': 'testCycle094WorkerCancelAndDrain(cycleRoot)\n',
                 'unknown': 'testCycle094StartedUnknownCompletion(cycleRoot)\n'}
        if selected not in calls:
            raise ValueError('cycle mutation selection')
        return prefix + fixture.split(cases)[0] + calls[selected]
    return (prefix + '\ntest058EveryPreparationIdentityField()\n'
            'test058PreparedContinuousCase("prefix")\n'
            'test058PreparedContinuousCase("cancel")\n'
            'print("PASS TEST094 selected old preparation identity/prefix/cancel callbacks")\n' + fixture)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fault-red', action='store_true')
    args = parser.parse_args()
    if not shutil.which('swiftc'):
        raise SystemExit('Swift unavailable; no Runtime094 callback or semantic Red executed')
    native = args.upstream.resolve() / 'LoopCtrlUITests'
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    for name in ('NG2Runtime.swift', 'NG2Controller.c', 'NG2Controller.h', 'NG2Ring.c', 'NG2Ring.h', *HELPERS):
        if (native / name).read_bytes() != (HERE / 'ngg2' / name).read_bytes():
            raise ValueError('patched production source differs: ' + name)
    with tempfile.TemporaryDirectory(prefix='runtime-cycle094-') as temporary:
        stage = Path(temporary)
        types = (args.upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('RPCTypes boundary')
        (stage / 'RPCTypes.swift').write_text(types[0])
        (stage / 'main.swift').write_text(fixture_source())
        (stage / 'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
            '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_cycle_runtime_fixture.h"\n'
            'void ng2_test_pause(uint8_t *, size_t);\n')
        (stage / 'pause.c').write_text('''#include "NG2Core.h"
#include "NG2Templates.h"
#include <string.h>
void ng2_test_pause(uint8_t *out,size_t length) {
    const NG2Template *templates[2]={&ng2_template_continue,&ng2_template_restart}; int x,y,index;
    if(!out||length!=896u*414u*4u)return;
    memset(out,0,length);
    for(size_t i=3;i<length;i+=4)out[i]=255;
    for(index=0;index<2;++index){const NG2Template *t=templates[index];
        for(y=0;y<t->h;++y)for(x=0;x<t->w;++x)
            if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1) {
                size_t p=((t->y+y)*896u+t->x+x)*4u;
                out[p]=out[p+1]=out[p+2]=255;
            }
    }
}
''')
        objects, commands = [], []
        sources_c = [native / name for name in NATIVE] + [HERE / 'ngg2_runtime_scene_fixtures.c',
            HERE / 'ngg2_cycle_runtime_fixture.c', stage / 'pause.c']
        for index, source in enumerate(sources_c):
            target = stage / ('native-' + str(index) + '.o')
            strict = source.name not in ('NG2Controller.c', 'NG2Beat.c')
            flags = ['-O2', '-fno-fast-math', '-ffp-contract=off'] if strict else ['-O0']
            command = ['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE),
                       '-c', str(source), '-o', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            (output / (source.stem + '-compile.txt')).write_text(result.stdout + result.stderr)
            if result.returncode:
                raise SystemExit(result.stdout + result.stderr)
            commands.append(command); objects.append(target)
        runtime = (native / 'NG2Runtime.swift').read_text()
        runtime_path = stage / 'NG2Runtime.swift'
        sources = [stage / 'RPCTypes.swift', native / 'NG2Ticket.swift', native / 'NG2Raster.swift',
            *(native / name for name in HELPERS), HERE / 'ngg2_runtime_fakes.swift', runtime_path, stage / 'main.swift']

        def execute(source, name, selected=None):
            runtime_path.write_text(source)
            (stage / 'main.swift').write_text(fixture_source(selected))
            command = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094', '-D', 'NG2_PREPARATION_TEST058_GREEN',
                '-Xcc', '-I' + str(native), '-Xcc', '-I' + str(HERE), '-import-objc-header', str(stage / 'Bridge.h'),
                *map(str, sources), *map(str, objects), '-o', str(stage / name)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (output / (name + '-compile.txt')).write_text(result.stdout + result.stderr)
            if result.returncode:
                raise SystemExit(result.stdout + result.stderr)
            result = subprocess.run([str(stage / name)], capture_output=True, text=True, timeout=180)
            (output / (name + '-tests.txt')).write_text(result.stdout + result.stderr)
            return result

        if args.fault_red:
            marker = ('                    && !(run.cycle?.workerBusy ?? false) && (run.cycle == nil || run.cycle!.terminalPersisted)')
            if runtime.count(marker) != 1:
                raise ValueError('cycle drain mutation boundary')
            red = execute(runtime.replace(marker, '', 1), 'cycle-drain-fault-red', 'lease')
            expected = 'FAIL cycle094_cancel_holds_lease_until_worker_and_main_return'
            if red.returncode != 1 or expected not in red.stdout:
                raise SystemExit('meaningful cycle drain Red missing:\n' + red.stdout + red.stderr)
            projection = '"native_inflight": .bool(run.inFlight && !drained)'
            if runtime.count(projection) != 1:
                raise ValueError('cycle UNKNOWN projection mutation boundary')
            red = execute(runtime.replace(projection, '"native_inflight": .bool(run.inFlight)', 1),
                          'cycle-unknown-projection-red', 'unknown')
            expected = 'FAIL cycle094_unknown_synth_actual_drain_projection'
            if red.returncode != 1 or expected not in red.stdout:
                raise SystemExit('meaningful UNKNOWN projection Red missing:\n' + red.stdout + red.stderr)
        green = execute(runtime, 'cycle-production-green')
        print(green.stdout, end='')
        if green.returncode:
            raise SystemExit(green.stderr or green.returncode)
        expected = 'PASS TEST094 production Runtime selected eleven cycle worker/cancel/deadline/storage/recovery/intent/two-shop/search/unknown callbacks; procedural clock/pixels/classifier'
        if not green.stdout.strip().endswith(expected):
            raise SystemExit('selected Runtime fixture inventory differs')
        (output / 'runtime-cycle094-evidence.json').write_text(json.dumps({
            'scope': 'actual production Runtime/C callbacks with procedural clock/pixels/classifier; no phone accuracy or speed acceptance',
            'native_commands': commands, 'swift_optimization': '-Onone', 'fixture_sha256': hashlib.sha256(fixture_source().encode()).hexdigest(),
            'runtime_sha256': hashlib.sha256(runtime.encode()).hexdigest(), 'mutation_red': args.fault_red,
            'old_cases': ['preparation identity', 'prefix', 'cancel'],
            'new_cases': ['worker cancel/drain', 'initial storage recovery', 'candidate one shot', 'late result', 'storage fault',
                          'intent cancel', 'two shops', 'search restart', 'search first partial', 'search first visible',
                          'started unknown completion']}, indent=2) + '\n')


if __name__ == '__main__':
    main()
