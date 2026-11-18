#!/usr/bin/env python3
"""Selected TEST115 actual Runtime callbacks with the current Controller and Ring."""
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
GREEN_CASES = ('passage_fresh', 'partial_view', 'partial_cancel', 'post_begin_clock')
DATA_CASES = ('partial_view', 'partial_cancel')
RED_CASE = 'partial_view'
RUNTIME_RED_CASE = 'post_begin_clock'
PREPARATION_KEYS = frozenset({
    'old_command_id', 'new_command_id', 'old_source_capture_id', 'new_source_capture_id',
    'old_target_ns', 'new_target_ns', 'old_not_before_ns', 'new_not_before_ns',
    'old_deadline_ns', 'new_deadline_ns', 'old_ordinal', 'new_ordinal',
    'refresh_commit_ns', 'old_return_ns', 'new_main_admission_ns',
    'old_query_start_ns', 'old_query_end_ns', 'new_query_start_ns', 'new_query_end_ns',
    'old_prepared_command_id', 'new_prepared_command_id',
    'old_epoch', 'new_epoch', 'old_begin_count', 'new_begin_count',
})
BEFORE_CONTROLLER_SHA256 = '053b2da0773899a8e19db7d11454c297edcca7cf04422a17210ede2f90195843'
BEFORE_RUNTIME_SHA256 = 'dc082fd9658df32924c90423c544030d327c744f4224d4d8c868762a6e2e741f'
EXPECTED_RED_ASSERTION = 'FAIL test115_old_partial_queues_independent_current_data_without_old_authority'
EXPECTED_RUNTIME_RED_ASSERTION = 'FAIL test115_post_begin_deadline_crossing_never_calls_gesture'
CONTROLLER_BEGIN_ALIAS = 'ng2_controller_begin115_actual'
POST_BEGIN_VARIANTS = ('late', 'within', 'equal', 'late_cancel', 'owner', 'locked', 'authority')
POST_BEGIN_INTEGER_KEYS = frozenset({'command_id', 'source_capture_id', 'before_ns', 'after_ns',
    'not_before_ns', 'deadline_ns', 'begin_ns', 'end_ns', 'outcome', 'inputs', 'moves',
    'input_state', 'gesture_count', 'move_event_count', 'begin_call_count'})
POST_BEGIN_BOOLEAN_KEYS = frozenset({'cancel_queued', 'cancel_completed', 'exported_source'})
POST_BEGIN_KEYS = POST_BEGIN_INTEGER_KEYS | POST_BEGIN_BOOLEAN_KEYS | frozenset({'variant', 'report_file', 'failure_code'})
HOST_ALIASES = ('NG2RuntimeTestHooks', 'NG2RuntimeCycleTestHooks', 'NG2Fake',
    'testRestartYieldState', 'testRestartYieldPinPressure', 'testRestartYieldSaturatePins112',
    'testIrregularRetentionIDs', 'testOriginalFrameEvidence', 'ng2_fixture_upper112_rgba',
    'ng2_fixture_floor_pixels_rgba', 'ng2_fixture_cycle_search_rgba', 'ng2_fixture_cycle_result',
    'ng2_fixture_partial_unknown110', 'ng2_fixture_irregular110', 'ng2_test_pause',
    'ng2_fixture_begin115_install', 'ng2_controller_begin115_actual')
SCOPE_FINALIZED = True  # Exact author-frozen callback scope; actual execution is separate.
IMMUTABLE_FIXTURES = (
    'ngg2_runtime_tests.swift', 'ngg2_dispatch_preparation_tests.swift',
    'ngg2_cycle_runtime_tests.swift', 'ngg2_runtime_irregular110_tests.swift',
    'ngg2_runtime110_tests.swift', 'ngg2_runtime_fakes.swift',
    'ngg2_runtime_scene_fixtures.c', 'ngg2_runtime_scene_fixtures.h',
    'ngg2_cycle_runtime_fixture.c', 'ngg2_cycle_runtime_fixture.h',
    'ngg2_runtime110_fixture.c', 'ngg2_runtime111_tests.swift',
    'check_runtime111.py', 'ngg2_runtime114_tests.swift', 'ngg2_runtime114_current_fixture.c',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preparation_evidence(lines, case):
    rows = []
    try:
        for line in lines:
            if line.startswith('EVIDENCE TEST115 PREPARATION '):
                rows.append(json.loads(line.split(' PREPARATION ', 1)[1]))
    except (ValueError, TypeError):
        return rows, False
    if case != 'passage_fresh':
        return rows, not rows
    if len(rows) != 1:
        return rows, False
    r = rows[0]
    qualified = (type(r) is dict and set(r) == PREPARATION_KEYS
        and all(type(value) is int and value >= 0 for value in r.values()))
    if not qualified:
        return rows, False
    qualified = (0 < r['old_command_id'] < r['new_command_id']
        and 0 < r['old_source_capture_id'] < r['new_source_capture_id']
        and all(r['old_'+key] == r['new_'+key] > 0
                for key in ('target_ns', 'not_before_ns', 'deadline_ns', 'ordinal'))
        and r['old_not_before_ns'] <= r['old_deadline_ns']
        and r['refresh_commit_ns'] <= r['old_return_ns'] <= r['new_main_admission_ns'] <= r['old_deadline_ns']
        and r['new_main_admission_ns']-r['refresh_commit_ns'] == 54_008_584
        and r['old_not_before_ns']-r['refresh_commit_ns'] == 49_974_003
        and r['new_main_admission_ns']-r['old_not_before_ns'] == 4_034_581
        and 0 < r['old_query_start_ns'] <= r['old_query_end_ns'] <= r['refresh_commit_ns']
        and r['old_query_start_ns'] == r['new_query_start_ns']
        and r['old_query_end_ns'] == r['new_query_end_ns']
        and r['old_prepared_command_id'] == r['new_prepared_command_id'] == r['old_command_id']
        and 0 < r['old_epoch'] == r['new_epoch']
        and (r['old_begin_count'], r['new_begin_count']) == (0, 1))
    return rows, qualified


def post_begin_evidence(lines, case, output, runtime_red, read_report=None):
    rows, reports = [], {}
    try:
        for line in lines:
            if line.startswith('EVIDENCE TEST115 POST_BEGIN '):
                rows.append(json.loads(line.split(' POST_BEGIN ', 1)[1]))
        if case != RUNTIME_RED_CASE:
            return rows, reports, not rows
        variants = ('late',) if runtime_red else POST_BEGIN_VARIANTS
        if len(rows) != len(variants):
            return rows, reports, False
        root = HERE.parents[1]
        import sys
        sys.path.insert(0, str(root))
        from necroprobe import native_walk
        if Path(native_walk.__file__).resolve() != root/'necroprobe/native_walk.py':
            return rows, reports, False
        for variant, row in zip(variants, rows):
            if (type(row) is not dict or set(row) != POST_BEGIN_KEYS or row['variant'] != variant
                    or any(type(row[k]) is not int or not 0 <= row[k] < 2**63 for k in POST_BEGIN_INTEGER_KEYS)
                    or any(type(row[k]) is not bool for k in POST_BEGIN_BOOLEAN_KEYS)):
                return rows, reports, False
            relative = 'status-snapshots/status-post-begin-'+variant+'.json'
            if row['report_file'] != relative:
                return rows, reports, False
            if read_report is None:
                path = output/relative
                if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
                    return rows, reports, False
                raw = path.read_bytes()
            else:
                raw = read_report(relative)
            if len(raw) > 2*1024*1024:
                return rows, reports, False
            try:
                value = native_walk.json_object(raw, 2*1024*1024)
                report = native_walk._report(value, api_version='1.98.16-ngg2',
                    require_motion_references=True, require_recovery=True)
            except native_walk.ProbeError:
                return rows, reports, False
            moves = [event for event in report.get('events', []) if event.get('kind') == 4]
            selected = [event for event in moves if event.get('id') == row['command_id']]
            if len(moves) != 1 or len(selected) != 1:
                return rows, reports, False
            event = selected[0]
            sent = runtime_red or variant in ('within', 'equal')
            failure = (None if sent else {'late':'too_late', 'late_cancel':'too_late',
                'owner':'owner', 'locked':'locked', 'authority':'authority_stale'}[variant])
            observed_failure = report.get('dispatch_failure')
            observed_code = None if observed_failure is None else observed_failure['code']
            if row['failure_code'] != failure or observed_code != failure:
                return rows, reports, False
            if not (row['command_id'] > 0 and row['source_capture_id'] > 0
                    and row['not_before_ns'] <= row['before_ns'] <= row['deadline_ns']
                    and row['begin_ns'] == row['before_ns'] > 0 and row['end_ns'] >= row['after_ns']
                    and row['begin_call_count'] == row['move_event_count'] == 1
                    and row['gesture_count'] == row['inputs'] == int(sent)
                    and row['moves'] == 0 and row['input_state'] != 4 and row['exported_source'] is True
                    and row['outcome'] == (2 if sent else 3)):
                return rows, reports, False
            for key in ('inputs', 'moves', 'input_state'):
                if report.get(key) != row[key]: return rows, reports, False
            for key in ('source_capture_id', 'not_before_ns', 'deadline_ns', 'begin_ns', 'end_ns', 'outcome'):
                if event.get(key) != row[key]: return rows, reports, False
            if variant in ('late', 'late_cancel') and row['after_ns'] != row['deadline_ns']+1:
                return rows, reports, False
            if variant == 'equal' and row['after_ns'] != row['deadline_ns']:
                return rows, reports, False
            if variant in ('within', 'owner', 'locked') and row['after_ns'] != row['deadline_ns']-1:
                return rows, reports, False
            if variant == 'authority':
                query = report.get('dispatch_failure', {}).get('query_start_ns')
                if type(query) is not int or row['after_ns'] < max(row['deadline_ns']+1, query+1_000_000_001):
                    return rows, reports, False
            if row['cancel_queued'] != (variant == 'late_cancel') or row['cancel_completed'] != (variant == 'late_cancel'):
                return rows, reports, False
            reports[variant] = dict(path=relative, sha256=hashlib.sha256(raw).hexdigest(),
                parser='necroprobe.native_walk._report', api_version='1.98.16-ngg2',
                parsed_sha256=hashlib.sha256(json.dumps(report, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        return rows, reports, True
    except (ValueError, TypeError, OSError, KeyError, AttributeError):
        return rows, reports, False


def fixture_source():
    # Old functions/assertions compile unchanged. Only their executable
    # entrypoints are replaced by the frozen TEST115 cases.
    import check_runtime112 as prior
    source = prior.fixture_source()
    boundary = '\nlet root112 = FileManager.default.temporaryDirectory'
    if source.count(boundary) != 1:
        raise ValueError('exact TEST112 executable boundary for TEST115')
    declarations114 = (HERE / 'ngg2_runtime114_tests.swift').read_text()
    boundary114 = '\nlet root114 = FileManager.default.temporaryDirectory'
    if declarations114.count(boundary114) != 1:
        raise ValueError('exact TEST114 executable boundary for TEST115')
    return (source.split(boundary)[0] + '\n' + declarations114.split(boundary114)[0]
            + '\n' + (HERE / 'ngg2_runtime115_tests.swift').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expect-red', action='store_true')
    parser.add_argument('--before-controller', type=Path)
    parser.add_argument('--expect-runtime-red', action='store_true')
    parser.add_argument('--before-runtime', type=Path)
    args = parser.parse_args()
    if args.expect_red != (args.before_controller is not None):
        parser.error('TEST115 before-Controller assertion requires both explicit options')
    if args.expect_runtime_red != (args.before_runtime is not None):
        parser.error('TEST115 before-Runtime assertion requires both explicit options')
    if args.expect_red and args.expect_runtime_red:
        parser.error('TEST115 before-Controller and before-Runtime are separate assertions')
    expecting_red = args.expect_red or args.expect_runtime_red
    if not SCOPE_FINALIZED or not GREEN_CASES:
        raise SystemExit('TEST115 Runtime scope is pending; no fixture executed')
    for compiler in ('swiftc', 'clang'):
        if not shutil.which(compiler):
            raise SystemExit(compiler + ' unavailable; no TEST115 Runtime assertion executed')
    native = args.upstream.resolve() / 'LoopCtrlUITests'
    before_controller = args.before_controller.resolve() if args.before_controller is not None else None
    before_runtime = args.before_runtime.resolve() if args.before_runtime is not None else None
    if before_controller is not None and (args.before_controller.is_symlink()
            or digest(before_controller) != BEFORE_CONTROLLER_SHA256):
        raise ValueError('TEST115 before-Controller differs from the pinned TEST114 C')
    if before_runtime is not None and (args.before_runtime.is_symlink()
            or digest(before_runtime) != BEFORE_RUNTIME_SHA256):
        raise ValueError('TEST115 before-Runtime differs from the pinned TEST114 Swift')
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
    with tempfile.TemporaryDirectory(prefix='runtime115-') as temporary:
        stage = Path(temporary)
        types = (args.upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
        if len(types) != 2:
            raise ValueError('RPCTypes boundary')
        (stage / 'RPCTypes.swift').write_text(types[0])
        fixture = fixture_source()
        (stage / 'main.swift').write_text(fixture)
        (output / 'runtime115-selected-fixture.swift').write_text(fixture)
        (stage / 'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n'
            '#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_cycle_runtime_fixture.h"\n'
            'int ng2_fixture_upper112_rgba(uint8_t *,size_t,int32_t,int32_t,double);\n'
            'void ng2_fixture_partial_unknown110(const NG2Scene *,uint64_t,uint64_t,NG2RingResult *);\n'
            'void ng2_test_pause(uint8_t *,size_t);\n'
            'int ng2_fixture_irregular110(uint8_t *,size_t,int,int,int);\n'
            'int ng2_fixture_current114_rgba(uint8_t *,size_t,int32_t,double);\n'
            'int ng2_fixture_passage115_rgba(uint8_t *,size_t,int32_t,double);\n'
            'int ng2_fixture_partial115_rgba(uint8_t *,size_t,int32_t,double);\n'
            'typedef void (*NG2Begin115Callback)(void *,uint64_t,uint64_t,int32_t);\n'
            'void ng2_fixture_begin115_install(NG2Begin115Callback,void *);\n')
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
        upper_generation = upper_pixels.generate(stage / 'runtime112_upper_shop.h', output / 'runtime115-upper-generation.json')
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
            HERE / 'ngg2_runtime112_upper_fixture.c', HERE / 'ngg2_runtime114_current_fixture.c', HERE / 'ngg2_runtime115_fixture.c',
            HERE / 'ngg2_runtime115_begin_fixture.c', stage / 'pause.c']
        if before_controller is not None:
            sources_c = [before_controller if source == native/'NG2Controller.c' else source for source in sources_c]
        compiled_native_sha256 = {name: digest(sources_c[index]) for index, name in enumerate(base.NATIVE)}
        for index, source in enumerate(sources_c):
            obj = stage / ('native-' + str(index) + '.o')
            flags = ['-O0'] if source.name in ('NG2Controller.c', 'NG2Beat.c') or source == before_controller else [
                '-O2', '-fno-fast-math', '-ffp-contract=off']
            if source == native/'NG2Controller.c' or source == before_controller:
                flags.append('-Dng2_controller_begin='+CONTROLLER_BEGIN_ALIAS)
            cmd = ['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE),
                   '-I', str(stage), '-c', str(source), '-o', str(obj)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            (output / (source.stem + '-compile.txt')).write_text(result.stdout + result.stderr)
            if result.returncode:
                raise SystemExit('C compile failure is not assertion Red:\n' + result.stdout + result.stderr)
            commands.append(cmd); objects.append(obj)
        runtime_source = before_runtime if before_runtime is not None else native / 'NG2Runtime.swift'
        sources = [stage / 'RPCTypes.swift', native / 'NG2Ticket.swift', native / 'NG2Raster.swift',
            *(native / name for name in base.HELPERS), HERE / 'ngg2_runtime_fakes.swift',
            runtime_source, stage / 'main.swift']
        cmd = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094',
            '-D', 'NG2_PREPARATION_TEST058_GREEN', '-Xcc', '-I' + str(native), '-Xcc', '-I' + str(HERE),
            '-import-objc-header', str(stage / 'Bridge.h'), *map(str, sources), *map(str, objects),
            '-o', str(stage / 'runtime115')]
        cmd.insert(1, 'NG2_IRREGULAR_TEST110_GREEN'); cmd.insert(1, '-D')
        cmd.insert(1, 'NG2_RESTART_YIELD_TEST112_GREEN'); cmd.insert(1, '-D')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (output / 'runtime115-swift-compile.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('Swift compile failure is not assertion Red:\n' + result.stdout + result.stderr)
        commands.append(cmd)
        fixture_inputs = {name: digest(HERE / name) for name in IMMUTABLE_FIXTURES}
        fixture_inputs['ngg2_runtime115_tests.swift'] = digest(HERE / 'ngg2_runtime115_tests.swift')
        fixture_inputs['ngg2_runtime115_fixture.c'] = digest(HERE / 'ngg2_runtime115_fixture.c')
        fixture_inputs['ngg2_runtime115_begin_fixture.c'] = digest(HERE / 'ngg2_runtime115_begin_fixture.c')
        fixture_inputs['ngg2_runtime112_tests.swift'] = digest(HERE / 'ngg2_runtime112_tests.swift')
        fixture_inputs['check_runtime112.py'] = digest(HERE / 'check_runtime112.py')
        fixture_inputs['ngg2_runtime112_upper_fixture.c'] = digest(HERE / 'ngg2_runtime112_upper_fixture.c')
        fixture_inputs['generate_upper112_pixels.py'] = digest(HERE / 'generate_upper112_pixels.py')
        fixture_inputs.update(upper_generation['source_sha256'])
        fixture_inputs['check_runtime115.py'] = digest(Path(__file__).resolve())
        fixture_inputs['RPCTypes.swift'] = digest(stage / 'RPCTypes.swift')
        fixture_inputs['Bridge.h'] = digest(stage / 'Bridge.h')
        fixture_inputs['pause.c'] = digest(stage / 'pause.c')
        fixture_inputs['runtime110_masks.h'] = digest(stage / 'runtime110_masks.h')
        fixture_inputs['runtime112_upper_shop.h'] = digest(stage / 'runtime112_upper_shop.h')
        fixture_inputs['check_runtime110.py'] = digest(HERE / 'check_runtime110.py')
        fixture_inputs['check_runtime_cycle094.py'] = digest(HERE / 'check_runtime_cycle094.py')
        for name in ('necroprobe/native_walk.py', 'necroprobe/validation.py'):
            fixture_inputs[name] = digest(HERE.parents[1]/name)
        compiled_sources = {str(path): digest(path) for path in [*sources_c, *sources]}
        generated_inputs = {}
        generated_root = output / 'generated-inputs'
        generated_root.mkdir(exist_ok=True)
        for name in ('RPCTypes.swift', 'Bridge.h', 'pause.c', 'runtime110_masks.h'):
            shutil.copyfile(stage / name, generated_root / name)
            generated_inputs['generated-inputs/' + name] = digest(stage / name)
        results = {}
        cases = ((RED_CASE,) if args.expect_red else
                 (RUNTIME_RED_CASE,) if args.expect_runtime_red else GREEN_CASES)
        for case in cases:
            try:
                environment = dict(os.environ, NG2_RUNTIME112_EVIDENCE=str(output / 'synthetic-runtime-exports'), NG2_RUNTIME112_CASE=case, NG2_RUNTIME115_EVIDENCE=str(output / 'synthetic-runtime-exports'), NG2_RUNTIME115_CASE=case)
                result = subprocess.run([str(stage / 'runtime115'), case], capture_output=True, text=True, timeout=240, env=environment)
                stdout, stderr, code = result.stdout, result.stderr, result.returncode
                timed_out = False
            except subprocess.TimeoutExpired as error:
                stdout = error.stdout or b''
                stderr = error.stderr or b''
                if isinstance(stdout, bytes): stdout = stdout.decode(errors='replace')
                if isinstance(stderr, bytes): stderr = stderr.decode(errors='replace')
                code, timed_out = None, True
            (output / ('runtime115-' + case + '.txt')).write_text(stdout + stderr)
            failures = [line for line in stdout.splitlines() if line.startswith('FAIL ')]
            markers = [line for line in stdout.splitlines() if line.startswith('PASS TEST115 CASE ')]
            admissions, admission_decode_failed = [], False
            for line in stdout.splitlines():
                if line.startswith(('EVIDENCE TEST112 ADMISSION ', 'EVIDENCE TEST114 ADMISSION ', 'EVIDENCE TEST115 ADMISSION ')):
                    try:
                        admissions.append(json.loads(line.split(' ADMISSION ', 1)[1]))
                    except (ValueError, TypeError):
                        admission_decode_failed = True
            ages_qualified = not admission_decode_failed and (bool(admissions) if case in DATA_CASES else not admissions)
            for row in admissions:
                if type(row) is not dict:
                    ages_qualified = False
                    continue
                values = [row.get(key) for key in ('capture_start_ns', 'worker_started_ns', 'deadline_ns', 'source_age_at_worker_admission_ns')]
                if (not all(type(value) is int for value in values) or not 0 <= values[3] <= 150_000_000
                        or values[3] != values[1] - values[0]
                        or not values[1] <= values[2] <= min(values[0] + 150_000_000, values[1] + 100_000_000)):
                    ages_qualified = False
            preparation, preparation_qualified = preparation_evidence(stdout.splitlines(), case)
            post_begin, post_reports, post_qualified = post_begin_evidence(
                stdout.splitlines(), case, output, args.expect_runtime_red)
            expected_failure = EXPECTED_RUNTIME_RED_ASSERTION if args.expect_runtime_red else EXPECTED_RED_ASSERTION
            qualified = (not timed_out and ages_qualified and preparation_qualified and post_qualified and
                (code == 1 and failures == [expected_failure] and not markers if expecting_red else
                 code == 0 and not failures and markers == ['PASS TEST115 CASE '+case]))
            results[case] = dict(returncode=code, timed_out=timed_out, assertion_failures=failures,
                markers=markers, qualification=('runtime_assertion_red' if args.expect_runtime_red else
                    'assertion_red' if args.expect_red else 'green'), source_admissions=admissions,
                source_admission_ages_qualified=ages_qualified,
                preparation_evidence=preparation, preparation_evidence_qualified=preparation_qualified,
                post_begin_evidence=post_begin, post_begin_reports=post_reports,
                post_begin_evidence_qualified=post_qualified,
                qualified=qualified)
            print(case+(': expected assertion Red' if expecting_red and qualified else ': Green' if qualified else ': FAILED qualification'), flush=True)
            if not qualified:
                print(stdout + stderr or 'Unexpected Runtime115 result', flush=True)
        # An unknown case must not execute a different successful fixture.
        unknown_rejected = False
        if not expecting_red:
            try:
                unknown = subprocess.run([str(stage/'runtime115'), '__unknown115__'],
                    capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired:
                unknown = subprocess.CompletedProcess(['runtime115', '__unknown115__'], None, '', 'unknown-case timeout')
            (output/'runtime115-unknown-case.txt').write_text(unknown.stdout+unknown.stderr)
            unknown_rejected = (unknown.returncode == 1 and
                [line for line in unknown.stdout.splitlines() if line.startswith('FAIL ')] ==
                ['FAIL test115_unknown_case_is_not_another_fixture'] and
                not any(line.startswith('PASS TEST115 CASE ') for line in unknown.stdout.splitlines()))
        product_pass = not expecting_red and tuple(results) == GREEN_CASES and all(row['qualified'] for row in results.values()) and unknown_rejected
        expected_red_qualified = args.expect_red and tuple(results) == (RED_CASE,) and all(row['qualified'] for row in results.values())
        expected_runtime_red_qualified = args.expect_runtime_red and tuple(results) == (RUNTIME_RED_CASE,) and all(row['qualified'] for row in results.values())
        status_snapshots = {str(path.relative_to(output)): digest(path) for path in sorted((output / 'status-snapshots').glob('status-*.json'))}
        proof = {
            'schema': 'ngg2-runtime115-host-proof-v1',
            'scope': 'actual current Swift Runtime/C callbacks and normal Ring producer; procedural pixels/clock/UI; no phone acceptance or captured-game replay',
            'required_cases': list(cases), 'product_pass': product_pass,
            'before_runtime_api_assertion_executed': False,
            'expected_assertion_red': args.expect_red, 'expected_red_qualified': expected_red_qualified,
            'expected_runtime_assertion_red': args.expect_runtime_red,
            'expected_runtime_red_qualified': expected_runtime_red_qualified,
            'before_controller_sha256': digest(before_controller) if before_controller is not None else None,
            'before_runtime_sha256': digest(before_runtime) if before_runtime is not None else None,
            'current_controller_sha256': identities['NG2Controller.c'],
            'current_runtime_sha256': identities['NG2Runtime.swift'],
            'compiled_runtime_sha256': digest(runtime_source),
            'controller_begin_symbol_alias': CONTROLLER_BEGIN_ALIAS,
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
            'host_aliases': list(HOST_ALIASES) + ['ng2_fixture_current114_rgba', 'ng2_fixture_passage115_rgba',
                'ng2_fixture_partial115_rgba'],
        }
        (output / 'runtime115-result.json').write_text(json.dumps(proof, indent=2) + '\n')
        failed = [case for case, row in results.items() if not row['qualified']]
        if failed or (not expecting_red and not unknown_rejected):
            raise SystemExit('TEST115 Runtime qualification failed: '+', '.join(failed+([] if expecting_red or unknown_rejected else ['unknown_case'])))
        print('PASS TEST115 pinned before-Runtime assertion Red' if args.expect_runtime_red else
              'PASS TEST115 pinned before-Controller assertion Red' if args.expect_red else
              'PASS TEST115 selected current Runtime callbacks')


if __name__ == '__main__':
    main()
