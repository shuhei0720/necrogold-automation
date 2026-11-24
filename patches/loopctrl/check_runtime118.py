#!/usr/bin/env python3
"""TEST118's selected actual Runtime callback boundaries, not a full fault run.

The normal pixel worlds and controlled future captures are procedural. No
private phone PNG/Scene or classifier outcome is supplied to the Runtime.
"""
import hashlib
import inspect
import json
from pathlib import Path
import sys

import check_runtime115 as retained
import check_runtime116 as prefix116

HERE = Path(__file__).resolve().parent
CURRENT_SCOPE_FINALIZED = True  # Three source-reviewed cases; Mac execution is separate.
SWIFT_CASES = ('preinput_refresh', 'upper_side_hhddd', 'full_data_palette')
GREEN_CASES = SWIFT_CASES
DATA_CASES = ('upper_side_hhddd', 'full_data_palette')
PREPARATION_KEYS = retained.PREPARATION_KEYS | frozenset({
    'old_source_start_ns', 'old_source_end_ns', 'frozen_period_ns', 'refresh_start_ns', 'refresh_end_ns',
    'refresh_analysis_cut_ns', 'refresh_planned_analysis_cut_ns', 'refresh_observe_end_ns',
    'begin_return_ns', 'begin_cost_ns', 'observe_cost_ns',
    'fit_phase_adjustments', 'tick_cost_ns',
})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_source():
    source = prefix116.fixture_source()
    boundary = '\nlet root116 = FileManager.default.temporaryDirectory'
    if source.count(boundary) != 1:
        raise ValueError('exact TEST116 declaration-only boundary')
    return source.split(boundary)[0]+'\n'+(HERE/'ngg2_runtime118_tests.swift').read_text()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('retained TEST115 builder boundary changed: '+old[:100])
    return source.replace(old, new)


def preparation_evidence(lines, case):
    rows = []
    try:
        rows = [json.loads(line.split(' PREPARATION ', 1)[1]) for line in lines
            if line.startswith('EVIDENCE TEST118 PREPARATION ')]
    except (ValueError, TypeError):
        return rows, False
    if not case.startswith('preinput_refresh'):
        return rows, not rows
    if len(rows) != 1 or set(rows[0]) != PREPARATION_KEYS:
        return rows, False
    r = rows[0]
    if not all(type(value) is int and value >= 0 for value in r.values()):
        return rows, False
    nb = r['old_not_before_ns']
    good = (0 < r['old_command_id'] < r['new_command_id']
        and 0 < r['old_source_capture_id'] < r['new_source_capture_id']
        and all(r['old_'+key] == r['new_'+key] > 0
                for key in ('target_ns', 'not_before_ns', 'deadline_ns', 'ordinal'))
        and 0 < r['old_source_start_ns'] < r['old_source_end_ns'] <= r['refresh_start_ns']
        and r['frozen_period_ns'] > 0
        and r['refresh_start_ns']-r['old_source_start_ns'] >= r['frozen_period_ns']//10
        and nb-30_000_000 <= r['refresh_start_ns'] < r['refresh_end_ns']
        and r['refresh_end_ns']-r['refresh_start_ns'] >= 10_000_000
        and nb-r['refresh_planned_analysis_cut_ns'] == 15_000_000
        and r['refresh_end_ns'] <= r['refresh_analysis_cut_ns']
        and r['refresh_planned_analysis_cut_ns'] <= r['refresh_analysis_cut_ns']
        and r['refresh_analysis_cut_ns'] < r['refresh_observe_end_ns'] <= r['refresh_commit_ns'] < nb
        and r['refresh_commit_ns'] <= r['old_return_ns']
        and r['old_return_ns'] <= r['new_main_admission_ns'] < r['begin_return_ns'] <= r['old_deadline_ns']
        and r['new_main_admission_ns']-nb == 3_610_361
        and 0 < r['begin_cost_ns'] == r['begin_return_ns']-r['new_main_admission_ns']
        and r['observe_cost_ns'] > 0 and r['tick_cost_ns'] > 0 and r['fit_phase_adjustments'] == 0
        and 0 < r['old_query_start_ns'] <= r['old_query_end_ns'] <= r['refresh_commit_ns']
        and r['old_query_start_ns'] == r['new_query_start_ns']
        and r['old_query_end_ns'] == r['new_query_end_ns']
        and r['old_prepared_command_id'] == r['new_prepared_command_id'] == r['old_command_id']
        and 0 < r['old_epoch'] == r['new_epoch']
        and (r['old_begin_count'], r['new_begin_count']) == (0, 1))
    return rows, good


def runtime_main():
    """Reuse the retained actual compile/source/link/export qualification."""
    source = inspect.getsource(retained.main)
    source = (source.replace('runtime115-', 'runtime118-').replace("'runtime115'", "'runtime118'")
        .replace('TEST115', 'TEST118').replace('test115_', 'test118_'))
    source = replace_once(source,
        "fixture_inputs['check_runtime115.py'] = digest(Path(__file__).resolve())",
        "fixture_inputs['check_runtime118.py'] = digest(Path(__file__).resolve())")
    source = replace_once(source,
        "'void ng2_fixture_begin115_install(NG2Begin115Callback,void *);\\n')",
        "'void ng2_fixture_begin115_install(NG2Begin115Callback,void *);\\n'\n"
        "            'int ng2_fixture_upper118_rgba(uint8_t *,size_t,int32_t,int32_t,int32_t,double);\\n'\n"
        "            'int ng2_fixture_walk118_rgba(uint8_t *,size_t,int32_t,double);\\n'\n"
        "            'int ng2_fixture_palette118(uint8_t *,size_t);\\n'\n"
        "            'typedef void (*NG2Tick118Callback)(void *,uint64_t);\\n'\n"
        "            'void ng2_fixture_tick118_install(NG2Tick118Callback,void *);\\n')")
    source = replace_once(source,
        "shutil.copyfile(stage / 'runtime112_upper_shop.h', output / 'runtime112_upper_shop.h')",
        "shutil.copyfile(stage / 'runtime112_upper_shop.h', output / 'runtime112_upper_shop.h')\n"
        "        import generate_shop118_pixels as shop118\n"
        "        shop_generation = shop118.generate(stage / 'runtime118_shop_pixels.h', output / 'runtime118-shop-generation.json')\n"
        "        shutil.copyfile(stage / 'runtime118_shop_pixels.h', output / 'runtime118_shop_pixels.h')")
    source = replace_once(source,
        "HERE / 'ngg2_runtime115_begin_fixture.c', stage / 'pause.c']",
        "HERE / 'ngg2_runtime115_begin_fixture.c', HERE / 'ngg2_runtime118_fixture.c', stage / 'pause.c']")
    source = replace_once(source, "fixture_inputs.update(upper_generation['source_sha256'])",
        "fixture_inputs.update(upper_generation['source_sha256'])\n"
        "        fixture_inputs.update(shop_generation['source_sha256'])\n"
        "        fixture_inputs['runtime118_shop_pixels.h'] = digest(stage / 'runtime118_shop_pixels.h')")
    source = replace_once(source, "'upper_pixel_generation': upper_generation,",
        "'upper_pixel_generation': upper_generation, 'shop118_pixel_generation': shop_generation,")
    source = replace_once(source,
        "flags.append('-Dng2_controller_begin='+CONTROLLER_BEGIN_ALIAS)",
        "flags.append('-Dng2_controller_begin='+CONTROLLER_BEGIN_ALIAS)\n"
        "                flags.append('-Dng2_controller_tick=ng2_controller_tick118_actual')\n"
        "            if source.name == 'ngg2_runtime118_fixture.c':\n"
        "                flags += ['-DNG2_RUNTIME118_TIMING_BRIDGE', '-D_POSIX_C_SOURCE=200809L']")
    source = replace_once(source,
        "compiled_sources = {str(path): digest(path) for path in [*sources_c, *sources]}",
        "compiled_sources = {str(path): digest(path) for path in [*sources_c, *sources]}\n"
        "        compiled_object_sha256 = {str(path): digest(obj) for path,obj in zip(sources_c,objects)}\n"
        "        linked_executable_sha256 = digest(stage / 'runtime118')\n"
        "        symbols = subprocess.run(['nm','-g',str(stage / 'runtime118')],capture_output=True,text=True,check=True)\n"
        "        (output / 'runtime118-linked-symbols.txt').write_text(symbols.stdout+symbols.stderr)\n"
        "        actual_symbols = {line.split()[-1].lstrip('_') for line in symbols.stdout.splitlines() if line.split()}\n"
        "        required_symbols = {'ng2_controller_tick118_actual','ng2_controller_tick','ng2_controller_begin115_actual','ng2_controller_begin','ng2_controller_observe_at','ng2_analyze_rgba','ng2_ring_assess_rgba'}\n"
        "        if not required_symbols.issubset(actual_symbols):\n"
        "            raise ValueError('TEST118 linked actual product C symbols missing')")
    source = replace_once(source,
        "'compiled_sources': compiled_sources, 'compilers': compiler_identity,",
        "'compiled_sources': compiled_sources, 'compiled_object_sha256': compiled_object_sha256,\n"
        "            'linked_executable_sha256': linked_executable_sha256, 'linked_required_symbols': sorted(required_symbols),\n"
        "            'compilers': compiler_identity,")
    namespace = dict(vars(retained))
    namespace.update(__file__=__file__, fixture_source=fixture_source,
        preparation_evidence=preparation_evidence,
        SCOPE_FINALIZED=CURRENT_SCOPE_FINALIZED, GREEN_CASES=SWIFT_CASES, DATA_CASES=DATA_CASES,
        HOST_ALIASES=retained.HOST_ALIASES+('NG2RuntimeContinuousTestHooks',
            'ng2_fixture_upper118_rgba', 'ng2_fixture_walk118_rgba', 'ng2_fixture_palette118',
            'ng2_fixture_tick118_install', 'ng2_controller_tick118_actual'),
        IMMUTABLE_FIXTURES=retained.IMMUTABLE_FIXTURES+('check_runtime115.py','check_runtime116.py',
            'ngg2_runtime116_tests.swift','ngg2_runtime118_tests.swift',
            'ngg2_runtime118_fixture.c','generate_shop118_pixels.py'))
    exec(compile(source, __file__+'::retained-main', 'exec'), namespace)
    namespace['main']()


def main():
    if len(sys.argv) != 3 or any(arg.startswith('--') for arg in sys.argv[1:]):
        raise SystemExit('usage: check_runtime118.py PATCHED_UPSTREAM OUTPUT')
    if not CURRENT_SCOPE_FINALIZED:
        raise SystemExit('TEST118 Runtime fixture scope pending; no assertion executed')
    runtime_main()
    receipt = Path(sys.argv[2]).resolve()/'runtime118-result.json'
    proof = json.loads(receipt.read_bytes())
    proof.update(controller_tick_symbol_alias='ng2_controller_tick118_actual', final_scope_finalized=CURRENT_SCOPE_FINALIZED, phone_acceptance=False,
        scope='selected current Runtime callback/normal RGBA boundaries with public procedural future and charged host native cost; no complete recorded-game replay or old fault suite')
    receipt.write_text(json.dumps(proof, indent=2)+'\n')


if __name__ == '__main__':
    main()
