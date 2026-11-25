#!/usr/bin/env python3
"""One TEST119 Runtime queue boundary, two raw-RGBA component subruns on macOS."""
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
CASE = 'entered_current_queue'
SUBRUNS = ('normal', 'candidate')
SCHEMA = 'ngg2-runtime119-queue-proof-v1'
RUNTIME_SHA256 = '58c6de6535dbe204e0e9ae39958a5e4c0edfc80a92a428e5b29cb0843d44a420'
NATIVE = ('NG2Beat.c', 'NG2Controller.c', 'NG2Navigation.c', 'NG2Perception.c',
          'NG2Ring.c', 'NG2RingKernel/observe.c', 'NG2RingKernel/icon.c', 'NG2RingKernel/word.c')
HELPERS = ('NG2CycleWire.swift', 'NG2CycleSpool.swift', 'NG2CycleExport.swift')
FIXTURES = ('check_runtime119.py', 'ngg2_runtime119_tests.swift',
            'ngg2_runtime119_queue_fixture.c', 'ngg2_runtime119_queue_fixture.h',
            'generate_shop119_queue_pixels.py', 'ngg2_runtime_fakes.swift',
            'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h')
HOST_ALIASES = ('test119EnteredCurrentQueue', 'NG2Runtime119Evidence', 'NG2Runtime119Worker',
                'retainQueue119Setup', 'sceneHash119', 'irregularHash119', 'require119', 'pump119',
                'ng2_fixture_queue119_setup', 'ng2_fixture_queue119_prepare', 'ng2_fixture_queue119_prepared',
                'ng2_fixture_queue119_rgba', 'ng2_fixture_queue119_phase')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def require(value, message):
    if not value:
        raise ValueError(message)


def fixture_source():
    """Reader-facing source inventory: production is not rewritten by this seam."""
    return (HERE/'ngg2_runtime119_tests.swift').read_text()


def source_binding(upstream):
    manifest = json.loads((HERE/'ngg2-manifest.json').read_bytes())
    sealed = {name: row['patched_sha256'] for name, row in manifest['files'].items()}
    sealed.update({name: row['sha256'] for name, row in manifest['additions'].items()})
    require(len(sealed) == 37, 'TEST119 complete installed native inventory must contain37 files')
    actual = {name: digest(upstream/name) for name in sealed}
    require(actual == sealed, 'TEST119 installed native37 differs from manifest')
    for name, row in manifest['additions'].items():
        source = ROOT/'tools/ring_native'/row['source'] if row.get('source_root') == 'ring_native' else HERE/'ngg2'/row['source']
        require(digest(source) == actual[name], 'TEST119 installed addition differs from driver: '+name)
    require(actual['LoopCtrlUITests/NG2Runtime.swift'] == RUNTIME_SHA256,
            'TEST119 original Runtime body must remain byte-identical')
    code = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    return dict(driver_commit=code, native_manifest_sha256=digest(HERE/'ngg2-manifest.json'),
                native_source_sha256=actual, runtime_body_sha256=RUNTIME_SHA256,
                fixture_source_sha256={name: digest(HERE/name) for name in FIXTURES})


def validate_subrun(value, variant):
    """Reject missing, fabricated-result, stale-source, or incomplete queue evidence."""
    require(type(value) is dict and value.get('schema') == 'ngg2-runtime119-subrun-v1', 'TEST119 subrun schema')
    require(value.get('case') == CASE and value.get('variant') == variant, 'TEST119 selected subrun identity')
    for key in ('normal_perception', 'normal_ring', 'actual_runtime_cycle', 'new_frames_via_latest',
                'same_public_setup_bookkeeping', 'original_parent_preserved', 'old_worker_return_fences',
                'queued_immutable_until_result', 'source_identity_bound', 'cancelled',
                'all_real_workers_drained', 'lease_released', 'no_future_move_or_restart'):
        require(value.get(key) is True, 'TEST119 missing affirmative evidence: '+key)
    require(value.get('extra_input_reservations') == 0, 'TEST119 no unissued extra UI reservation')
    require(value.get('result_override_used') is False and value.get('scene_override_used') is False,
            'TEST119 classifier/Scene override forbidden')
    require(value.get('clock') == 'real-monotonic-offset0-after-earned-setup', 'TEST119 clock model')
    require(value.get('runtime_profile') == 'normal-1-1-irregular-v1'
        and value.get('yield_after_restart') is True and value.get('normal_irregular_analysis') is True,
        'TEST119 real accepted Runtime yield profile and normal irregular analysis')
    require(value.get('capture_thread_started') is False and value.get('physical_game_tested') is False,
            'TEST119 component limit must be explicit')
    frames, workers = value.get('frames'), value.get('workers')
    require(type(frames) is list and len(frames) >= 4 and type(workers) is list,
            'TEST119 actual frame/worker evidence missing')
    require(type(value.get('owner_started_ns')) is int and value['owner_started_ns'] > 0
        and value.get('accepted_started_ns') == value['owner_started_ns'], 'TEST119 same public owner/accepted start')
    require(all(type(value.get(k)) is int and value[k] > 0 for k in
        ('setup_prefix', 'setup_latest_capture_id', 'original_ack_command_id',
         'original_ack_source_capture_id', 'original_ack_source_start_ns', 'original_ack_ns',
         'original_ack_target_ns', 'before_capture_id', 'original_inputs', 'setup_public_frame_count',
         'setup_normal_units', 'setup_opened_units', 'hold_started_ns', 'parent_deadline_ns')),
        'TEST119 public earned setup binding')
    require(all(type(value.get(k)) is int for k in ('setup_entry_ns', 'setup_return_ns', 'setup_replay_actual_cost_ns'))
        and value['setup_entry_ns'] <= value['setup_return_ns']
        and value['setup_replay_actual_cost_ns'] == value['setup_return_ns']-value['setup_entry_ns'],
        'TEST119 real public setup replay expense remains on same monotonic clock')
    require(value['setup_prefix'] == value['original_ack_command_id']
        and value['hold_started_ns'] < value['parent_deadline_ns'], 'TEST119 original prefix/parent')
    by_id = {}
    for f in frames:
        require(type(f) is dict and all(type(f.get(k)) is int and f[k] >= 0 for k in
            ('id', 'start_ns', 'end_ns', 'prefix', 'generation', 'analysis_start_ns', 'analysis_end_ns')),
            'TEST119 frame metadata')
        require(f['id'] > 0 and f['start_ns'] <= f['end_ns'] <= f['analysis_end_ns']
            and f['analysis_start_ns'] <= f['analysis_end_ns'] and f['generation'] == 1,
            'TEST119 frame chronology/generation')
        require(f['id'] not in by_id and all(type(f.get(k)) is str and len(f[k]) == 64
            for k in ('raw_sha256', 'scene_sha256', 'irregular_sha256', 'tiles_sha256', 'protected_sha256')), 'TEST119 immutable frame identity')
        by_id[f['id']] = f
    require(len(workers) == (3 if variant == 'normal' else 2), 'TEST119 actual worker count')
    for w in workers:
        require(type(w) is dict and w.get('capture_id') in by_id, 'TEST119 worker original source exists')
        f = by_id[w['capture_id']]
        require(all(type(w.get(k)) is int and w[k] > 0 for k in
            ('job_id', 'capture_id', 'capture_start_ns', 'prefix', 'level_id', 'worker_started_ns',
             'deadline_ns', 'ring_return_ns', 'commit_ns', 'producer_hook_ns', 'commit_return_hook_ns')),
            'TEST119 worker scalar evidence')
        require(w['capture_start_ns'] == f['start_ns'] and w['prefix'] == f['prefix'] == value['setup_prefix']
            and w.get('generation') == f['generation'] == 1
            and w.get('raw_sha256') == f['raw_sha256'] and w.get('scene_sha256') == f['scene_sha256']
            and w.get('irregular_sha256') == f['irregular_sha256'] and f.get('irregular_kind') == 0,
            'TEST119 worker must own original RGBA/Scene/metadata')
        require(f['start_ns'] <= w['worker_started_ns'] <= w['deadline_ns'] <=
            min(f['start_ns']+150_000_000, w['worker_started_ns']+100_000_000)
            and w['worker_started_ns'] <= w['ring_return_ns'] <= w['commit_ns'] <= w['deadline_ns'],
            'TEST119 source150/worker100 actual Ring and commit cost')
        require(w.get('mode') == 2 and w.get('fast') == 1 and w.get('status') == 0
            and w.get('adopted') is True and w.get('drain_token_at_commit_return') is True
            and w.get('drain_token_at_producer_return') is True,
            'TEST119 ordinary classifier/adoption/real return token')
        require(w.get('hold_started_ns') == value['hold_started_ns']
            and type(w.get('parent_deadline_ns')) is int
            and w['worker_started_ns'] <= w['deadline_ns'] <= w['parent_deadline_ns'] <= value['parent_deadline_ns'],
            'TEST119 each worker preserves old hold and never extends original parent')
    require(all(b['job_id'] > a['job_id'] and b['worker_started_ns'] >= max(a['producer_hook_ns'], a['commit_return_hook_ns'])
                for a, b in zip(workers, workers[1:])), 'TEST119 next worker waits for real old return fences')
    require(len({w['job_id'] for w in workers}) == len(workers), 'TEST119 jobs must advance')
    require(workers[0]['outcome'] == 0, 'TEST119 early FULL requires genuine UNKNOWN')
    require(workers[1]['outcome'] == (0 if variant == 'normal' else 2)
            or (variant == 'candidate' and workers[1]['outcome'] == 1), 'TEST119 late DATA Ring outcome')
    require(value.get('late_unit_credited_once') is True and value.get('late_token_before_candidate') is True,
            'TEST119 new late-entered branch must precede candidate')
    old, new, queued = (value.get(k) for k in ('early_capture_id', 'late_capture_id', 'queued_capture_id'))
    require(type(old) is int and type(new) is int and type(queued) is int and 0 < old < new < queued,
            'TEST119 source progression')
    require(all(capture in by_id and by_id[capture].get('state') == 2 and by_id[capture].get('goods') == 2
                for capture in (old, new, queued)), 'TEST119 all target frames are normal FULL FLOOR')
    require(by_id[old]['tiles_sha256'] == by_id[new]['tiles_sha256']
        and by_id[old]['protected_sha256'] == by_id[new]['protected_sha256'] == by_id[queued]['protected_sha256']
        and by_id[new]['tiles_sha256'] != by_id[queued]['tiles_sha256']
        and by_id[old]['raw_sha256'] != by_id[new]['raw_sha256'] != by_id[queued]['raw_sha256'],
        'TEST119 late unit has zero revealed geometry and queued source has real new material')
    require(value.get('motion_proofs') == [
        dict(before=value['before_capture_id'], after=old, direction=1, kind=0, dx=0, dy=0),
        dict(before=value['before_capture_id'], after=new, direction=1, kind=1, dx=-1, dy=0),
        dict(before=new, after=queued, direction=1, kind=2, dx=0, dy=0)],
        'TEST119 public normal motion proofs must bind same raw source IDs')
    require(value.get('early_moves') == value.get('original_moves')
        and value.get('early_input_state') == 0 and value.get('early_ack_motion') == 0
        and value.get('early_ack_observed_capture_id') == old,
        'TEST119 early FULL closes real original ACK without normal-reference fallback credit')
    require(workers[0]['capture_id'] == old and workers[1]['capture_id'] == new,
            'TEST119 early/late worker source')
    if variant == 'normal':
        require(workers[2]['capture_id'] == queued and workers[2]['outcome'] == 0
            and value.get('new_queued_source_adopted') is True, 'TEST119 queued new source adoption')
    else:
        require(value.get('candidate_latched') is True and value.get('candidate_source_preserved') is True,
                'TEST119 actual pending candidate priority')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', choices=(CASE,), default=CASE)
    args = parser.parse_args()
    require(os.uname().sysname == 'Darwin', 'TEST119 Runtime queue requires macOS; no callback assertion executed')
    for name in ('swiftc', 'clang'):
        require(shutil.which(name) is not None, name+' unavailable; no TEST119 Runtime callback executed')
    upstream = args.upstream.resolve(); native = upstream/'LoopCtrlUITests'
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    binding = source_binding(upstream)
    compiler = {name: subprocess.run([name, '--version'], capture_output=True, text=True, check=True).stdout
                for name in ('swiftc', 'clang')}
    proof = dict(schema=SCHEMA, required_cases=[CASE], required_subruns=list(SUBRUNS),
        product_pass=False, compile_errors=0, production_source_binding=binding, compilers=compiler,
        scope='selected real Runtime source lease/normal Ring/producer-control return drain; public procedural RGBA and earned simulated ACK; no physical game or phone speed acceptance',
        host_aliases=list(HOST_ALIASES), subruns={}, commands=[], compiled_sources={},
        compiled_object_sha256={}, generated_inputs={})
    try:
        with tempfile.TemporaryDirectory(prefix='runtime119-') as temporary:
            stage = Path(temporary)
            generated = output/'generated-inputs'; generated.mkdir(exist_ok=True)
            types = (upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
            require(len(types) == 2, 'TEST119 RPCTypes declaration boundary')
            (stage/'RPCTypes.swift').write_text(types[0])
            suffix = fixture_source()
            original = (native/'NG2Runtime.swift').read_bytes()
            (stage/'NG2Runtime.swift').write_bytes(original+b'\n'+suffix.encode())
            proof['runtime_body_sha256'] = sha(original)
            proof['host_suffix_sha256'] = sha(suffix.encode())
            proof['compiled_runtime_sha256'] = digest(stage/'NG2Runtime.swift')
            (stage/'main.swift').write_text('import Foundation\nlet args119 = CommandLine.arguments\n'
                'guard args119.count == 3 && args119[1] == "entered_current_queue" && '
                '["normal", "candidate"].contains(args119[2]) else { print("FAIL test119_unknown_case_or_variant"); exit(1) }\n'
                'NG2Runtime.shared.test119EnteredCurrentQueue(args119[2])\n')
            (stage/'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
                '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_runtime119_queue_fixture.h"\n'
                'void ng2_test_pause(uint8_t *, size_t);\n')
            (stage/'pause.c').write_text('#include "NG2Core.h"\n#include "NG2Templates.h"\n#include <string.h>\n'
                'void ng2_test_pause(uint8_t *out,size_t n){if(!out||n!=896u*414u*4u)return;memset(out,0,n);'
                'for(size_t i=3;i<n;i+=4)out[i]=255;const NG2Template *ts[2]={&ng2_template_continue,&ng2_template_restart};'
                'for(int k=0;k<2;k++){const NG2Template *t=ts[k];for(int y=0;y<t->h;y++)for(int x=0;x<t->w;x++)'
                'if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1){size_t p=((t->y+y)*896u+t->x+x)*4u;'
                'out[p]=out[p+1]=out[p+2]=255;}}}\n')
            import generate_shop119_queue_pixels as pixels
            proof['pixel_generation'] = pixels.generate(stage/'runtime119_queue_pixels.h', output/'runtime119-pixel-generation.json')
            c_sources = [native/name for name in NATIVE] + [HERE/'ngg2_runtime_scene_fixtures.c',
                HERE/'ngg2_runtime119_queue_fixture.c', stage/'pause.c']
            objects = []
            def run_compile(command, label):
                proof['commands'].append(command)
                answer = subprocess.run(command, capture_output=True, text=True, timeout=180)
                (output/(label+'-compile.txt')).write_text(answer.stdout+answer.stderr)
                if answer.returncode:
                    proof['compile_errors'] += 1
                    raise RuntimeError('TEST119 compile failure is not assertion evidence: '+label+'\n'+answer.stdout+answer.stderr)
            for index, source in enumerate(c_sources):
                obj = stage/('native-'+str(index)+'.o')
                flags = ['-O0'] if source.name in ('NG2Beat.c', 'NG2Controller.c') else ['-O2', '-fno-fast-math', '-ffp-contract=off']
                run_compile(['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE), '-I', str(stage),
                             '-c', str(source), '-o', str(obj)], source.stem)
                proof['compiled_object_sha256'][str(source)] = digest(obj)
                objects.append(obj)
            swift_sources = [stage/'RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
                *(native/name for name in HELPERS), HERE/'ngg2_runtime_fakes.swift', stage/'NG2Runtime.swift', stage/'main.swift']
            executable = stage/'runtime119'
            run_compile(['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094',
                '-D', 'NG2_PREPARATION_TEST058_GREEN', '-Xcc', '-I'+str(native), '-Xcc', '-I'+str(HERE),
                '-import-objc-header', str(stage/'Bridge.h'), *map(str, swift_sources), *map(str, objects),
                '-o', str(executable)], 'runtime119-swift')
            proof['executable_sha256'] = digest(executable)
            symbol_command = ['nm', '-gUj', str(executable)]
            symbol_answer = subprocess.run(symbol_command, capture_output=True, text=True, check=True)
            (output/'runtime119-linked-symbols.txt').write_text(symbol_answer.stdout+symbol_answer.stderr)
            required_symbols = ('ng2_controller_create_cycle', 'ng2_controller_observe_irregular_at',
                'ng2_controller_tick', 'ng2_controller_begin', 'ng2_controller_complete',
                'ng2_controller_cycle_worker_begin', 'ng2_controller_cycle_assess', 'ng2_ring_assess_rgba')
            symbol_lines = symbol_answer.stdout.splitlines()
            require(all(symbol_lines.count('_'+name) == 1 for name in required_symbols),
                    'TEST119 must link each real public C/Ring definition exactly once')
            proof['linked_symbols'] = dict(command=symbol_command,
                file='runtime119-linked-symbols.txt', sha256=digest(output/'runtime119-linked-symbols.txt'),
                required=list(required_symbols))
            proof['compiled_sources'] = {str(path): digest(path) for path in [*c_sources, *swift_sources]}
            for name in ('RPCTypes.swift', 'Bridge.h', 'pause.c', 'NG2Runtime.swift', 'main.swift', 'runtime119_queue_pixels.h'):
                shutil.copyfile(stage/name, generated/name)
                proof['generated_inputs']['generated-inputs/'+name] = digest(stage/name)
            for variant in SUBRUNS:
                answer = subprocess.run([str(executable), CASE, variant], capture_output=True, text=True, timeout=30)
                (output/('runtime119-'+variant+'.txt')).write_text(answer.stdout+answer.stderr)
                lines = answer.stdout.splitlines()
                rows = [json.loads(line.removeprefix('EVIDENCE TEST119 SUBRUN ')) for line in lines
                        if line.startswith('EVIDENCE TEST119 SUBRUN ')]
                require(answer.returncode == 0 and len(rows) == 1
                    and not any(line.startswith('FAIL ') for line in lines)
                    and lines[-1:] == ['PASS TEST119 CASE '+CASE+' '+variant], 'TEST119 actual subrun failed: '+variant)
                validate_subrun(rows[0], variant)
                raw = (json.dumps(rows[0], sort_keys=True, indent=2)+'\n').encode()
                filename = 'runtime119-'+variant+'-evidence.json'; (output/filename).write_bytes(raw)
                proof['subruns'][variant] = dict(returncode=answer.returncode, qualified=True,
                    evidence_file=filename, evidence_sha256=sha(raw), evidence=rows[0])
            proof['product_pass'] = tuple(proof['subruns']) == SUBRUNS
    finally:
        (output/'runtime119-result.json').write_text(json.dumps(proof, indent=2)+'\n')
    require(proof['product_pass'], 'TEST119 queue selected scope is incomplete')
    print('PASS TEST119 selected entered_current_queue normal/candidate actual callbacks')


if __name__ == '__main__':
    main()
