#!/usr/bin/env python3
"""One TEST120 PARTIAL begin/dispatch boundary, two public-RGBA Mac subruns."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'partial_begin_dispatch'
SUBRUNS = ('normal', 'post_guard_late')
SCHEMA = 'ngg2-runtime120-partial-begin-v1'
RUNTIME_SHA256 = '58c6de6535dbe204e0e9ae39958a5e4c0edfc80a92a428e5b29cb0843d44a420'
FAKES_SHA256 = '2ff67987e157314eef4c7ad551d9c48021a0a5caa33051d463b80c37b24465bb'
NATIVE = ('NG2Beat.c', 'NG2Controller.c', 'NG2Navigation.c', 'NG2Perception.c',
          'NG2Ring.c', 'NG2RingKernel/observe.c', 'NG2RingKernel/icon.c', 'NG2RingKernel/word.c')
HELPERS = ('NG2CycleWire.swift', 'NG2CycleSpool.swift', 'NG2CycleExport.swift')
FIXTURES = ('check_runtime120.py', 'ngg2_runtime120_tests.swift',
            'ngg2_runtime120_partial_fixture.c', 'ngg2_runtime120_partial_fixture.h',
            'generate_shop120_partial_pixels.py', 'ngg2_runtime_fakes.swift',
            'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h')
HOST_ALIASES = ('test120PartialBeginDispatch', 'NG2Runtime120Owner', 'NG2Runtime120Evidence',
                'retainPartial120Setup', 'counts120', 'sceneHash120', 'require120', 'pump120')
CONTROLLER_MACROS = ('-Dng2_motion=ng2_runtime120_motion',
    '-Dng2_controller_tick=ng2_runtime120_real_tick',
    '-Dng2_controller_begin=ng2_runtime120_real_begin',
    '-Dng2_controller_complete=ng2_runtime120_real_complete',
    '-Dng2_controller_preparation_epoch=ng2_runtime120_real_epoch')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def require(value, message):
    if not value:
        raise ValueError(message)


def fixture_source():
    """Reader-facing source inventory: production is not rewritten by this seam."""
    return (HERE/'ngg2_runtime120_tests.swift').read_text()


def source_binding(upstream):
    manifest = json.loads((HERE/'ngg2-manifest.json').read_bytes())
    sealed = {name: row['patched_sha256'] for name, row in manifest['files'].items()}
    sealed.update({name: row['sha256'] for name, row in manifest['additions'].items()})
    require(len(sealed) == 37, 'TEST120 complete installed native inventory must contain37 files')
    actual = {name: digest(upstream/name) for name in sealed}
    require(actual == sealed, 'TEST120 installed native37 differs from manifest')
    for name, row in manifest['additions'].items():
        source = ROOT/'tools/ring_native'/row['source'] if row.get('source_root') == 'ring_native' else HERE/'ngg2'/row['source']
        require(digest(source) == actual[name], 'TEST120 installed addition differs from driver: '+name)
    require(actual['LoopCtrlUITests/NG2Runtime.swift'] == RUNTIME_SHA256,
            'TEST120 original Runtime body must remain byte-identical')
    require(digest(HERE/'ngg2_runtime_fakes.swift') == FAKES_SHA256,
            'TEST120 shared fakes must remain byte-identical')
    code = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    return dict(driver_commit=code, native_manifest_sha256=digest(HERE/'ngg2-manifest.json'),
                native_source_sha256=actual, runtime_body_sha256=RUNTIME_SHA256,
                fixture_source_sha256={name: digest(HERE/name) for name in FIXTURES})


def validate_subrun(value, variant):
    """Pure receipt reader: no build, generator, classifier, or callbacks."""
    require(type(value) is dict and value.get('schema') == 'ngg2-runtime120-subrun-v1'
        and value.get('case') == CASE and value.get('variant') == variant and variant in SUBRUNS,
        'TEST120 subrun identity')
    for key in ('normal_perception', 'normal_ring', 'actual_runtime_dispatch',
                'setup_component_known_ACK', 'all_real_workers_drained', 'lease_released', 'callback_returned'):
        require(value.get(key) is True, 'TEST120 missing affirmative evidence: '+key)
    for key in ('scene_override_used', 'result_override_used', 'physical_game_tested', 'capture_thread_started'):
        require(value.get(key) is False, 'TEST120 component scope or override: '+key)
    require(value.get('clock') == 'real-monotonic-offset0', 'TEST120 actual clock')
    positive = ('setup_entry_ns', 'setup_return_ns', 'owner_started_ns', 'accepted_started_ns',
        'original_opening_ACK', 'source_capture_id', 'current_capture_id', 'command_id',
        'command_source_capture_id', 'ordinal', 'not_before_ns', 'deadline_ns',
        'observe_motion_calls', 'begin_calls', 'begin_accepted', 'getter_calls',
        'begin_entry_ns', 'begin_exit_ns', 'complete_calls', 'complete_ns', 'ring_return_ns',
        'tick_calls', 'tick_entry_ns', 'tick_exit_ns', 'scheduled_ns', 'main_hook_ns')
    require(all(type(value.get(key)) is int and value[key] > 0 for key in positive), 'TEST120 positive scalar evidence')
    require(all(type(value.get(key)) is int and value[key] >= 0 for key in
        ('begin_motion_calls', 'getter_motion_calls', 'getter_cost_ns', 'normal_motion_cost_ns',
         'complete_outcome', 'event_outcome', 'synth_moves', 'synth_entry_ns',
         'guard_expense_start_ns', 'guard_expense_end_ns')), 'TEST120 nonnegative counters/costs')
    require(type(value.get('assessment_sha256')) is str and len(value['assessment_sha256']) == 64
        and all(c in '0123456789abcdef' for c in value['assessment_sha256']), 'TEST120 actual assessment identity')
    require(value['owner_started_ns'] == value['accepted_started_ns'] == value['setup_entry_ns']
        and value['setup_entry_ns'] <= value['setup_return_ns'] <= value['begin_entry_ns'], 'TEST120 setup chronology')
    require(value['not_before_ns'] <= value['begin_entry_ns'] <= value['deadline_ns']
        and value['begin_entry_ns'] <= value['begin_exit_ns'] <= value['complete_ns']
        and 0 < value['deadline_ns']-value['not_before_ns'] <= 10_000_000, 'TEST120 original begin window')
    require(value['begin_calls'] == value['begin_accepted'] == value['complete_calls'] == 1
        and value.get('begin_motion_calls') == 0 and value.get('getter_motion_calls') == 0,
        'TEST120 no repeated Motion at true begin/getter')
    require(value.get('ring_mode') == 2 and value.get('ring_status') == 0 and value.get('ring_outcome') == 0,
        'TEST120 normal target-only Ring UNKNOWN')
    require(value['source_capture_id'] < value['command_source_capture_id'] < value['current_capture_id']
        and value['original_opening_ACK'] < value['command_id'], 'TEST120 original anchor/new current roles')
    frames = value.get('frames'); require(type(frames) is list and len(frames) >= 4, 'TEST120 normal frames')
    by_id = {}
    for row in frames:
        require(type(row) is dict and all(type(row.get(key)) is int and row[key] >= 0 for key in
            ('id', 'start_ns', 'end_ns', 'analysis_start_ns', 'analysis_end_ns', 'prefix', 'generation', 'state', 'goods')),
            'TEST120 frame metadata')
        require(row['id'] > 0 and row['id'] not in by_id and row['generation'] == 1
            and row['start_ns'] <= row['end_ns'] <= row['analysis_start_ns'] <= row['analysis_end_ns']
            and all(type(row.get(key)) is str and len(row[key]) == 64
                and all(c in '0123456789abcdef' for c in row[key]) for key in ('raw_sha256', 'scene_sha256')),
            'TEST120 immutable frame identity')
        by_id[row['id']] = row
    for capture in (value['source_capture_id'], value['command_source_capture_id'], value['current_capture_id']):
        require(capture in by_id and by_id[capture]['goods'] == 1 and by_id[capture]['state'] == 2,
                'TEST120 exact PARTIAL sources exist')
    anchor, current = by_id[value['source_capture_id']], by_id[value['current_capture_id']]
    command_source = by_id[value['command_source_capture_id']]
    require(value['tick_calls'] == 1 and command_source['analysis_end_ns'] <= value['tick_entry_ns']
        <= value['tick_exit_ns'] <= value['scheduled_ns'] < value['not_before_ns']
        <= value['main_hook_ns'] <= value['begin_entry_ns']
        and value.get('cost_accounting') == 'nested-real-clock-intervals-not-an-additive-total',
        'TEST120 actual tick/preparation/main cost intervals')
    observations = value.get('observations')
    require(type(observations) is list, 'TEST120 actual observe cost intervals')
    observed = set()
    for observation in observations:
        require(type(observation) is dict and all(type(observation.get(key)) is int and observation[key] > 0
            for key in ('id', 'observe_start_ns', 'observe_end_ns')), 'TEST120 observe scalar chronology')
        capture = observation['id']
        require(capture in by_id and capture not in observed and capture >= anchor['id']
            and by_id[capture]['analysis_end_ns'] <= observation['observe_start_ns']
            <= observation['observe_end_ns'] <= value['begin_entry_ns'], 'TEST120 each real observe once')
        observed.add(capture)
    require(observed == {capture for capture in by_id if capture >= anchor['id']},
            'TEST120 every target source must have an actual observe interval')
    require(anchor['scene_sha256'] != current['scene_sha256']
        and current['analysis_end_ns'] <= value['begin_entry_ns'], 'TEST120 independent material/current before begin')
    worker = value.get('worker'); require(type(worker) is dict and all(type(worker.get(key)) is int and worker[key] > 0
        for key in ('job_id', 'capture_id', 'capture_start_ns', 'prefix', 'level_id',
                    'worker_started_ns', 'deadline_ns', 'parent_deadline_ns')), 'TEST120 real worker')
    require(worker['capture_id'] == anchor['id'] and worker['capture_start_ns'] == anchor['start_ns']
        and worker.get('raw_sha256') == anchor['raw_sha256'] and worker.get('scene_sha256') == anchor['scene_sha256']
        and worker['prefix'] == anchor['prefix'] == current['prefix']
        and anchor['analysis_end_ns'] <= worker['worker_started_ns'] <= value['ring_return_ns'] <= worker['deadline_ns']
        and worker['deadline_ns'] <= min(anchor['start_ns']+150_000_000, worker['worker_started_ns']+100_000_000,
                                       worker['parent_deadline_ns'])
        and value['deadline_ns'] <= worker['parent_deadline_ns'], 'TEST120 source150/worker100/frozen parent')
    if variant == 'normal':
        require(value.get('synth_moves') == 1 and value.get('complete_outcome') == 1 and value.get('event_outcome') == 2
            and value['begin_exit_ns'] <= value['deadline_ns'] and value.get('dispatch_failure') == 'none'
            and value['begin_exit_ns'] <= value['synth_entry_ns'] <= min(value['deadline_ns'], value['complete_ns'])
            and value.get('guard_expense_start_ns') == value.get('guard_expense_end_ns') == 0,
            'TEST120 future MOVE known ACK')
    else:
        start, end = value.get('guard_expense_start_ns'), value.get('guard_expense_end_ns')
        require(type(start) is int and type(end) is int and value['begin_exit_ns'] <= start < end <= value['complete_ns']
            and 11_000_000 <= end-start <= 50_000_000 and end > value['deadline_ns']
            and value.get('synth_moves') == 0 and value['synth_entry_ns'] == 0 and value.get('complete_outcome') == 0
            and value.get('event_outcome') == 3 and value.get('dispatch_failure') == 'too_late',
            'TEST120 actual post-guard expense and certain NOT_SENT')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', choices=(CASE,), default=CASE)
    args = parser.parse_args()
    require(os.uname().sysname == 'Darwin', 'TEST120 Runtime queue requires macOS; no callback assertion executed')
    for name in ('swiftc', 'clang'):
        require(shutil.which(name) is not None, name+' unavailable; no TEST120 Runtime callback executed')
    upstream = args.upstream.resolve(); native = upstream/'LoopCtrlUITests'
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    require({path.name for path in output.iterdir()} <= {'runtime-command.txt'},
            'TEST120 output must be fresh; preserve prior failure artifacts')
    binding = source_binding(upstream)
    compiler = {name: subprocess.run([name, '--version'], capture_output=True, text=True, check=True).stdout
                for name in ('swiftc', 'clang')}
    proof = dict(schema=SCHEMA, required_cases=[CASE], required_subruns=list(SUBRUNS),
        product_pass=False, compile_errors=0, production_source_binding=binding, compilers=compiler,
        scope='selected real Runtime ordinary PARTIAL preparation/begin/post guard; public procedural RGBA, normal Perception/Ring and component known ACK; real monotonic offset0; no physical game or phone speed acceptance',
        host_aliases=list(HOST_ALIASES), controller_call_routes=list(CONTROLLER_MACROS),
        shared_fakes_sha256=FAKES_SHA256, subruns={}, commands=[], compiled_sources={},
        compiled_object_sha256={}, generated_inputs={})
    try:
        with tempfile.TemporaryDirectory(prefix='runtime120-') as temporary:
            stage = Path(temporary)
            generated = output/'generated-inputs'; generated.mkdir(exist_ok=True)
            types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
            require(len(types) == 2, 'TEST120 RPCTypes declaration boundary')
            (stage/'RPCTypes.swift').write_text(types[0])
            suffix = fixture_source()
            original = (native/'NG2Runtime.swift').read_bytes()
            (stage/'NG2Runtime.swift').write_bytes(original+b'\n'+suffix.encode())
            proof['runtime_body_sha256'] = sha(original)
            proof['host_prefix_sha256'] = sha(b'')
            proof['host_suffix_sha256'] = sha(suffix.encode())
            proof['compiled_runtime_sha256'] = digest(stage/'NG2Runtime.swift')
            (stage/'main.swift').write_text('import Foundation\nlet args120 = CommandLine.arguments\n'
                'guard args120.count == 3 && args120[1] == "partial_begin_dispatch" && '
                '["normal", "post_guard_late"].contains(args120[2]) else { print("FAIL test120_unknown_case_or_variant"); exit(1) }\n'
                'NG2Runtime.shared.test120PartialBeginDispatch(args120[2])\n')
            (stage/'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
                '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_runtime120_partial_fixture.h"\n'
                'void ng2_test_pause(uint8_t *, size_t);\n')
            (stage/'pause.c').write_text('#include "NG2Core.h"\n#include "NG2Templates.h"\n#include <string.h>\n'
                'void ng2_test_pause(uint8_t *out,size_t n){if(!out||n!=896u*414u*4u)return;memset(out,0,n);'
                'for(size_t i=3;i<n;i+=4)out[i]=255;const NG2Template *ts[2]={&ng2_template_continue,&ng2_template_restart};'
                'for(int k=0;k<2;k++){const NG2Template *t=ts[k];for(int y=0;y<t->h;y++)for(int x=0;x<t->w;x++)'
                'if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1){size_t p=((t->y+y)*896u+t->x+x)*4u;'
                'out[p]=out[p+1]=out[p+2]=255;}}}\n')
            import generate_shop120_partial_pixels as pixels
            proof['pixel_generation'] = pixels.generate(stage/'runtime120_partial_pixels.h', output/'runtime120-pixel-generation.json')
            c_sources = [native/name for name in NATIVE] + [HERE/'ngg2_runtime_scene_fixtures.c',
                HERE/'ngg2_runtime120_partial_fixture.c', stage/'pause.c']
            objects = []
            object_output = output/'objects'; object_output.mkdir(exist_ok=True)
            proof['compiled_objects'] = []
            def run_compile(command, label):
                proof['commands'].append(command)
                answer = subprocess.run(command, capture_output=True, text=True, timeout=180)
                (output/(label+'-compile.txt')).write_text(answer.stdout+answer.stderr)
                if answer.returncode:
                    proof['compile_errors'] += 1
                    raise RuntimeError('TEST120 compile failure is not assertion evidence: '+label+'\n'+answer.stdout+answer.stderr)
            for index, source in enumerate(c_sources):
                obj = stage/('native-'+str(index)+'.o')
                flags = ['-O0'] if source.name in ('NG2Beat.c', 'NG2Controller.c') else ['-O2', '-fno-fast-math', '-ffp-contract=off']
                if source.name == 'NG2Controller.c':
                    flags += list(CONTROLLER_MACROS)
                run_compile(['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE), '-I', str(stage),
                             '-c', str(source), '-o', str(obj)], source.stem)
                proof['compiled_object_sha256'][str(source)] = digest(obj)
                saved = object_output/obj.name; shutil.copyfile(obj, saved)
                proof['compiled_objects'].append(dict(source=str(source), file='objects/'+obj.name, sha256=digest(saved)))
                objects.append(obj)
            swift_sources = [stage/'RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
                *(native/name for name in HELPERS), HERE/'ngg2_runtime_fakes.swift', stage/'NG2Runtime.swift', stage/'main.swift']
            executable = stage/'runtime120'
            run_compile(['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094',
                '-D', 'NG2_PREPARATION_TEST058_GREEN', '-Xcc', '-I'+str(native), '-Xcc', '-I'+str(HERE),
                '-import-objc-header', str(stage/'Bridge.h'), *map(str, swift_sources), *map(str, objects),
                '-o', str(executable)], 'runtime120-swift')
            proof['executable_sha256'] = digest(executable)
            shutil.copy2(executable, output/'runtime120-host')
            proof['executable_file'] = 'runtime120-host'
            symbol_command = ['nm', '-gUj', str(executable)]
            symbol_answer = subprocess.run(symbol_command, capture_output=True, text=True, check=True)
            (output/'runtime120-linked-symbols.txt').write_text(symbol_answer.stdout+symbol_answer.stderr)
            required_symbols = ('ng2_runtime120_real_begin', 'ng2_runtime120_real_tick',
                'ng2_runtime120_real_complete', 'ng2_runtime120_real_epoch', 'ng2_motion',
                'ng2_runtime120_motion', 'ng2_controller_create_cycle', 'ng2_controller_observe_irregular_at',
                'ng2_controller_tick', 'ng2_controller_begin', 'ng2_controller_complete',
                'ng2_controller_cycle_worker_begin', 'ng2_controller_cycle_assess', 'ng2_ring_assess_rgba')
            symbol_lines = symbol_answer.stdout.splitlines()
            require(len(required_symbols) == len(set(required_symbols)), 'TEST120 unique required symbol inventory')
            require(all(symbol_lines.count('_'+name) == 1 for name in required_symbols),
                    'TEST120 must link each real public C/Ring definition exactly once')
            proof['linked_symbols'] = dict(command=symbol_command,
                file='runtime120-linked-symbols.txt', sha256=digest(output/'runtime120-linked-symbols.txt'),
                required=list(required_symbols))
            proof['compiled_sources'] = {str(path): digest(path) for path in [*c_sources, *swift_sources]}
            for name in ('RPCTypes.swift', 'Bridge.h', 'pause.c', 'NG2Runtime.swift', 'main.swift', 'runtime120_partial_pixels.h'):
                shutil.copyfile(stage/name, generated/name)
                proof['generated_inputs']['generated-inputs/'+name] = digest(stage/name)
            for variant in SUBRUNS:
                answer = subprocess.run([str(executable), CASE, variant], capture_output=True, text=True, timeout=30)
                (output/('runtime120-'+variant+'.txt')).write_text(answer.stdout+answer.stderr)
                lines = answer.stdout.splitlines()
                rows = [json.loads(line.removeprefix('EVIDENCE TEST120 SUBRUN ')) for line in lines
                        if line.startswith('EVIDENCE TEST120 SUBRUN ')]
                require(answer.returncode == 0 and len(rows) == 1
                    and not any(line.startswith('FAIL ') for line in lines)
                    and lines[-1:] == ['PASS TEST120 CASE '+CASE+' '+variant], 'TEST120 actual subrun failed: '+variant)
                validate_subrun(rows[0], variant)
                raw = (json.dumps(rows[0], sort_keys=True, indent=2)+'\n').encode()
                filename = 'runtime120-'+variant+'-evidence.json'; (output/filename).write_bytes(raw)
                proof['subruns'][variant] = dict(returncode=answer.returncode, qualified=True,
                    evidence_file=filename, evidence_sha256=sha(raw), evidence=rows[0])
            proof['product_pass'] = tuple(proof['subruns']) == SUBRUNS
    finally:
        proof['file_inventory'] = {str(p.relative_to(output)): dict(bytes=p.stat().st_size, sha256=digest(p))
            for p in sorted(output.rglob('*')) if p.is_file() and p.name not in ('runtime120-result.json', 'runtime-command.txt')}
        proof['workflow_tee_required'] = 'runtime-command.txt'
        (output/'runtime120-result.json').write_text(json.dumps(proof, indent=2)+'\n')
    require(proof['product_pass'], 'TEST120 queue selected scope is incomplete')
    print('PASS TEST120 selected partial_begin_dispatch normal/post_guard_late actual callbacks')


if __name__ == '__main__':
    main()
