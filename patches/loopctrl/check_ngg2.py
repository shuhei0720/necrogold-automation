"""Compile production NG-G2 helpers and require executable behavior evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
EXPECTED_RED = 'FAIL cancelled_ticket_not_sent'
# The original permits() stub was successfully compiled and produced this
# assertion Red in Actions run42332613748 / commit9995371259135f33919df7ef50d538c46d7f985d.
# Later helper signatures are inert compatibility stubs so that the expanded
# same test executable can reproduce the original first assertion.
BASELINE = '''import Foundation
enum NG2TicketGuard {
    static func permits(expectedGeneration: UInt64, currentGeneration: UInt64,
                        cancelled: Bool, ownerActive: Bool, foreground: Bool,
                        locked: Bool, now: UInt64, notBefore: UInt64,
                        deadline: UInt64) -> Bool { return true }
    static func canReleaseLease(captureWorkerDone: Bool, captureOutstanding: Bool,
                                mainOutstanding: Bool, legacyCaptures: Int) -> Bool { return false }
    static func renewsHeartbeat(keepalive: Bool = false, ownerActive: Bool, cancelled: Bool) -> Bool { return false }
}
'''


def execute(source, destination, label):
    destination.mkdir(parents=True, exist_ok=True)
    staged = destination / label
    staged.mkdir(exist_ok=True)
    (staged / 'NG2Ticket.swift').write_text(source)
    shutil.copyfile(HERE / 'ngg2_ticket_tests.swift', staged / 'main.swift')
    executable = staged / 'ticket-tests'
    built = subprocess.run(['swiftc', str(staged / 'NG2Ticket.swift'),
        str(staged / 'main.swift'), '-o', str(executable)],
        capture_output=True, text=True, timeout=120)
    (destination / (label + '-compile.txt')).write_text(built.stdout + built.stderr)
    built.check_returncode()
    result = subprocess.run([str(executable.resolve())], capture_output=True,
                            text=True, timeout=30)
    (destination / (label + '-tests.txt')).write_text(result.stdout + result.stderr)
    return result


def require_red(result, expected=EXPECTED_RED):
    if result.returncode != 1 or result.stdout.strip().splitlines()[-1] != expected or result.stderr:
        raise RuntimeError('compiled_behavioral_red_not_observed')


def compile_run(sources, executable, output, label, extra=()):
    built = subprocess.run(['swiftc', *map(str, sources), *map(str, extra), '-o', str(executable)],
                           capture_output=True, text=True, timeout=180)
    (output / (label + '-compile.txt')).write_text(built.stdout + built.stderr)
    built.check_returncode()
    result = subprocess.run([str(executable.resolve())], capture_output=True, text=True, timeout=60)
    (output / (label + '-tests.txt')).write_text(result.stdout + result.stderr)
    return result


def api_contract(upstream, output):
    stage = output / 'api'; stage.mkdir(exist_ok=True)
    server = (upstream / 'LoopCtrlKit/JSONRPCServer.swift').read_text()
    begin = '// NG-G2 BEGIN authenticated owner projection (tested verbatim).'
    end = '// NG-G2 END authenticated owner projection.'
    if server.count(begin) != 1 or server.count(end) != 1:
        raise ValueError('owner_projection_boundary')
    helper = server[server.index(begin):server.index(end)+len(end)]
    types = (upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
    if len(types) != 2: raise ValueError('rpc_types_boundary')
    (stage / 'RPCTypes.swift').write_text(types[0])
    (stage / 'NG2AuthenticatedOwner.swift').write_text('import Foundation\n'+helper+'\n')
    shutil.copyfile(HERE / 'ngg2_api_tests.swift', stage / 'main.swift')
    sources = [stage / 'RPCTypes.swift', stage / 'NG2AuthenticatedOwner.swift', stage / 'main.swift']
    green = compile_run(sources, stage / 'api-tests', output, 'api-production-green')
    green.check_returncode()
    if not green.stdout.startswith('PASS 16 production authenticated owner projection contracts;') or green.stderr:
        raise RuntimeError('api_production_contract_missing')
    old = 'native["_necro_owner"] = .string(owner)'
    if helper.count(old) != 1: raise ValueError('api_mutation_target')
    (stage / 'NG2AuthenticatedOwner.swift').write_text('import Foundation\n'+helper.replace(old, '// owner projection removed')+'\n')
    red = compile_run(sources, stage / 'api-mutated-tests', output, 'api-mutation-red')
    if red.returncode != 1 or 'FAIL authenticated_owner_' not in red.stdout or red.stderr:
        raise RuntimeError('api_mutation_red_missing')
    return {'production_green': green.stdout.strip(), 'mutation_red': red.stdout.strip(), 'compiled': True}


def raster_contract(upstream, output):
    stage = output / 'raster'; stage.mkdir(exist_ok=True)
    native = upstream / 'LoopCtrlUITests'
    objects = []
    for source in sorted(native.glob('NG2*.c')):
        target = stage / (source.stem + '.o')
        result = subprocess.run(['clang', '-std=c11', '-O2', '-I', str(native), '-c', str(source), '-o', str(target)],
                                capture_output=True, text=True, timeout=120)
        (output / (source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
        result.check_returncode(); objects.append(target)
    if len(objects) != 4: raise ValueError('native_C_source_set')
    source = (native / 'NG2Raster.swift').read_text()
    (stage / 'NG2Raster.swift').write_text(source)
    shutil.copyfile(HERE / 'ngg2_raster_tests.swift', stage / 'main.swift')
    sources = [stage / 'NG2Raster.swift', stage / 'main.swift']
    extra = ['-import-objc-header', native / 'NG2Core.h', *objects]
    green = compile_run(sources, stage / 'raster-tests', output, 'raster-production-green', extra)
    green.check_returncode()
    if not green.stdout.startswith('PASS production CoreGraphics') or green.stderr:
        raise RuntimeError('raster_production_contract_missing')
    old = 'case 6: p = (y, image.height-1-x)'
    if source.count(old) != 1: raise ValueError('raster_mutation_target')
    (stage / 'NG2Raster.swift').write_text(source.replace(old, 'case 6: p = (y, x)'))
    red = compile_run(sources, stage / 'raster-mutated-tests', output, 'raster-mutation-red', extra)
    require_red(red, 'FAIL orientation_6_asymmetric_pixels')
    return {'production_green': green.stdout.strip(), 'mutation_red': red.stdout.strip(), 'compiled': True}


def runtime_contract(upstream, output):
    stage = output / 'runtime'; stage.mkdir(exist_ok=True)
    native = upstream / 'LoopCtrlUITests'
    (stage / 'NG2RuntimeFixture.h').write_text('#include "NG2Core.h"\nvoid ng2_test_pause(uint8_t *, size_t);\n')
    (stage / 'fixture.c').write_text('''#include "NG2Core.h"
#include "NG2Templates.h"
#include <string.h>
void ng2_test_pause(uint8_t *out,size_t length) {
    const NG2Template *t=&ng2_template_continue; int x,y;
    if(!out||length!=896u*414u*4u)return;
    memset(out,0,length);
    for(size_t i=3;i<length;i+=4)out[i]=255;
    for(y=0;y<t->h;++y)for(x=0;x<t->w;++x)
        if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1) {
            size_t p=((t->y+y)*896u+t->x+x)*4u;
            out[p]=out[p+1]=out[p+2]=255;
        }
}
''')
    built = subprocess.run(['clang', '-std=c11', '-O2', '-I', str(native), '-c', str(stage/'fixture.c'),
                            '-o', str(stage/'fixture.o')], capture_output=True, text=True, timeout=60)
    (output/'runtime-fixture-compile.txt').write_text(built.stdout+built.stderr); built.check_returncode()
    shutil.copyfile(HERE/'ngg2_runtime_fakes.swift', stage/'Fakes.swift')
    shutil.copyfile(HERE/'ngg2_runtime_tests.swift', stage/'main.swift')
    source = (native/'NG2Runtime.swift').read_text()
    (stage/'NG2Runtime.swift').write_text(source)
    sources = [output/'api/RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
               stage/'Fakes.swift', stage/'NG2Runtime.swift', stage/'main.swift']
    objects = sorted((output/'raster').glob('NG2*.o'))+[stage/'fixture.o']
    extra = ['-D', 'NG2_RUNTIME_HOST_TEST', '-Xcc', '-I'+str(native), '-import-objc-header', stage/'NG2RuntimeFixture.h', *objects]
    green = compile_run(sources, stage/'runtime-tests', output, 'runtime-production-green', extra)
    green.check_returncode()
    if not green.stdout.startswith('PASS production Runtime public API/') or green.stderr:
        raise RuntimeError('runtime_production_contract_missing')
    mutations = {
        'capture-admission': ('guard !run.stopped, run.cancelReason == 0, self.ownerActive(run) else { return nil }',
                              '// mutation: capture admission recheck removed',
                              'FAIL cancel_between_loop_and_admission_no_capture'),
        'main-admission': ('''guard NG2TicketGuard.permits(expectedGeneration: generation, currentGeneration: run.generation,
                    cancelled: run.cancelReason != 0, ownerActive: ownerActive, foreground: foreground,
                    locked: locked, now: now, notBefore: command.not_before_ns, deadline: command.deadline_ns),
                    ng2_controller_begin''', 'guard ng2_controller_begin',
                           'FAIL production_capture_C_ticket_main_cancel_no_synth'),
        'legacy-pending': ('if NG2CaptureBridge.pendingRequests != 0 { return failure("Previous daemon capture is still outstanding.") }',
                           '// mutation: legacy pending start exclusion removed',
                           'FAIL legacy_timeout_actual_request_blocks_native_run'),
    }
    reds = {}
    for label,(old,new,expected) in mutations.items():
        if source.count(old)!=1: raise ValueError('runtime_mutation_target: '+label)
        (stage/'NG2Runtime.swift').write_text(source.replace(old,new))
        result = compile_run(sources, stage/(label+'-tests'), output, 'runtime-'+label+'-mutation-red', extra)
        require_red(result, expected); reds[label]=result.stdout.strip()
    return {'production_green':green.stdout.strip(),'mutation_red':reds,'compiled':True,
            'scope':'Actual Runtime public API, raster, real C, main ticket and lifecycle with UIKit/XCTest/daemon fakes'}


def capture_contract(upstream, output):
    stage=output/'daemon';stage.mkdir(exist_ok=True)
    native=upstream/'LoopCtrlUITests'
    shutil.copyfile(HERE/'ngg2_capture_host.h',stage/'NG2CaptureHostTest.h')
    shutil.copyfile(HERE/'ngg2_capture_tests.m',stage/'main.m')
    original=(native/'ObjCException.m').read_text()
    bridge=(native/'NG2CaptureBridge.m').read_text()
    (stage/'ObjCException.m').write_text(original)
    (stage/'NG2CaptureBridge.m').write_text(bridge)
    def run(label):
        target=stage/(label+'-tests')
        built=subprocess.run(['clang','-fobjc-arc','-fblocks','-DNG2_CAPTURE_HOST_TEST=1','-I',str(stage),'-I',str(native),
            str(stage/'ObjCException.m'),str(stage/'NG2CaptureBridge.m'),str(stage/'main.m'),
            '-framework','Foundation','-framework','CoreGraphics','-o',str(target)],capture_output=True,text=True,timeout=120)
        (output/(label+'-compile.txt')).write_text(built.stdout+built.stderr);built.check_returncode()
        result=subprocess.run([str(target.resolve())],capture_output=True,text=True,timeout=30)
        (output/(label+'-tests.txt')).write_text(result.stdout+result.stderr);return result
    green=run('daemon-production-green');green.check_returncode()
    if not green.stdout.startswith('PASS production legacy timeout and native daemon callback exclusion;') or green.stderr:
        raise RuntimeError('daemon_production_contract_missing')
    reds={}
    old='[NG2CaptureBridge legacyRequestEnded];'
    if original.count(old)!=1:raise ValueError('legacy_callback_mutation_target')
    (stage/'ObjCException.m').write_text(original.replace(old,'// mutation: actual legacy callback release removed'))
    result=run('legacy-callback-mutation-red');require_red(result,'FAIL legacy_actual_reply_releases_pending');reds['legacy']=result.stdout.strip()
    (stage/'ObjCException.m').write_text(original)
    old='[self legacyRequestEnded];'
    if bridge.count(old)!=1:raise ValueError('native_callback_mutation_target')
    (stage/'NG2CaptureBridge.m').write_text(bridge.replace(old,'// mutation: actual native callback release removed'))
    result=run('native-callback-mutation-red');require_red(result,'FAIL native_actual_reply_releases_pending');reds['native']=result.stdout.strip()
    return {'production_green':green.stdout.strip(),'mutation_red':reds,'compiled':True,
            'scope':'Actual ObjC legacy timeout and direct async callback bodies, fake private daemon classes'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--red-only', action='store_true')
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    if args.red_only:
        if len(args.paths) != 1:
            parser.error('--red-only requires output directory')
        output = args.paths[0]
        observed = execute(BASELINE, output, 'baseline-red')
        require_red(observed)
        report = {'baseline_red': {'compiled': True, 'returncode': 1,
                  'observed': observed.stdout.strip()}, 'device_test': 'not_run'}
    else:
        if len(args.paths) != 2:
            parser.error('requires patched upstream and output directory')
        upstream, output = args.paths
        output.mkdir(parents=True, exist_ok=True)
        baseline = execute(BASELINE, output, 'baseline-red')
        require_red(baseline)
        source = (upstream / 'LoopCtrlUITests/NG2Ticket.swift').read_text()
        observed = execute(source, output, 'production-green')
        observed.check_returncode()
        if not observed.stdout.startswith('PASS 20 pure Swift ticket/drain/heartbeat contracts;') or observed.stderr:
            raise RuntimeError('missing_production_green')
        old = '&& !cancelled && ownerActive && foreground && !locked'
        if source.count(old) != 1: raise ValueError('ticket_mutation_target')
        mutation = execute(source.replace(old, '&& ownerActive && foreground && !locked'), output, 'ticket-mutation-red')
        require_red(mutation)
        report = {'production_green': {'compiled': True, 'returncode': 0,
                  'observed': observed.stdout.strip()}, 'baseline_red': baseline.stdout.strip(),
                  'ticket_mutation_red': mutation.stdout.strip(),
                  'api': api_contract(upstream, output), 'raster': raster_contract(upstream, output),
                  'runtime': runtime_contract(upstream, output), 'daemon':capture_contract(upstream, output),
                  'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((upstream/'LoopCtrlUITests').glob('NG2*')) if p.is_file()},
                  'device_test': 'not_run'}
    (output / 'ngg2-swift-contract.json').write_text(json.dumps(report, indent=2)+'\n')
    print(observed.stdout, end='')


if __name__ == '__main__':
    main()
