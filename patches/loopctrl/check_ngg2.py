"""Compile production NG-G2 helpers and require executable behavior evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STRICT_PERCEPTION_FP = ['-fno-fast-math', '-ffp-contract=off']
TEST049_RUNTIME_COMMIT = 'bbdff15852cc4070392c54cc039b00d49cacd77c'
TEST049_RUNTIME_SHA256 = 'c41bc2ca168518775b73851a40ba055bc566d7c29ac13e7c4ded0573ec2e6fd9'
TEST050_RUNTIME_COMMIT = '53f722c6d925e0df5c84d377acc59b2e32cf8135'
TEST050_RUNTIME_SHA256 = '1938af7edd09a6b6689363cd9ad03d93148425e56256a2dc18bcab3b973115ab'


def native_object_flags(name, *, test049=False):
    # Match the app's per-source profile. Controller and Beat stay Debug O0.
    strict = name == 'NG2Perception.c' or (name == 'NG2Navigation.c' and not test049)
    return ['-O2', *STRICT_PERCEPTION_FP] if strict else ['-O0']

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
    static func authoritySampleIsFresh(start: UInt64, end: UInt64, now: UInt64) -> Bool { return false }
}
'''


def checked(result):
    """Keep compiler and unexpected assertion diagnostics visible in CI logs."""
    if result.returncode:
        print(result.stdout, end='', file=sys.stderr)
        print(result.stderr, end='', file=sys.stderr)
    result.check_returncode()


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
    checked(built)
    result = subprocess.run([str(executable.resolve())], capture_output=True,
                            text=True, timeout=30)
    (destination / (label + '-tests.txt')).write_text(result.stdout + result.stderr)
    return result


def require_red(result, expected=EXPECTED_RED):
    if result.returncode != 1 or result.stdout.strip().splitlines()[-1] != expected or result.stderr:
        print(result.stdout, end='', file=sys.stderr)
        print(result.stderr, end='', file=sys.stderr)
        raise RuntimeError('compiled_behavioral_red_not_observed')


def compile_run(sources, executable, output, label, extra=(), *, run_timeout=60):
    built = subprocess.run(['swiftc', *map(str, sources), *map(str, extra), '-o', str(executable)],
                           capture_output=True, text=True, timeout=180)
    (output / (label + '-compile.txt')).write_text(built.stdout + built.stderr)
    checked(built)
    result = subprocess.run([str(executable.resolve())], capture_output=True, text=True, timeout=run_timeout)
    (output / (label + '-tests.txt')).write_text(result.stdout + result.stderr)
    return result


def test051_public_fixture_source(tests):
    prefix_marker = '// TEST051 MANIFEST FIXTURE END.\n'
    begin, end = '// TEST051 PUBLIC FIXTURES BEGIN.\n', '// TEST051 PUBLIC FIXTURES END.\n'
    if any(tests.count(marker) != 1 for marker in (prefix_marker, begin, end)):
        raise ValueError('runtime_test051_public_fixture_boundary')
    return (tests.split(prefix_marker)[0]+prefix_marker+tests.split(begin)[1].split(end)[0]+
        '\ntestContinuousRevalidationCallbacksPublic()\ntestPagedResultsPublic()\n'
        'print("PASS production Runtime public API/TEST051 continuous callback and bounded image export fixtures")\n')


def test052_public_fixture_source(tests):
    prefix_marker = '// TEST051 MANIFEST FIXTURE END.\n'
    markers = ('// TEST051 PUBLIC FIXTURES BEGIN.\n', '// TEST051 PUBLIC FIXTURES END.\n',
               '// TEST052 PUBLIC FIXTURES BEGIN.\n', '// TEST052 PUBLIC FIXTURES END.\n')
    if any(tests.count(marker) != 1 for marker in (prefix_marker, *markers)):
        raise ValueError('runtime_test052_public_fixture_boundary')
    return (tests.split(prefix_marker)[0]+prefix_marker+
        tests.split(markers[0])[1].split(markers[1])[0]+
        tests.split(markers[2])[1].split(markers[3])[0]+
        '\ntestTargetDriftPlannerProof()\ntestTargetDriftRevalidationCallbacksPublic()\n'
        'print("PASS production Runtime public API/TEST052 reason8 target drift and original callback ownership fixtures")\n')


def test053_public_fixture_source(tests):
    prefix_marker = '// TEST051 MANIFEST FIXTURE END.\n'
    begin, end = '// TEST053 PUBLIC FIXTURES BEGIN.\n', '// TEST053 PUBLIC FIXTURES END.\n'
    if any(tests.count(marker) != 1 for marker in (prefix_marker, begin, end)):
        raise ValueError('runtime_test053_public_fixture_boundary')
    return (tests.split(prefix_marker)[0]+prefix_marker+tests.split(begin)[1].split(end)[0]+
        '\ntestStartupRemotePixelProof()\ntestInitialSlotPreparationPublic()\n'
        'print("PASS production Runtime public API/TEST053 frozen initial slot, measured authority preparation and original-window rejection fixtures")\n')


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
    checked(green)
    if not green.stdout.startswith('PASS 16 production authenticated owner projection contracts;') or green.stderr:
        raise RuntimeError('api_production_contract_missing')
    old = 'native["_necro_owner"] = .string(owner)'
    if helper.count(old) != 1: raise ValueError('api_mutation_target')
    (stage / 'NG2AuthenticatedOwner.swift').write_text('import Foundation\n'+helper.replace(old, '// owner projection removed')+'\n')
    red = compile_run(sources, stage / 'api-mutated-tests', output, 'api-mutation-red')
    if red.returncode != 1 or 'FAIL authenticated_owner_' not in red.stdout or red.stderr:
        raise RuntimeError('api_mutation_red_missing')
    return {'production_green': green.stdout.strip(), 'mutation_red': red.stdout.strip(), 'compiled': True}


def raster_contract(upstream, output, *, expect_red=False, expect_native_red=False):
    output.mkdir(parents=True, exist_ok=True)
    stage = output / 'raster'; stage.mkdir(exist_ok=True)
    native = HERE / 'ngg2' if expect_red or expect_native_red else upstream / 'LoopCtrlUITests'
    objects = []
    for source in sorted(native.glob('NG2*.c')):
        target = stage / (source.stem + '.o')
        result = subprocess.run(['clang', '-std=c11', *native_object_flags(source.name),
                                '-I', str(native), '-c', str(source), '-o', str(target)],
                                capture_output=True, text=True, timeout=120)
        (output / (source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
        checked(result); objects.append(target)
    if len(objects) != 4: raise ValueError('native_C_source_set')
    source = (native / 'NG2Raster.swift').read_text()
    (stage / 'NG2Raster.swift').write_text(source)
    reference = (HERE / 'ngg2_raster_reference.swift').read_text()
    frozen = reference[reference.index('import Foundation\n'):].replace('enum NG2RasterReference', 'enum NG2Raster')
    if hashlib.sha256(frozen.encode()).hexdigest() != '2c526132b673fa26a0b18390eee24cf76fe19756a7c24906fb0ad17b58e1a3b7':
        raise ValueError('raster_frozen_reference_hash')
    (stage / 'NG2RasterReference.swift').write_text(reference)
    shutil.copyfile(HERE / 'ngg2_raster_tests.swift', stage / 'main.swift')
    sources = [stage / 'NG2Raster.swift', stage / 'NG2RasterReference.swift', stage / 'main.swift']
    # Only this Raster executable replaces the Perception object with a renamed
    # implementation and a thin call-count wrapper. Runtime keeps the four
    # original production NG2*.o objects, without the spy or any global counter.
    (stage/'NG2RasterHost.h').write_text('#include "NG2Core.h"\nvoid ng2_raster_spy_reset(void);\nuint64_t ng2_raster_spy_calls(void);\n')
    spy_objects = []
    for path,target,flags in [(native/'NG2Perception.c',stage/'perception-native.o',
            ['-Dng2_orient_rgba=ng2_orient_rgba_real']),
            (HERE/'ngg2_raster_spy.c',stage/'orientation-spy.o',[])]:
        built = subprocess.run(['clang','-std=c11','-O2',
            *(STRICT_PERCEPTION_FP if path.name == 'NG2Perception.c' else []),'-I',str(native),*flags,
            '-c',str(path),'-o',str(target)],capture_output=True,text=True,timeout=120)
        (output/(target.stem+'-compile.txt')).write_text(built.stdout+built.stderr)
        checked(built);spy_objects.append(target)
    extra = ['-D','NG2_RASTER_HOST_TEST','-Xcc','-I'+str(native),'-import-objc-header',stage/'NG2RasterHost.h',
             *[o for o in objects if o.name!='NG2Perception.o'],*spy_objects]
    label = ('raster-baseline-red' if expect_red else
             'raster-native-baseline-red' if expect_native_red else 'raster-production-green')
    green = compile_run(sources, stage / 'raster-tests', output, label, extra, run_timeout=180)
    if expect_red:
        require_red(green, 'FAIL orientation_1_identity_avoids_pixel_copy actual=6 expected=0')
        return {'baseline_red': green.stdout.strip(), 'compiled': True, 'returncode': 1,
                'scope': 'public normalizeProfiled with unchanged pixel loop and real copy accounting'}
    if expect_native_red:
        require_red(green,'FAIL orientation_8_uses_native_C actual=0 expected=1')
        detailed = subprocess.run([str((stage/'raster-tests').resolve()),'--decode-failure-contract'],
            capture_output=True,text=True,timeout=30)
        (output/'raster-detailed-baseline-red-tests.txt').write_text(detailed.stdout+detailed.stderr)
        require_red(detailed,'FAIL detailed_empty_failure_stage_and_code')
        return {'baseline_red':green.stdout.strip(),'detailed_baseline_red':detailed.stdout.strip(),
                'compiled':True,'returncode':1,'scope':'public native-call spy and executable typed decode stub'}
    checked(green)
    # macOS hosted arm runners can emit this unavailable accelerator notice
    # during real ImageIO JPEG work. Retain it in evidence, allow only this
    # exact line, and still reject every other stderr diagnostic.
    warnings = green.stderr.strip().splitlines()
    if (not green.stdout.startswith('PASS production CoreGraphics')
        or any(line != 'IOServiceMatchingfailed for: AppleM2ScalerParavirtDriver' for line in warnings)):
        raise RuntimeError('raster_production_contract_missing')
    perception = (native/'NG2Perception.c').read_text()
    old = 'case 6:sx=y;sy=height-1-x;break;'
    if perception.count(old)!=1:raise ValueError('raster_C_orientation_mutation_target')
    mutation_source=stage/'perception-mutation.c'
    mutation_source.write_text(perception.replace(old,'case 6:sx=y;sy=x;break;'))
    original_spy_object=(stage/'perception-native.o').read_bytes()
    try:
        built=subprocess.run(['clang','-std=c11','-O2',*STRICT_PERCEPTION_FP,'-I',str(native),
            '-Dng2_orient_rgba=ng2_orient_rgba_real','-c',str(mutation_source),
            '-o',str(stage/'perception-native.o')],capture_output=True,text=True,timeout=120)
        (output/'raster-C-orientation-mutation-compile.txt').write_text(built.stdout+built.stderr)
        checked(built)
        red=compile_run(sources,stage/'raster-mutated-tests',output,'raster-mutation-red',extra,run_timeout=180)
        require_red(red,'FAIL orientation_6_asymmetric_pixels')
    finally:
        (stage/'perception-native.o').write_bytes(original_spy_object)
    old = '        if orientation != 1 {\n'
    if source.count(old) != 1: raise ValueError('raster_identity_mutation_target')
    (stage / 'NG2Raster.swift').write_text(source.replace(old, '        if true {\n'))
    identity_red = compile_run(sources, stage / 'raster-identity-tests', output,
        'raster-identity-mutation-red', extra, run_timeout=180)
    require_red(identity_red, 'FAIL orientation_1_identity_avoids_pixel_copy actual=6 expected=0')
    begin='// NG-G2 BEGIN native orientation integer copy.'
    end='// NG-G2 END native orientation integer copy.'
    if source.count(begin)!=1 or source.count(end)!=1:raise ValueError('raster_native_copy_boundary')
    copy_start=source.rfind('\n',0,source.index(begin))+1
    copy_end=source.index('\n',source.index(end))+1
    old_loop=reference[reference.index('        original.withUnsafeBytes { source in\n'):
                       reference.index('        if orientedWidth == outputWidth')]
    old_loop=''.join('    '+line for line in old_loop.splitlines(keepends=True))
    old_loop+='            copyPixels = UInt64(orientedWidth * orientedHeight)\n'
    (stage/'NG2Raster.swift').write_text(source[:copy_start]+old_loop+source[copy_end:])
    backend_red=compile_run(sources,stage/'raster-backend-tests',output,
        'raster-native-backend-mutation-red',extra,run_timeout=180)
    require_red(backend_red,'FAIL orientation_8_uses_native_C actual=0 expected=1')
    return {'production_green': green.stdout.strip(), 'mutation_red': red.stdout.strip(),
            'identity_mutation_red': identity_red.stdout.strip(),
            'native_backend_mutation_red':backend_red.stdout.strip(),
            'environment_warnings': warnings, 'compiled': True}


def perception_profile_contract(upstream, output, *, compiler='clang'):
    """Apple Clang compares complete outputs, using the unchanged O0 reference."""
    stage = output / 'perception-profile'; stage.mkdir(exist_ok=True)
    native = upstream / 'LoopCtrlUITests'
    reference_object = stage / 'reference.o'
    renames = ['-Dng2_analyze_rgba=ref_ng2_analyze_rgba',
               '-Dng2_fingerprint_changed=ref_ng2_fingerprint_changed',
               '-Dng2_orient_rgba=ref_ng2_orient_rgba']
    reference_command = [compiler, '-std=c11', '-O0', '-I', str(native), *renames,
                         '-c', str(native/'NG2Perception.c'), '-o', str(reference_object)]
    built = subprocess.run(reference_command, capture_output=True, text=True, timeout=120)
    (output/'perception-profile-reference-compile.txt').write_text(built.stdout+built.stderr)
    checked(built)
    production_object = output/'raster/NG2Perception.o'
    if not production_object.is_file():
        raise ValueError('perception_profile_production_object_missing')

    def run(label, object_path):
        executable = stage/(label+'-tests')
        command = [compiler, '-std=c11', '-O2', *STRICT_PERCEPTION_FP,
            '-Wall', '-Wextra', '-Werror', '-pedantic', '-I', str(native), '-I', str(HERE),
            str(HERE/'ngg2_perception_profile_tests.c'), str(HERE/'ngg2_runtime_scene_fixtures.c'),
            str(reference_object), str(object_path), '-lm', '-o', str(executable)]
        built = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (output/('perception-profile-'+label+'-compile.txt')).write_text(built.stdout+built.stderr)
        checked(built)
        result = subprocess.run([str(executable.resolve())], capture_output=True, text=True, timeout=120)
        (output/('perception-profile-'+label+'-tests.txt')).write_text(result.stdout+result.stderr)
        return result

    green = run('production-green', production_object)
    checked(green)
    if not green.stdout.startswith('PASS strict O2 perception matches unchanged O0;') or green.stderr:
        raise RuntimeError('perception_profile_production_contract_missing')
    # A one-field difference exercises the whole-Scene comparison, even while
    # basic state and movement thresholds remain unchanged. Runtime's four
    # production objects are never overwritten by this profile-only mutant.
    original = (native/'NG2Perception.c').read_text()
    old = 'out->gold_peak=(int32_t)peak;'
    if original.count(old) != 1:
        raise ValueError('perception_profile_whole_scene_mutation_target')
    mutation_source = stage/'perception-mutated.c'
    mutation_source.write_text(original.replace(old, 'out->gold_peak=(int32_t)peak+1;'))
    mutation_object = stage/'perception-mutated.o'
    built = subprocess.run([compiler, '-std=c11', '-O2', *STRICT_PERCEPTION_FP,
        '-I', str(native), '-c', str(mutation_source), '-o', str(mutation_object)],
        capture_output=True, text=True, timeout=120)
    (output/'perception-profile-whole-scene-mutation-compile.txt').write_text(built.stdout+built.stderr)
    checked(built)
    red = run('whole-scene-mutation-red', mutation_object)
    require_red(red, 'FAIL strict_O2_and_unchanged_O0_entire_scene_bytes')
    return {'production_green': green.stdout.strip(), 'mutation_red': red.stdout.strip(),
            'compiled': True, 'reference_flags': ['-O0'],
            'optimized_flags': ['-O2', *STRICT_PERCEPTION_FP],
            'compiler': subprocess.check_output([compiler, '--version'], text=True, timeout=30).strip(),
            'architecture': platform.machine(),
            'source_sha256': hashlib.sha256((native/'NG2Perception.c').read_bytes()).hexdigest(),
            'test_source_sha256': {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                for name in ('ngg2_perception_profile_tests.c', 'ngg2_runtime_scene_fixtures.c',
                             'ngg2_runtime_scene_fixtures.h')},
            'scope': 'same production C file, unchanged O0 and strict O2 complete synthetic Scene/RGBA output parity'}


def navigation_profile_contract(upstream, output, *, compiler='clang'):
    """Compare whole Navigation outputs and static scores with untouched O0."""
    stage = output/'navigation-profile'; stage.mkdir(exist_ok=True)
    native = upstream/'LoopCtrlUITests'
    probe = HERE/'ngg2_navigation_profile_tests.c'
    base = [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-I', str(native)]
    reference_object = stage/'reference.o'
    static_object = stage/'strict-static-probes.o'
    commands = {
        'reference': [*base, '-O0', '-DNG2_NAVIGATION_PROFILE_WRAPPER=1',
            '-DNG2_PROFILE_REFERENCE=1', '-c', str(probe), '-o', str(reference_object)],
        'static-probes': [*base, '-O2', *STRICT_PERCEPTION_FP,
            '-DNG2_NAVIGATION_PROFILE_WRAPPER=1', '-c', str(probe), '-o', str(static_object)],
    }
    for label, command in commands.items():
        built = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (output/('navigation-profile-'+label+'-compile.txt')).write_text(built.stdout+built.stderr)
        checked(built)
    production_object = output/'raster/NG2Navigation.o'
    if not production_object.is_file():
        raise ValueError('navigation_profile_production_object_missing')

    def run(label, object_path):
        executable = stage/(label+'-tests')
        command = [*base, '-O0', str(probe), str(reference_object), str(static_object),
            str(object_path), '-lm', '-o', str(executable)]
        built = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (output/('navigation-profile-'+label+'-compile.txt')).write_text(built.stdout+built.stderr)
        checked(built)
        result = subprocess.run([str(executable.resolve())], capture_output=True, text=True, timeout=120)
        (output/('navigation-profile-'+label+'-tests.txt')).write_text(result.stdout+result.stderr)
        return result

    green = run('production-green', production_object)
    checked(green)
    if not green.stdout.startswith('PASS strict O2 Navigation matches unchanged O0;') or green.stderr:
        raise RuntimeError('navigation_profile_production_contract_missing')
    source = (native/'NG2Navigation.c').read_text()
    old = 'out->target_y=y;'
    if source.count(old) != 1:
        raise ValueError('navigation_profile_whole_decision_mutation_target')
    mutation_source = stage/'NG2Navigation-mutated.c'
    mutation_source.write_text(source.replace(old, 'out->target_y=y+1;'))
    mutation_object = stage/'navigation-mutated.o'
    built = subprocess.run([*base, '-O2', *STRICT_PERCEPTION_FP,
        '-c', str(mutation_source), '-o', str(mutation_object)], capture_output=True, text=True, timeout=120)
    (output/'navigation-profile-whole-decision-mutation-compile.txt').write_text(built.stdout+built.stderr)
    checked(built)
    red = run('whole-decision-mutation-red', mutation_object)
    require_red(red, 'FAIL strict_O2_and_unchanged_O0_entire_Decision_bytes')
    return {'production_green': green.stdout.strip(), 'mutation_red': red.stdout.strip(),
            'compiled': True, 'reference_flags': ['-O0'],
            'optimized_flags': ['-O2', *STRICT_PERCEPTION_FP],
            'compiler': subprocess.check_output([compiler, '--version'], text=True, timeout=30).strip(),
            'architecture': platform.machine(),
            'source_sha256': hashlib.sha256((native/'NG2Navigation.c').read_bytes()).hexdigest(),
            'test_source_sha256': hashlib.sha256(probe.read_bytes()).hexdigest(),
            'compile_commands': commands,
            'scope': 'actual production strict Navigation public API, unchanged O0, complete views/73-score bytes/Motion/Decision/Entrance/boundary and input parity'}


def runtime_contract(upstream, output, *, expect_capture_red=False, expect_dispatch_red=False, expect_observe_red=False, expect_manifest_red=False, baseline_native=None, public051_only=False, new051_mutations_only=False, selected_mutations=None, public052_only=False, new052_mutations_only=False, public053_only=False, new053_mutations_only=False):
    stage = output / 'runtime'; stage.mkdir(exist_ok=True)
    native = HERE/'ngg2' if expect_capture_red or expect_dispatch_red or expect_observe_red or expect_manifest_red else upstream / 'LoopCtrlUITests'
    if baseline_native is not None:
        native = baseline_native
    (stage / 'NG2RuntimeFixture.h').write_text('#include "NG2Core.h"\n#include "NG2Controller.h"\n#include "ngg2_runtime_scene_fixtures.h"\nvoid ng2_test_pause(uint8_t *, size_t);\n')
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
    (output/'runtime-fixture-compile.txt').write_text(built.stdout+built.stderr); checked(built)
    scene_object = stage/'scene-fixtures.o'
    fixture_build = subprocess.run(['clang', '-std=c11', '-O2', '-I', str(native),
        '-c', str(HERE/'ngg2_runtime_scene_fixtures.c'), '-o', str(scene_object)],
        capture_output=True, text=True, timeout=60)
    (output/'runtime-scene-fixtures-compile.txt').write_text(fixture_build.stdout+fixture_build.stderr)
    checked(fixture_build)
    shutil.copyfile(HERE/'ngg2_runtime_fakes.swift', stage/'Fakes.swift')
    shutil.copyfile(HERE/'ngg2_runtime_tests.swift', stage/'main.swift')
    source = (native/'NG2Runtime.swift').read_text()
    if public051_only or new051_mutations_only:
        (stage/'main.swift').write_text(test051_public_fixture_source((HERE/'ngg2_runtime_tests.swift').read_text()))
    if public052_only or new052_mutations_only:
        (stage/'main.swift').write_text(test052_public_fixture_source((HERE/'ngg2_runtime_tests.swift').read_text()))
    if public053_only or new053_mutations_only:
        (stage/'main.swift').write_text(test053_public_fixture_source((HERE/'ngg2_runtime_tests.swift').read_text()))
    if expect_manifest_red:
        source = subprocess.check_output(['git', 'show', TEST050_RUNTIME_COMMIT+
            ':patches/loopctrl/ngg2/NG2Runtime.swift'], cwd=HERE).decode()
        if hashlib.sha256(source.encode()).hexdigest() != TEST050_RUNTIME_SHA256:
            raise ValueError('runtime_manifest_baseline_source_hash')
        tests = (HERE/'ngg2_runtime_tests.swift').read_text()
        marker = '// TEST051 MANIFEST FIXTURE END.\n'
        if tests.count(marker) != 1:
            raise ValueError('runtime_manifest_baseline_boundary')
        (stage/'main.swift').write_text(tests.split(marker)[0]+marker+
            'testPagedResultsManifestPublicBaseline()\n')
    if expect_capture_red:
        baseline = '31b428bab258b7a1a3d948379c0b2e55d9dd9e24'
        source = subprocess.check_output(['git','show',baseline+':patches/loopctrl/ngg2/NG2Runtime.swift'],cwd=HERE).decode()
        fakes = subprocess.check_output(['git','show',baseline+':patches/loopctrl/ngg2_runtime_fakes.swift'],cwd=HERE).decode()
        if hashlib.sha256(source.encode()).hexdigest()!='5d99106b8ba08af2dc867a137b8dd2f112d16e0595676b5d06002f37859b8c93':
            raise ValueError('runtime_failure_baseline_source_hash')
        if hashlib.sha256(fakes.encode()).hexdigest()!='d73f682ee7b2f12287658b5c67cd404c942df185477f750f8e9937c819060116':
            raise ValueError('runtime_failure_baseline_fakes_hash')
        # Current source defines a shared walking-fixture helper that is not
        # called by this historical nil-capture baseline. Keep that declaration
        # compilable with the hash-checked original fake; the inert extension
        # changes neither its capture behavior nor the fixed production bytes.
        (stage/'Fakes.swift').write_text(fakes+'\nextension NG2Fake { static func useFixedCaptureClock() {} }\n')
        tests = (HERE/'ngg2_runtime_tests.swift').read_text()
        marker = '// TEST047 RUNTIME FAILURE BASELINE END.\n'
        if tests.count(marker)!=1:raise ValueError('runtime_failure_baseline_boundary')
        (stage/'main.swift').write_text(tests.split(marker)[0]+marker)
    if expect_dispatch_red:
        baseline = '20912df2efd2f84245e02464baf5c4a177799cb4'
        source = subprocess.check_output(['git','show',baseline+':patches/loopctrl/ngg2/NG2Runtime.swift'],cwd=HERE).decode()
        if hashlib.sha256(source.encode()).hexdigest()!='c11fd45d52f5884f71b5ef29ec4b3692b72570e4bca448fff9fc640254bab09f':
            raise ValueError('runtime_dispatch_baseline_source_hash')
        marker = '// TEST048 RUNTIME DISPATCH BASELINE END.\n'
        tests = (HERE/'ngg2_runtime_tests.swift').read_text()
        if tests.count(marker)!=1:raise ValueError('runtime_dispatch_baseline_boundary')
        (stage/'main.swift').write_text(tests.split(marker)[0]+marker)
    if expect_observe_red:
        # The source bytes are fixed in Git, even after the app producer changes.
        # New fixture hooks remain unused by this exact previous Runtime.
        source = subprocess.check_output(['git', 'show', TEST049_RUNTIME_COMMIT+
            ':patches/loopctrl/ngg2/NG2Runtime.swift'], cwd=HERE).decode()
        if hashlib.sha256(source.encode()).hexdigest() != TEST049_RUNTIME_SHA256:
            raise ValueError('runtime_observe_baseline_source_hash')
        tests = (HERE/'ngg2_runtime_tests.swift').read_text()
        marker = '// TEST050 OBSERVE FIXTURE END.\n'
        if tests.count(marker) != 1:
            raise ValueError('runtime_observe_baseline_boundary')
        (stage/'main.swift').write_text(tests.split(marker)[0]+marker+
            'testObserveStartAtCommittedCBoundary()\n')
    (stage/'NG2Runtime.swift').write_text(source)
    sources = [output/'api/RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
               stage/'Fakes.swift', stage/'NG2Runtime.swift', stage/'main.swift']
    objects = sorted((output/'raster').glob('NG2*.o'))+[stage/'fixture.o', scene_object]
    extra = ['-D', 'NG2_RUNTIME_HOST_TEST', '-Xcc', '-I'+str(native), '-Xcc', '-I'+str(HERE), '-import-objc-header', stage/'NG2RuntimeFixture.h', *objects]
    green = compile_run(sources, stage/'runtime-tests', output,
        'runtime-manifest-baseline-red' if expect_manifest_red else
        'runtime-observe-baseline-red' if expect_observe_red else
        'runtime-dispatch-baseline-red' if expect_dispatch_red else
        'runtime-failure-baseline-red' if expect_capture_red else 'runtime-production-green', extra, run_timeout=120)
    if expect_manifest_red:
        require_red(green, 'FAIL MISSING_paged_results_manifest')
        return {'baseline_red': green.stdout.strip(), 'compiled': True, 'returncode': 1,
                'stderr': green.stderr, 'source_commit': TEST050_RUNTIME_COMMIT,
                'source_sha256': TEST050_RUNTIME_SHA256,
                'scope': 'fixed TEST050 Runtime, real C, public terminal/drained manifest request; no new C detail dependency'}
    if expect_observe_red:
        require_red(green, 'FAIL MISSING_observe_start_ns')
        return {'baseline_red': green.stdout.strip(), 'compiled': True, 'returncode': 1,
                'stderr': green.stderr, 'source_commit': TEST049_RUNTIME_COMMIT,
                'source_sha256': TEST049_RUNTIME_SHA256,
                'scope': 'fixed TEST049 Runtime, real C, public committed capture/results with independent C-boundary clock'}
    if expect_dispatch_red:
        require_red(green,'FAIL move_foreground_prepared_before_final_callback_is_offered')
        return {'baseline_red':green.stdout.strip(),'compiled':True,'returncode':1,
                'scope':'fixed TEST047 production Runtime, real C and public held MOVE callback'}
    if expect_capture_red:
        require_red(green,'FAIL capture_failure_actual_nil_reply_is_reported')
        return {'baseline_red':green.stdout.strip(),'compiled':True,'returncode':1,
                'scope':'previous production Runtime and public nil-reply results fixture'}
    checked(green)
    if not green.stdout.startswith('PASS production Runtime public API/') or green.stderr:
        raise RuntimeError('runtime_production_contract_missing')
    if public051_only:
        return {'production_green': green.stdout.strip(), 'compiled': True,
                'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'scope': 'TEST051 production Runtime public revalidation/callback/drain and paged image producer contracts'}
    if public052_only:
        return {'production_green': green.stdout.strip(), 'compiled': True,
                'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'controller_sha256': hashlib.sha256((native/'NG2Controller.c').read_bytes()).hexdigest(),
                'scope': 'TEST052 real Perception/Navigation reason8 target drift, public Runtime callback/lease/drain contracts'}
    if public053_only:
        return {'production_green': green.stdout.strip(), 'compiled': True,
                'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'controller_sha256': hashlib.sha256((native/'NG2Controller.c').read_bytes()).hexdigest(),
                'scope': 'TEST053 actual first-slot arming, three remote changes, AX/main costs, original ticket and slow-AX rejection with full callback drain'}
    all_tests = (HERE/'ngg2_runtime_tests.swift').read_text()
    new_calls = '\ntestContinuousRevalidationCallbacksPublic()\ntestPagedResultsPublic()\n'
    target_calls = 'testTargetDriftPlannerProof()\ntestTargetDriftRevalidationCallbacksPublic()\n'
    startup_calls = 'testStartupRemotePixelProof()\ntestInitialSlotPreparationPublic()\n'
    if all_tests.count(new_calls) != 1 or all_tests.count(target_calls) != 1 or all_tests.count(startup_calls) != 1:
        raise ValueError('runtime_test051_public_calls_boundary')
    if selected_mutations is not None:
        if selected_mutations != 'stale-entry':
            raise ValueError('runtime_selected_mutation_not_supported')
        # Run the complete production Green above, then the exact established
        # fault with all original preceding fixtures and its named assertion.
        # This is a real selected execution, never a synthetic Red substitute.
        (stage/'main.swift').write_text(all_tests.replace(new_calls, '\n').replace(target_calls, '\n').replace(startup_calls, '\n'))
        ownership = '        guard ownsTicket(run, command, generation: generation) else { return }'
        if source.count(ownership) != 1:
            raise ValueError('runtime_stale_entry_mutation_target')
        (stage/'NG2Runtime.swift').write_text(source.replace(ownership, '// mutation: stale callback early ownership removed'))
        print('Runtime mutation: stale-entry', flush=True)
        result = compile_run(sources, stage/'stale-entry-tests', output, 'runtime-stale-entry-mutation-red', extra, run_timeout=120)
        require_red(result, 'FAIL replan_stale_callback_skips_final_authority_hook')
        print('Runtime mutation observed: stale-entry / '+result.stdout.strip().splitlines()[-1], flush=True)
        (stage/'NG2Runtime.swift').write_text(source)
        (stage/'main.swift').write_text(all_tests)
        return {'production_green': green.stdout.strip(), 'mutation_red': {'stale-entry': result.stdout.strip()},
                'compiled': True, 'baseline_mutation_count': 1, 'test051_mutation_count': 0,
                'mutation_selection': ['stale-entry'],
                'native_object_flags': {path.name: native_object_flags(path.name) for path in sorted(native.glob('NG2*.c'))},
                'scope': 'Full production Runtime Green and exact selected established stale-entry mutation; all preceding fixtures retained'}
    reds = {}
    if not new051_mutations_only and not new052_mutations_only and not new053_mutations_only:
        # Established faults retain their original fixtures/assertions. Execute
        # new public fixtures once in production Green and for their own faults,
        # avoiding dozens of unrelated repeated PNG boundary stress runs.
        (stage/'main.swift').write_text(all_tests.replace(new_calls, '\n').replace(target_calls, '\n').replace(startup_calls, '\n'))
        reds = {}
        clock_begin = source.index('        DispatchQueue.main.sync {', source.index('    private func execute('))
        clock_end = source.index('                run.inFlight = true', clock_begin)
        clock_gate = source[clock_begin:clock_end]
        if clock_gate.count('                let now = Self.now()') != 1:
            raise ValueError('runtime_clock_mutation_target')
        # The UI RESUME fixture crosses its deadline after main entry. Keep MOVE
        # clocks real so their independent not-before alignment remains setup,
        # rather than becoming an earlier rejection that masks this fault.
        stale_clock_gate = clock_gate.replace('        DispatchQueue.main.sync {',
            '        DispatchQueue.main.sync {\n            let admissionClockSnapshot = Self.now()', 1).replace(
            'locked: locked, now: now, notBefore: command.not_before_ns',
            'locked: locked, now: command.kind == 4 ? now : admissionClockSnapshot, notBefore: command.not_before_ns', 1).replace(
            'ng2_controller_begin(core, command.id, now, foreground ? 1 : 0',
            'ng2_controller_begin(core, command.id, command.kind == 4 ? now : admissionClockSnapshot, foreground ? 1 : 0', 1)
        prepare_begin = source.index('    private func prepare(')
        query_begin = source.index('            let authorityQueryStart = Self.now()', prepare_begin)
        query_end = source.index('\n        }\n        return sample', query_begin)
        query_block = source[query_begin:query_end]
        query_inside_lock = ('            run.lock.ng2Locked {\n'
            + ''.join('    '+line for line in query_block.splitlines(keepends=True)) + '\n            }')
        final_query_block = query_block.replace(
            '            sample = AuthoritySample(', '            let authority = AuthoritySample(')
        final_query_source = source[:query_begin] + '// mutation: foreground query delayed until final dispatch\n' + source[query_end:]
        final_foreground = '            let foreground = authority.foreground\n'
        if final_query_source.count(final_foreground)!=1:raise ValueError('runtime_final_query_mutation_target')
        final_query_source = final_query_source.replace(final_foreground,final_query_block+'\n')
        mutations = {
            'capture-admission': ('guard !run.stopped, run.cancelReason == 0, self.ownerActive(run) else { return nil }',
                                  '// mutation: capture admission recheck removed',
                                  'FAIL cancel_between_loop_and_admission_no_capture'),
            'main-admission': ('            guard permitted else { return }',
                               '            // mutation: synth proceeds without a successful begin gate',
                               'FAIL expired_during_main_admission_no_synth'),
            'analysis-commit': ('guard run.generation == analysisGeneration, run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return false }',
                                '// mutation: revoked analysis commit exclusion removed',
                                'FAIL revoked_analysis_never_observed_or_retained_cancel'),
            'analysis-owner': ('guard run.generation == analysisGeneration, run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return false }',
                               'guard run.generation == analysisGeneration, run.cancelReason == 0, !run.stopped else { return false }',
                               'FAIL revoked_analysis_never_observed_or_retained_owner'),
            'foreground-lock': (query_block, query_inside_lock,
                                'FAIL foreground_IPC_hold_keeps_status_cancel_nonblocking'),
            'main-clock': (clock_gate, stale_clock_gate, 'FAIL expired_during_main_admission_no_synth'),
            'move-input': ('result = run.fast?.fastGesture([[(point: point, t: 0.0), (point: point, t: 0.05)]]) ?? (nil, .internalError)',
                           'result = run.fast?.fastTap(x: Double(command.x), y: Double(command.y)) ?? (nil, .internalError)',
                           'FAIL prepared_move_final_has_no_AX_and_one_50ms_gesture'),
            'legacy-pending': ('if NG2CaptureBridge.pendingRequests != 0 { return failure("Previous daemon capture is still outstanding.") }',
                               '// mutation: legacy pending start exclusion removed',
                               'FAIL legacy_timeout_actual_request_blocks_native_run'),
            'stale-cleanup': ('run.lock.ng2Locked { run.mainCallbacks.remove(command.id) }',
                              'run.lock.ng2Locked { run.mainCallbacks.remove(command.id); run.mainCommandID = 0 }',
                              'FAIL replan_replacement_is_only_direction_synth'),
            'callback-drain': ('mainOutstanding: run.mainOutstanding, legacyCaptures: legacy)',
                               'mainOutstanding: false, legacyCaptures: legacy)',
                               'FAIL replan_queued_stale_callback_keeps_core_and_lease'),
            'difference-reference': ('''            for change in changes.prefix(min(changeCount, changes.count)) {
                required.insert(change.source_capture_id); required.insert(change.observed_capture_id)
            }''', '// mutation: rejected scene difference image references removed',
                                     'FAIL rejected_difference_frames_pinned_beyond_recent_window'),
            # Keep the earlier initial-alignment fixture's clock barrier intact;
            # regress the real callsite's clock specifically while an ACK waits.
            'motion-clock': ('ng2_controller_tick(core, Self.now(), run.foreground',
                             'ng2_controller_tick(core, status.input_state == 3 && status.inputs > 0 ? now : Self.now(), run.foreground',
                             'FAIL motion_deadline_rechecked_after_analysis_before_next_tick'),
            'raster-trace': ('''                    run.rasterSamples.append(.object(["capture_id": number(frame.id),
                        "source_width": .int(trace.sourceWidth), "source_height": .int(trace.sourceHeight),
                        "orientation": .int(trace.orientation), "source_ns": number(trace.sourceNs),
                        "draw_ns": number(trace.drawNs), "orient_ns": number(trace.orientNs),
                        "scale_ns": number(trace.scaleNs), "copy_pixels": number(trace.copyPixels)]))''',
                             '// mutation: committed raster trace propagation removed',
                             'FAIL raster_trace_first_and_latest_retention_31'),
            'capture-failure-connection': (
                'commitCaptureFailure(run, generation: before.3, id: before.0, start: start, end: captureEnd, failure: failure)',
                '// mutation: actual capture failure diagnostic connection removed',
                'FAIL capture_failure_actual_nil_reply_is_reported'),
            'capture-failure-generation': (
                'guard run.generation == failureGeneration, run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return false }',
                'guard run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return false }',
                'FAIL capture_failure_generation_only_revocation_does_not_publish'),
            'capture-failure-first': (
                'guard run.captureFailure == nil else { return false }',
                '// mutation: first capture failure immutability removed',
                'FAIL capture_failure_first_record_is_immutable'),
            'capture-failure-orientation': (
                'orientation: frame.diagnosticOrientation))',
                'orientation: trace.orientation))',
                'FAIL capture_failure_real_C_analysis_rejection_is_reported'),
            'observe-start-connection': (
                '"observe_start_ns": number(observeStart), ',
                '',
                'FAIL MISSING_observe_start_ns'),
        }
        mutations.update({
            'authority-origin': ('start: authority.start, end: authority.end, now: now)',
                                 'start: authority.end, end: authority.end, now: now)',
                                 'FAIL authority_sample_over_1s_no_synth_query'),
            'final-lock': ('            let locked = LockStateMonitor.shared().isLocked',
                           '            let locked = false // mutation: final live lock is not sampled',
                           'FAIL final_authority_loss_no_synth_or_cleanup_lock'),
            'prepare-token': ('        return sample\n',
                              '        run.lock.ng2Locked { run.mainCallbacks.remove(command.id) }\n        return sample\n',
                              'FAIL prepared_move_pipeline_retains_lease_between_prepare_and_final'),
        })
        dispatch_begin = source.index('        run.dispatchFailure = [',source.index('    private func recordDispatchFailure('))
        dispatch_end = source.index('\n    }',dispatch_begin)
        dispatch_storage = source[dispatch_begin:dispatch_end]
        mutations.update({
            'dispatch-failure-connection': (dispatch_storage,
                '        // mutation: live MOVE rejection diagnostic is not stored',
                'FAIL dispatch_failure_actual_producer_exact_schema_and_reason_foreground'),
            'dispatch-failure-first': ('guard command.kind == 4, run.dispatchFailure == nil else { return }',
                'guard command.kind == 4 else { return }',
                'FAIL dispatch_failure_first_record_is_immutable'),
            'dispatch-failure-generation': ('guard run.mainCommandID == command.id, run.generation == generation, run.cancelReason == 0 else { return }',
                'guard run.mainCommandID == command.id, run.cancelReason == 0 else { return }',
                'FAIL dispatch_failure_stale_generation_does_not_publish'),
            'dispatch-failure-command': ('guard run.mainCommandID == command.id, run.generation == generation, run.cancelReason == 0 else { return }',
                'guard run.generation == generation, run.cancelReason == 0 else { return }',
                'FAIL dispatch_failure_stale_command_does_not_publish'),
            'dispatch-failure-query-start': ('"query_start_ns": authority.start == 0 ? .null : number(authority.start)',
                '"query_start_ns": authority.start == 0 ? .null : number(authority.end)',
                'FAIL dispatch_failure_actual_producer_exact_schema_and_reason_foreground'),
        })
        observe_clock = '                    let observeStart = Self.now()\n'
        observe_gate = '                let committed = run.lock.ng2Locked { () -> Bool in\n'
        if source.count(observe_clock) != 1 or source.count(observe_gate) != 1:
            raise ValueError('runtime_observe_start_placement_mutation_target')
        # Moving the real producer sample ahead of the commit guard observes the
        # gate clock (+100), while the independent C boundary enters at +200.
        misplaced_observe = source.replace(observe_clock, '').replace(observe_gate,
            '                let observeStart = Self.now()\n'+observe_gate)
        mutations['observe-start-placement'] = (source, misplaced_observe,
            'FAIL observe_start_actual_committed_C_entry')
        scan_begin = source.index('            #if NG2_RUNTIME_HOST_TEST\n            let analysisRGBA = NG2RuntimeTestHooks.analysisRGBA?')
        scan_end = source.index('            let frame = NG2Frame(',scan_begin)
        scan = source[scan_begin:scan_end]
        if scan.count('            let analyzed = analysisRGBA.withUnsafeBytes')!=1:
            raise ValueError('runtime_worker_analysis_mutation_target')
        # Activate this fault only for the controlled analysis hook. Earlier
        # MOVE setup still scans on its worker, so it cannot deadlock the capture
        # boundary used to align an unrelated fixture's original dispatch time.
        synchronous_scan = ('            let scanFrame: () -> Int32 = {\n'
            + ''.join('    '+line for line in scan.replace(
                '            let analyzed = analysisRGBA.withUnsafeBytes',
                '            return analysisRGBA.withUnsafeBytes').splitlines(keepends=True))
            + '            }\n'
            + '            let analyzed: Int32 = NG2RuntimeTestHooks.analysisRGBA != nil ? controlQueue.sync(execute: scanFrame) : scanFrame()\n')
        mutations['worker-analysis'] = (scan,synchronous_scan,'FAIL pure_analysis_hold_does_not_block_final_MOVE')
        # Exercise the new placement proof and the cases not completed by the
        # previous Mac run before the remaining established mutant inventory.
        first_mutations = ['observe-start-placement', 'dispatch-failure-first',
            'dispatch-failure-generation', 'dispatch-failure-command',
            'dispatch-failure-query-start', 'motion-clock', 'worker-analysis']
        for label in first_mutations:
            old, new, expected = mutations.pop(label)
            print('Runtime mutation: '+label, flush=True)
            if source.count(old)!=1: raise ValueError('runtime_mutation_target: '+label)
            (stage/'NG2Runtime.swift').write_text(source.replace(old,new))
            result = compile_run(sources, stage/(label+'-tests'), output, 'runtime-'+label+'-mutation-red', extra, run_timeout=120)
            require_red(result, expected); reds[label]=result.stdout.strip()
            print('Runtime mutation observed: '+label+' / '+result.stdout.strip().splitlines()[-1], flush=True)
        ownership = '        guard ownsTicket(run, command, generation: generation) else { return }'
        if source.count(ownership) != 1: raise ValueError('runtime_stale_entry_mutation_target')
        (stage/'NG2Runtime.swift').write_text(source.replace(ownership, '// mutation: stale callback early ownership removed'))
        print('Runtime mutation: stale-entry', flush=True)
        result = compile_run(sources, stage/'stale-entry-tests', output, 'runtime-stale-entry-mutation-red', extra, run_timeout=120)
        require_red(result, 'FAIL replan_stale_callback_skips_final_authority_hook')
        reds['stale-entry'] = result.stdout.strip()
        print('Runtime mutation observed: stale-entry / '+result.stdout.strip().splitlines()[-1], flush=True)
        print('Runtime mutation: final-query', flush=True)
        (stage/'NG2Runtime.swift').write_text(final_query_source)
        result = compile_run(sources, stage/'final-query-tests', output, 'runtime-final-query-mutation-red', extra, run_timeout=120)
        require_red(result, 'FAIL move_foreground_prepared_before_final_callback_is_offered')
        reds['final-query'] = result.stdout.strip()
        print('Runtime mutation observed: final-query / '+result.stdout.strip().splitlines()[-1], flush=True)
        # Both final-stage exclusions independently stop a generation-only stale
        # callback. Remove them together to exercise the actual no-synth contract.
        generation_owner = 'run.mainCommandID == command.id && run.generation == generation'
        generation_gate = 'expectedGeneration: generation, currentGeneration: run.generation'
        if source.count(generation_owner)!=1 or source.count(generation_gate)!=1:
            raise ValueError('runtime_final_generation_mutation_target')
        generation_mutation = source.replace(generation_owner, 'run.mainCommandID == command.id').replace(
            generation_gate,'expectedGeneration: generation, currentGeneration: generation')
        print('Runtime mutation: final-generation', flush=True)
        (stage/'NG2Runtime.swift').write_text(generation_mutation)
        result = compile_run(sources, stage/'final-generation-tests', output,
            'runtime-final-generation-mutation-red', extra, run_timeout=120)
        require_red(result, 'FAIL final_generation_only_revocation_prevents_synth')
        reds['final-generation'] = result.stdout.strip()
        print('Runtime mutation observed: final-generation / '+result.stdout.strip().splitlines()[-1], flush=True)
        # Mutate the actual core assessment reference while retaining production
        # Runtime behavior. Only staged code and its existing staged object change;
        # restoring the exact original object also keeps later contracts independent.
        (stage/'NG2Runtime.swift').write_text(source)
        controller = (native/'NG2Controller.c').read_text()
        old = 'if(e){e->observed_capture_id=id;e->motion=motion.kind;'
        new = ('if(e){if(motion.kind!=NG2_MOTION_UNKNOWN&&motion.kind!=NG2_TWEEN)'
               'e->observed_capture_id=id;e->motion=motion.kind;')
        if controller.count(old) != 1: raise ValueError('runtime_motion_reference_mutation_target')
        controller_objects = [path for path in objects if path.name == 'NG2Controller.o']
        if len(controller_objects) != 1: raise ValueError('runtime_controller_object_target')
        controller_object = controller_objects[0]
        original_object = controller_object.read_bytes()
        (stage/'NG2Controller.c').write_text(controller.replace(old, new))
        print('Runtime mutation: motion-reference', flush=True)
        try:
            built = subprocess.run(['clang', '-std=c11', *native_object_flags('NG2Controller.c'), '-I', str(native),
                '-c', str(stage/'NG2Controller.c'), '-o', str(controller_object)],
                capture_output=True, text=True, timeout=120)
            (output/'runtime-motion-reference-C-compile.txt').write_text(built.stdout+built.stderr)
            checked(built)
            result = compile_run(sources, stage/'motion-reference-tests', output,
                'runtime-motion-reference-mutation-red', extra, run_timeout=120)
            require_red(result, 'FAIL motion_first_UNKNOWN_frame_pinned_beyond_recent_window')
            reds['motion-reference'] = result.stdout.strip()
            print('Runtime mutation observed: motion-reference / '+result.stdout.strip().splitlines()[-1], flush=True)
        finally:
            controller_object.write_bytes(original_object)
        for label,(old,new,expected) in mutations.items():
            print('Runtime mutation: '+label, flush=True)
            if source.count(old)!=1: raise ValueError('runtime_mutation_target: '+label)
            (stage/'NG2Runtime.swift').write_text(source.replace(old,new))
            result = compile_run(sources, stage/(label+'-tests'), output, 'runtime-'+label+'-mutation-red', extra, run_timeout=120)
            require_red(result, expected); reds[label]=result.stdout.strip()
            print('Runtime mutation observed: '+label+' / '+result.stdout.strip().splitlines()[-1], flush=True)
        if len(reds) != 32:
            raise RuntimeError('runtime_expected_32_named_mutation_reds')
    baseline_count = len(reds)
    # TEST051 faults use only their public fixtures. Their entry conditions
    # include two actual MOVEs and exact image budgets; earlier fixtures must
    # not mask a broken continuous callback or cached-reply gate.
    (stage/'main.swift').write_text(test051_public_fixture_source(all_tests))
    new_mutations = {
        'continuous-command-id': (
            'run.lock.ng2Locked { run.mainCommandID == command.id && run.generation == generation }',
            'run.lock.ng2Locked { (run.report["moves"]?.intValue ?? 0) >= 2 || (run.mainCommandID == command.id && run.generation == generation) }',
            'FAIL continuous_old_command_skips_authority_and_touches'),
        'continuous-return-bookkeeping': (
            'run.lock.ng2Locked { run.mainCallbacks.remove(command.id) }',
            'run.lock.ng2Locked { run.mainCallbacks.remove(command.id); if command.ordinal >= 3 && command.id != run.mainCommandID && (run.report["moves"]?.intValue ?? 0) >= 2 && (run.report["events"]?.arrayValue ?? []).contains(where: { $0.objectValue?["id"]?.intValue == Int(command.id) && $0.objectValue?["outcome"]?.intValue == 3 && $0.objectValue?["begin_ns"]?.intValue == 0 }) { run.mainCommandID = 0 } }',
            'FAIL continuous_old_return_keeps_replacement_ownership'),
        'continuous-callback-drain': (
            'mainOutstanding: run.mainOutstanding, legacyCaptures: legacy)',
            'mainOutstanding: (run.report["moves"]?.intValue ?? 0) >= 2 ? false : run.mainOutstanding, legacyCaptures: legacy)',
            'FAIL continuous_stale_callback_retains_lease_and_blocks_manifest'),
        'continuous-details-connection': (
            '"scene_change_details": .array(encodedDetails)',
            '"scene_change_details": .array([])',
            'FAIL continuous_revalidation_actual_detail_producer'),
        'export-manifest-reply-owner': (
            'guard exportEligibleLocked(run, generation: generation), run.exportCache?.id == id else {',
            'guard current === run, run.exportCache?.id == id else {',
            'FAIL paged_cached_manifest_reply_rechecks_auth_owner'),
        'export-manifest-reply-current': (
            'guard exportEligibleLocked(run, generation: generation), run.exportCache?.id == id else {',
            'guard (current !== run ? (ownerActive(run) && generation == run.generation) : (exportEligibleLocked(run, generation: generation) && run.exportCache?.id == id)) else {',
            'FAIL paged_cached_manifest_reply_rechecks_current_run'),
        'export-chunk-reply-owner': (
            'guard exportEligibleLocked(run, generation: generation), run.exportCache?.id == exportID else {',
            'guard current === run, run.exportCache?.id == exportID else {',
            'FAIL paged_cached_chunk_reply_rechecks_auth_owner'),
        'export-chunk-reply-current': (
            'guard exportEligibleLocked(run, generation: generation), run.exportCache?.id == exportID else {',
            'guard (current !== run ? (ownerActive(run) && generation == run.generation) : (exportEligibleLocked(run, generation: generation) && run.exportCache?.id == exportID)) else {',
            'FAIL paged_cached_chunk_reply_rechecks_current_run'),
        'export-chunk-offset': (
            '"capture_id": .int(captureID), "offset": .int(offset)',
            '"capture_id": .int(captureID), "offset": .int(0)',
            'FAIL paged_chunk_identity_offset_and_digest_bound'),
        'export-parallel-build': (
            'guard run.exportBuildID == nil else { return .busy }',
            '// mutation: an overlapping manifest build may replace the active token',
            'FAIL paged_parallel_build_and_new_run_do_not_amplify_cache'),
        'export-per-image-boundary': (
            'if bytes.count > 512 * 1024 || total + bytes.count > 4 * 1024 * 1024 { continue }',
            'if bytes.count >= 512 * 1024 || total + bytes.count > 4 * 1024 * 1024 { continue }',
            'FAIL paged_exact_per_image_aggregate_and_image_count_budget_524288'),
        'export-total-boundary': (
            'if bytes.count > 512 * 1024 || total + bytes.count > 4 * 1024 * 1024 { continue }',
            'if bytes.count > 512 * 1024 || total + bytes.count >= 4 * 1024 * 1024 { continue }',
            'FAIL paged_exact_per_image_aggregate_and_image_count_budget_524288'),
        'export-selection-count': (
            'return Array(frames.prefix(20))',
            'return Array(frames.prefix(21))',
            'FAIL paged_24_retained_frames_select_only_original_20_image_budget'),
        'export-manifest-immutable': (
            'return (manifest, nil)',
            'var refreshed = manifest; if (run.report["moves"]?.intValue ?? 0) == 0 { var snapshot = manifest["report"]?.objectValue ?? [:]; snapshot["device_now_ns"] = number(Self.now()); refreshed["report"] = .object(snapshot) }; return (refreshed, nil)',
            'FAIL paged_cached_manifest_is_immutable_including_report'),
        'export-stale-generation-cache': (
            'return allowed && (generation == nil || generation == run.generation)',
            'if generation != nil && generation != run.generation { run.exportCache = nil }; return allowed && (generation == nil || generation == run.generation)',
            'FAIL paged_late_old_generation_reply_preserves_new_export_cache'),
        'export-retired-raw-storage': (
            'old.images.removeAll(); old.pinned.removeAll()\n                        old.initial = nil; old.found = nil; old.latest = nil',
            '// mutation: old rasters remain retained across replacement',
            'FAIL paged_replacement_retires_previous_raw_and_encoded_storage'),
    }
    if new052_mutations_only or new053_mutations_only:
        new_mutations = {}
    for label, (old, new, expected) in new_mutations.items():
        print('Runtime mutation: '+label, flush=True)
        if source.count(old) != 1:
            raise ValueError('runtime_test051_mutation_target: '+label)
        (stage/'NG2Runtime.swift').write_text(source.replace(old, new))
        result = compile_run(sources, stage/(label+'-tests'), output,
            'runtime-'+label+'-mutation-red', extra, run_timeout=120)
        require_red(result, expected); reds[label] = result.stdout.strip()
        print('Runtime mutation observed: '+label+' / '+result.stdout.strip().splitlines()[-1], flush=True)
    if len(reds) != baseline_count + len(new_mutations):
        raise RuntimeError('runtime_expected_baseline_and_test051_named_mutation_reds')
    target_mutations = {} if new051_mutations_only or new053_mutations_only else {
        'target-drift-after-action': (
            '!same_continuous_action(&before,&after)', '!same_choice(&before,&after)',
            'FAIL target_drift_revalidation_follows_two_actual_confirmed_moves'),
        'target-drift-pending-action': (
            '!same_continuous_action(&choice,&p->command_choice)', '!same_choice(&choice,&p->command_choice)',
            'FAIL target_drift_revalidation_follows_two_actual_confirmed_moves'),
    }
    controller = (native/'NG2Controller.c').read_text()
    target_mutation_sources = {}
    if target_mutations:
        (stage/'main.swift').write_text(test052_public_fixture_source(all_tests))
        (stage/'NG2Runtime.swift').write_text(source)
        controller_objects = [path for path in objects if path.name == 'NG2Controller.o']
        if len(controller_objects) != 1:
            raise ValueError('runtime_test052_controller_object_target')
        controller_object = controller_objects[0]
        original_object = controller_object.read_bytes()
        try:
            for label, (old, new, expected) in target_mutations.items():
                if controller.count(old) != 1:
                    raise ValueError('runtime_test052_action_mutation_target: '+label)
                mutated_controller = controller.replace(old, new)
                (stage/'NG2Controller.c').write_text(mutated_controller)
                print('Runtime mutation: '+label, flush=True)
                built = subprocess.run(['clang', '-std=c11', *native_object_flags('NG2Controller.c'),
                    '-I', str(native), '-c', str(stage/'NG2Controller.c'), '-o', str(controller_object)],
                    capture_output=True, text=True, timeout=120)
                (output/('runtime-'+label+'-C-compile.txt')).write_text(built.stdout+built.stderr)
                checked(built)
                result = compile_run(sources, stage/(label+'-tests'), output,
                    'runtime-'+label+'-mutation-red', extra, run_timeout=120)
                require_red(result, expected); reds[label] = result.stdout.strip()
                target_mutation_sources[label] = hashlib.sha256(mutated_controller.encode()).hexdigest()
                print('Runtime mutation observed: '+label+' / '+result.stdout.strip().splitlines()[-1], flush=True)
        finally:
            controller_object.write_bytes(original_object)
    if len(reds) != baseline_count + len(new_mutations) + len(target_mutations):
        raise RuntimeError('runtime_expected_baseline_test051_test052_named_mutation_reds')
    startup_mutations = {} if new051_mutations_only or new052_mutations_only else {
        'initial-slot-early-publication': (
            'if(p->initial_slot_not_before-now>INITIAL_PUBLICATION)return 0;',
            '/* mutation: initial ticket published before its bounded preparation window */',
            'FAIL startup_publication_waits_for_latest_three_changes_without_replan_budget'),
        'initial-slot-missing-preparation-margin': (
            'ng2_next_target(&p->model,now,p->s.lead_ns+INITIAL_PREPARATION)',
            'ng2_next_target(&p->model,now,p->s.lead_ns)',
            'FAIL startup_first_slot_reserves_foreground_preparation_margin'),
    }
    startup_mutation_sources = {}
    if startup_mutations:
        (stage/'main.swift').write_text(test053_public_fixture_source(all_tests))
        (stage/'NG2Runtime.swift').write_text(source)
        controller_objects = [path for path in objects if path.name == 'NG2Controller.o']
        if len(controller_objects) != 1:
            raise ValueError('runtime_test053_controller_object_target')
        controller_object = controller_objects[0]
        original_object = controller_object.read_bytes()
        try:
            for label, (old, new, expected) in startup_mutations.items():
                if controller.count(old) != 1:
                    raise ValueError('runtime_test053_initial_slot_mutation_target: '+label)
                mutated_controller = controller.replace(old, new)
                (stage/'NG2Controller.c').write_text(mutated_controller)
                print('Runtime mutation: '+label, flush=True)
                built = subprocess.run(['clang', '-std=c11', *native_object_flags('NG2Controller.c'),
                    '-I', str(native), '-c', str(stage/'NG2Controller.c'), '-o', str(controller_object)],
                    capture_output=True, text=True, timeout=120)
                (output/('runtime-'+label+'-C-compile.txt')).write_text(built.stdout+built.stderr)
                checked(built)
                result = compile_run(sources, stage/(label+'-tests'), output,
                    'runtime-'+label+'-mutation-red', extra, run_timeout=120)
                require_red(result, expected); reds[label] = result.stdout.strip()
                startup_mutation_sources[label] = hashlib.sha256(mutated_controller.encode()).hexdigest()
                print('Runtime mutation observed: '+label+' / '+result.stdout.strip().splitlines()[-1], flush=True)
        finally:
            controller_object.write_bytes(original_object)
    if len(reds) != baseline_count + len(new_mutations) + len(target_mutations) + len(startup_mutations):
        raise RuntimeError('runtime_expected_baseline_test051_test052_test053_named_mutation_reds')
    (stage/'NG2Runtime.swift').write_text(source)
    (stage/'main.swift').write_text(all_tests)
    return {'production_green':green.stdout.strip(),'mutation_red':reds,'compiled':True,
            'baseline_mutation_count': baseline_count, 'test051_mutation_count': len(new_mutations),
            'test052_mutation_count': len(target_mutations),
            'test053_mutation_count': len(startup_mutations),
            'test053_controller_sha256': hashlib.sha256(controller.encode()).hexdigest(),
            'test053_mutation_controller_sha256': startup_mutation_sources,
            'test052_controller_sha256': hashlib.sha256(controller.encode()).hexdigest(),
            'test052_mutation_controller_sha256': target_mutation_sources,
            'mutation_selection': 'test051_only' if new051_mutations_only else 'test052_only' if new052_mutations_only else 'test053_only' if new053_mutations_only else 'all_52',
            'native_object_flags': {path.name: native_object_flags(path.name) for path in sorted(native.glob('NG2*.c'))},
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
        (output/(label+'-compile.txt')).write_text(built.stdout+built.stderr);checked(built)
        result=subprocess.run([str(target.resolve())],capture_output=True,text=True,timeout=30)
        (output/(label+'-tests.txt')).write_text(result.stdout+result.stderr);return result
    green=run('daemon-production-green');checked(green)
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
    parser.add_argument('--raster-red-only', action='store_true')
    parser.add_argument('--test047-red-only', action='store_true')
    parser.add_argument('--test048-red-only', action='store_true')
    parser.add_argument('--test050-red-only', action='store_true')
    parser.add_argument('--test051-red-only', action='store_true')
    parser.add_argument('--test051-public-only', action='store_true')
    parser.add_argument('--test051-runtime-only', action='store_true')
    parser.add_argument('--test051-new-mutations-only', action='store_true')
    parser.add_argument('--test051-selected-mutations', choices=['stale-entry'])
    parser.add_argument('--test052-public-only', action='store_true')
    parser.add_argument('--test052-new-mutations-only', action='store_true')
    parser.add_argument('--test053-public-only', action='store_true')
    parser.add_argument('--test053-new-mutations-only', action='store_true')
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    if args.test051_red_only or args.test051_public_only or args.test051_runtime_only or args.test051_new_mutations_only or args.test051_selected_mutations is not None or args.test052_public_only or args.test052_new_mutations_only or args.test053_public_only or args.test053_new_mutations_only:
        if sum((args.test051_red_only, args.test051_public_only, args.test051_runtime_only, args.test051_new_mutations_only, args.test051_selected_mutations is not None, args.test052_public_only, args.test052_new_mutations_only, args.test053_public_only, args.test053_new_mutations_only)) != 1 or args.red_only or args.raster_red_only or args.test047_red_only or args.test048_red_only or args.test050_red_only or len(args.paths) != 2:
            parser.error('TEST051 standalone mode requires fixed upstream and output directory')
        upstream, output = args.paths
        output.mkdir(parents=True, exist_ok=True)
        (output/'api').mkdir(exist_ok=True)
        (output/'raster').mkdir(exist_ok=True)
        types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('rpc_types_boundary')
        (output/'api/RPCTypes.swift').write_text(types[0])
        native = HERE/'ngg2'
        if args.test051_red_only:
            native = output/'test050-native-baseline'
            native.mkdir(exist_ok=True)
            # Freeze C/header/helpers too, avoiding an old/new hybrid proof.
            for name in ('NG2Core.h', 'NG2Controller.h', 'NG2Templates.h', 'NG2Perception.c',
                         'NG2Navigation.c', 'NG2Beat.c', 'NG2Controller.c', 'NG2Ticket.swift',
                         'NG2Raster.swift', 'NG2Runtime.swift'):
                data = subprocess.check_output(['git', 'show', TEST050_RUNTIME_COMMIT+
                    ':patches/loopctrl/ngg2/'+name], cwd=HERE)
                (native/name).write_bytes(data)
        flags = {}
        for source in sorted(native.glob('NG2*.c')):
            flags[source.name] = native_object_flags(source.name)
            result = subprocess.run(['clang', '-std=c11', *flags[source.name],
                '-I', str(native), '-c', str(source),
                '-o', str(output/'raster'/(source.stem+'.o'))], capture_output=True, text=True, timeout=120)
            (output/(source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            checked(result)
        if len(flags) != 4:
            raise ValueError('native_C_source_set')
        report = {'runtime': runtime_contract(upstream, output, expect_manifest_red=args.test051_red_only,
                      public051_only=args.test051_public_only, new051_mutations_only=args.test051_new_mutations_only,
                      selected_mutations=args.test051_selected_mutations, baseline_native=native,
                      public052_only=args.test052_public_only, new052_mutations_only=args.test052_new_mutations_only,
                      public053_only=args.test053_public_only, new053_mutations_only=args.test053_new_mutations_only),
                  'native_object_flags': flags, 'device_test': 'not_run'}
        (output/'ngg2-swift-contract.json').write_text(json.dumps(report, indent=2)+'\n')
        print(report['runtime'].get('baseline_red', report['runtime'].get('production_green')))
        return
    elif args.test050_red_only:
        if args.red_only or args.raster_red_only or args.test047_red_only or args.test048_red_only or len(args.paths) != 2:
            parser.error('--test050-red-only requires fixed upstream and output directory')
        upstream, output = args.paths
        output.mkdir(parents=True, exist_ok=True)
        (output/'api').mkdir(exist_ok=True)
        (output/'raster').mkdir(exist_ok=True)
        types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('rpc_types_boundary')
        (output/'api/RPCTypes.swift').write_text(types[0])
        native = HERE/'ngg2'
        flags = {}
        for source in sorted(native.glob('NG2*.c')):
            flags[source.name] = native_object_flags(source.name, test049=True)
            result = subprocess.run(['clang', '-std=c11', *flags[source.name],
                '-I', str(native), '-c', str(source),
                '-o', str(output/'raster'/(source.stem+'.o'))], capture_output=True, text=True, timeout=120)
            (output/(source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            checked(result)
        if len(flags) != 4:
            raise ValueError('native_C_source_set')
        report = {'runtime': runtime_contract(upstream, output, expect_observe_red=True),
                  'native_object_flags': flags, 'device_test': 'not_run'}
        (output/'ngg2-swift-contract.json').write_text(json.dumps(report, indent=2)+'\n')
        print(report['runtime']['baseline_red'])
        return
    elif args.test048_red_only:
        if args.red_only or args.raster_red_only or args.test047_red_only or len(args.paths)!=2:
            parser.error('--test048-red-only requires fixed upstream and output directory')
        upstream,output=args.paths
        output.mkdir(parents=True,exist_ok=True)
        (output/'api').mkdir(exist_ok=True)
        (output/'raster').mkdir(exist_ok=True)
        types=(upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n',1)
        if len(types)!=2:raise ValueError('rpc_types_boundary')
        (output/'api/RPCTypes.swift').write_text(types[0])
        native=HERE/'ngg2'
        for source in sorted(native.glob('NG2*.c')):
            result=subprocess.run(['clang','-std=c11','-O2',
                *(STRICT_PERCEPTION_FP if source.name == 'NG2Perception.c' else []),'-I',str(native),'-c',str(source),
                '-o',str(output/'raster'/(source.stem+'.o'))],capture_output=True,text=True,timeout=120)
            (output/(source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            checked(result)
        report={'runtime':runtime_contract(upstream,output,expect_dispatch_red=True),'device_test':'not_run'}
        (output/'ngg2-swift-contract.json').write_text(json.dumps(report,indent=2)+'\n')
        print(report['runtime']['baseline_red'])
        return
    elif args.test047_red_only:
        if args.red_only or args.raster_red_only or len(args.paths)!=2:
            parser.error('--test047-red-only requires fixed upstream and output directory')
        upstream,output=args.paths
        output.mkdir(parents=True,exist_ok=True)
        (output/'api').mkdir(exist_ok=True)
        types=(upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n',1)
        if len(types)!=2:raise ValueError('rpc_types_boundary')
        (output/'api/RPCTypes.swift').write_text(types[0])
        report={'raster':raster_contract(None,output,expect_native_red=True),
                'runtime':runtime_contract(upstream,output,expect_capture_red=True),'device_test':'not_run'}
        (output/'ngg2-swift-contract.json').write_text(json.dumps(report,indent=2)+'\n')
        print(report['raster']['baseline_red'])
        print(report['raster']['detailed_baseline_red'])
        print(report['runtime']['baseline_red'])
        return
    elif args.raster_red_only:
        if args.red_only or len(args.paths) != 1:
            parser.error('--raster-red-only requires output directory')
        output = args.paths[0]
        report = raster_contract(None, output, expect_red=True)
        report['device_test'] = 'not_run'
        (output / 'ngg2-swift-contract.json').write_text(json.dumps(report, indent=2)+'\n')
        print(report['baseline_red'])
        return
    elif args.red_only:
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
        checked(observed)
        if not observed.stdout.startswith('PASS 26 pure Swift ticket/drain/heartbeat/authority contracts;') or observed.stderr:
            raise RuntimeError('missing_production_green')
        old = '&& !cancelled && ownerActive && foreground && !locked'
        if source.count(old) != 1: raise ValueError('ticket_mutation_target')
        mutation = execute(source.replace(old, '&& ownerActive && foreground && !locked'), output, 'ticket-mutation-red')
        require_red(mutation)
        boundary = 'now - start <= 1_000_000_000'
        if source.count(boundary) != 1: raise ValueError('authority_freshness_mutation_target')
        authority_mutation = execute(source.replace(boundary, 'now - start < 1_000_000_000'), output, 'authority-boundary-mutation-red')
        require_red(authority_mutation, 'FAIL authority_query_boundary_inclusive')
        report = {'production_green': {'compiled': True, 'returncode': 0,
                  'observed': observed.stdout.strip()}, 'baseline_red': baseline.stdout.strip(),
                  'ticket_mutation_red': mutation.stdout.strip(),
                  'authority_freshness_mutation_red': authority_mutation.stdout.strip(),
                  'api': api_contract(upstream, output), 'raster': raster_contract(upstream, output),
                  'perception_profile': perception_profile_contract(upstream, output),
                  'navigation_profile': navigation_profile_contract(upstream, output),
                  'runtime': runtime_contract(upstream, output), 'daemon':capture_contract(upstream, output),
                  'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((upstream/'LoopCtrlUITests').glob('NG2*')) if p.is_file()},
                  'device_test': 'not_run'}
    (output / 'ngg2-swift-contract.json').write_text(json.dumps(report, indent=2)+'\n')
    print(observed.stdout, end='')


if __name__ == '__main__':
    main()
