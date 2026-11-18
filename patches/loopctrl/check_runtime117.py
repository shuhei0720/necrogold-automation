#!/usr/bin/env python3
"""Five TEST117 boundaries: three actual Runtime/RGBA, two public C Scene cuts.

No private PNG/Scene is an input. Recorded relative timing constants constrain
the Scene cuts; their later procedural captures are not captured-game replay.
"""
import ctypes as C
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

import check_runtime115 as retained
import check_runtime116 as prefix116
import generate_shop117_pixels as shop_pixels

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CURRENT_SCOPE_FINALIZED = True  # Exact five-case author scope; Mac execution is separate.
SWIFT_CASES = ('single_face_restart', 'mixed_price_partial', 'root_floor_restart')
SCENE_CASES = ('unsent_clear_reproof', 'unsent_gold1_reproof')
GREEN_CASES = SWIFT_CASES + SCENE_CASES
DATA_CASES = SWIFT_CASES[:2]
INITIAL_RUNTIME_RED_ASSERTION = 'FAIL test117_initial_root_never_RESUMEs_old_floor'
INITIAL_ENABLE_CALL = 'ng2_controller_enable_initial_restart(core)'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_source():
    source = prefix116.fixture_source()
    boundary = '\nlet root116 = FileManager.default.temporaryDirectory'
    if source.count(boundary) != 1:
        raise ValueError('exact TEST116 declaration-only boundary')
    return source.split(boundary)[0]+'\n'+(HERE/'ngg2_runtime117_tests.swift').read_text()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('retained TEST115 builder boundary changed: '+old[:100])
    return source.replace(old, new)


def runtime_main(*, feature_off_sha=None):
    """Reuse compile, sealed-source matching, callback and export predicates."""
    source = inspect.getsource(retained.main)
    source = (source.replace('runtime115-', 'runtime117-').replace("'runtime115'", "'runtime117'")
        .replace('TEST115', 'TEST117').replace('test115_', 'test117_'))
    source = replace_once(source,
        "fixture_inputs['check_runtime115.py'] = digest(Path(__file__).resolve())",
        "fixture_inputs['check_runtime117.py'] = digest(Path(__file__).resolve())")
    source = replace_once(source,
        "'void ng2_fixture_begin115_install(NG2Begin115Callback,void *);\\n')",
        "'void ng2_fixture_begin115_install(NG2Begin115Callback,void *);\\n'\n"
        "            'int ng2_fixture_shop117_rgba(uint8_t *,size_t,int,int,int,double);\\n')")
    source = replace_once(source,
        "shutil.copyfile(stage / 'runtime112_upper_shop.h', output / 'runtime112_upper_shop.h')",
        "shutil.copyfile(stage / 'runtime112_upper_shop.h', output / 'runtime112_upper_shop.h')\n"
        "        import generate_shop117_pixels as shop117\n"
        "        shop_generation = shop117.generate(stage / 'runtime117_shop_pixels.h', output / 'runtime117-shop-generation.json')\n"
        "        shutil.copyfile(stage / 'runtime117_shop_pixels.h', output / 'runtime117_shop_pixels.h')")
    source = replace_once(source,
        "HERE / 'ngg2_runtime115_begin_fixture.c', stage / 'pause.c']",
        "HERE / 'ngg2_runtime115_begin_fixture.c', HERE / 'ngg2_runtime117_fixture.c', stage / 'pause.c']")
    source = replace_once(source, "fixture_inputs.update(upper_generation['source_sha256'])",
        "fixture_inputs.update(upper_generation['source_sha256'])\n"
        "        fixture_inputs.update(shop_generation['source_sha256'])\n"
        "        fixture_inputs['runtime117_shop_pixels.h'] = digest(stage / 'runtime117_shop_pixels.h')")
    source = replace_once(source, "'upper_pixel_generation': upper_generation,",
        "'upper_pixel_generation': upper_generation, 'shop117_pixel_generation': shop_generation,")
    namespace = dict(vars(retained))
    namespace.update(__file__=__file__, fixture_source=fixture_source,
        SCOPE_FINALIZED=True, GREEN_CASES=SWIFT_CASES, DATA_CASES=DATA_CASES,
        HOST_ALIASES=retained.HOST_ALIASES+('NG2RuntimeContinuousTestHooks','ng2_fixture_shop117_rgba'),
        IMMUTABLE_FIXTURES=retained.IMMUTABLE_FIXTURES+('check_runtime115.py','check_runtime116.py',
            'ngg2_runtime116_tests.swift','ngg2_runtime117_tests.swift',
            'ngg2_runtime117_fixture.c','generate_shop117_pixels.py'))
    if feature_off_sha is not None:
        namespace.update(RUNTIME_RED_CASE='single_face_restart', DATA_CASES=(),
            BEFORE_RUNTIME_SHA256=feature_off_sha,
            EXPECTED_RUNTIME_RED_ASSERTION=INITIAL_RUNTIME_RED_ASSERTION)
    exec(compile(source, __file__+'::retained-main', 'exec'), namespace)
    namespace['main']()


def scene_case_body(case, output):
    """Execute exact existing public assertions, then charge one real proof call.

    The original relative-time assertions remain unchanged. The second stage
    charges elapsed native computation to the next actual public begin gate;
    it never changes the fitted phase, W/P or ten millisecond window.
    """
    sys.path.insert(0, str(ROOT))
    from tests import test_native_stationary117 as cut
    from tests import test_native_stationary_support117 as support
    from tests import test_native_controller as native
    from tests.test_native_motion067 import Motion
    gold = case == SCENE_CASES[1]
    cls = support.NativeFixedSupport117Tests if gold else cut.NativeClearProof117Tests
    method = ('test_first_direct_support_stays_fixed_and_funds_only_current_zero' if gold else
        'test_independent_reproof_current_HUD_then_recorded_ACK_duration_and_real_Motion')
    result = unittest.TestResult()
    unittest.TestSuite([cls(method)]).run(result)
    if not result.wasSuccessful() or result.testsRun != 1:
        raise AssertionError('TEST117 selected public C Scene assertion failed: '+str(result.errors+result.failures))
    cls.setUpClass()
    harness = cls('runTest')
    try:
        harness.setUp()
        if gold:
            from copy import deepcopy
            before, fixed, after, old = harness.support_cut()
            harness.cut_observe(fixed,start=10_700_083,end=22_107_292,commit=45_736_417)
            later=deepcopy(fixed);later.signature=before.signature
            harness.cut_observe(later,start=55_814_292,end=66_476_083,commit=90_950_250)
            harness.cut_observe(after,start=138_665_250,end=149_785_167,commit=175_623_458)
        else:
            before, after, old, _ = harness.lose_ready()
        a,b = harness.frame(before),harness.frame(after)
        motion,zero = Motion(),C.c_int32()
        if gold:
            function = harness.lib.ng2_single_gold_dirt_motion_zero
            function.argtypes=[C.POINTER(native.Scene),C.POINTER(native.Scene),C.c_int32,
                C.POINTER(Motion),C.POINTER(C.c_int32)]
            args=(C.byref(a),C.byref(b),old.direction,C.byref(motion),C.byref(zero))
            fixed_frame=harness.frame(fixed)
            support_function=harness.lib.ng2_single_gold_dirt_support_zero
            support_function.argtypes=[C.POINTER(native.Scene),C.POINTER(native.Scene),C.POINTER(native.Scene),C.c_int32]
        else:
            function = harness.lib.ng2_clear_plural_stationary_zero
            args=(C.byref(a),C.byref(b),old.direction)
        started=time.perf_counter_ns(); returned=function(*args)
        support_return=(support_function(C.byref(a),C.byref(fixed_frame),C.byref(b),old.direction) if gold else None)
        elapsed=time.perf_counter_ns()-started
        if returned != 1 or elapsed <= 0 or (gold and (zero.value != 0 or support_return != 1)):
            raise AssertionError('TEST117 cost probe must execute the real nonempty proof')
        # The recorded preparation cut above keeps its original offsets.
        # Charge actual C computation on the procedural FUTURE observations,
        # before public tick selects a ticket. Recomputing Motion at notBefore
        # would insert work which the production begin path does not perform.
        future_costs=[]
        observe=harness.lib.ng2_controller_observe_at
        def charged_observe(*arguments):
            at=harness.now; started=time.perf_counter_ns()
            answer=observe(*arguments); duration=time.perf_counter_ns()-started
            harness.now+=duration
            future_costs.append(dict(entry_ns=at,return_ns=harness.now,cost_ns=duration))
            return answer
        harness.lib.ng2_controller_observe_at=charged_observe
        tick=harness.tick;tick_costs=[]
        def charged_tick(*arguments,**keywords):
            at=harness.now;started=time.perf_counter_ns()
            answer=tick(*arguments,**keywords);duration=time.perf_counter_ns()-started
            harness.now+=duration
            tick_costs.append(dict(entry_ns=at,return_ns=harness.now,cost_ns=duration))
            return answer
        harness.tick=charged_tick
        try: command = harness.reacquire_fixed_cadence(after)
        finally:
            harness.lib.ng2_controller_observe_at=observe;harness.tick=tick
        postcost=harness.now
        latest_source=harness.status().last_capture_start_ns
        source_age=postcost-latest_source
        started=time.perf_counter_ns()
        old_rejected=harness.lib.ng2_controller_begin(harness.engine,old.id,postcost,1,0,1)==0
        old_cost=time.perf_counter_ns()-started
        begin=max(command.not_before_ns,postcost+old_cost)
        if not (elapsed < 100_000_000 and 0 <= source_age <= 150_000_000 and future_costs
                and all(0 < row['cost_ns'] < 100_000_000 for row in future_costs)
                and tick_costs and all(0 < row['cost_ns'] < 100_000_000 for row in tick_costs)
                and begin <= command.deadline_ns
                and begin < harness.parent_deadline
                and old_rejected):
            raise AssertionError('TEST117 real proof cost crosses the original begin/parent gate')
        started=time.perf_counter_ns()
        admitted=harness.lib.ng2_controller_begin(harness.engine,command.id,begin,1,0,1)
        begin_cost=time.perf_counter_ns()-started
        returned_at=begin+begin_cost
        if admitted!=1:
            raise AssertionError('TEST117 existing C begin must still recheck current proof')
        # Actual Runtime re-reads time after ng2_controller_begin, before the
        # gesture. Preserve that second gate: C admission alone is not synth.
        would_synthesize=returned_at<=command.deadline_ns and returned_at<harness.parent_deadline
        if not would_synthesize:
            before_credit=(harness.status().inputs,harness.status().moves)
            if harness.lib.ng2_controller_complete(harness.engine,command.id,returned_at,0)!=1:
                raise AssertionError('TEST117 late actual return must complete without synth')
            if (harness.status().inputs,harness.status().moves)!=before_credit:
                raise AssertionError('TEST117 late actual return cannot gain synth or movement credit')
        record=dict(scope='public_C_Scene_relative_time_cut_plus_measured_native_cost',
            phone_replay=False, private_pixels_used=False, private_scene_used=False,
            original_timing_offsets=True, later_captures='procedural unrecorded future model',
            recorded_preparation_cut_computation_cost='not charged; separate from measured future calls',
            physical_period_ns=native.PERIOD, fit_phase_adjustments=0,
            actual_native_cost_ns=elapsed, not_before_ns=command.not_before_ns,
            deadline_ns=command.deadline_ns, actual_begin_ns=begin,
            publication_after_native_cost_ns=postcost, future_observe_costs=future_costs,
            latest_capture_start_ns=latest_source, source_age_at_publication_after_cost_ns=source_age,
            future_tick_costs=tick_costs, old_callback_cost_ns=old_cost,
            begin_cost_ns=begin_cost, begin_return_ns=returned_at,
            runtime_post_begin_gate_allows_synth=would_synthesize,
            late_return_completed_without_synth=not would_synthesize,
            original_parent_deadline_ns=harness.parent_deadline,
            old_begin_rejected=True, replacement_c_begin_accepted=True,
            actual_synth_sent=False, actual_phone_movement=False,
            direct_original_current_zero=zero.value if gold else None,
            fixed_first_support_zero=support_return,
            separate_scalar_probe_maximum_derivative_views=4 if gold else 2,
            separate_scalar_probe_maximum_raw_translation_scores=146 if gold else 73,
            support_replaced_or_chained=False if gold else None,
            source_age150_worker100='normal Runtime DATA cases independently validate both unchanged gates',
            tests_run=1, assertion_errors=0, assertion_failures=0)
        (output/('runtime117-'+case+'.txt')).write_text('EVIDENCE TEST117 SCENE '+json.dumps(record)+'\nPASS TEST117 CASE '+case+'\n')
        return dict(qualified=True, safety_pass=True, recovery_pass=would_synthesize,
            returncode=0, timed_out=False, scope=record['scope'], evidence=record,
            assertion_failures=[], markers=['PASS TEST117 CASE '+case])
    finally:
        harness.doCleanups(); cls.tearDownClass()


def scene_case(case, output):
    import subprocess
    from unittest.mock import patch
    commands=[]; actual_run=subprocess.run
    def captured_run(argv, *args, **kwargs):
        if not isinstance(argv,(list,tuple)):
            raise ValueError('TEST117 Scene compiler must receive an argv list')
        inputs={}
        for value in argv:
            path=Path(str(value))
            if path.is_file() and path.suffix in ('.c','.h','.o'):
                inputs[str(path.resolve())]=digest(path)
        answer=actual_run(argv,*args,**kwargs)
        commands.append(dict(argv=list(map(str,argv)),input_sha256=inputs,returncode=answer.returncode))
        return answer
    with patch.object(subprocess,'run',side_effect=captured_run):
        result=scene_case_body(case,output)
    modules={}
    for module in tuple(sys.modules.values()):
        raw=getattr(module,'__file__',None)
        if not raw: continue
        path=Path(raw).resolve()
        if path.is_file() and path.suffix=='.py' and path.is_relative_to(ROOT):
            modules[str(path.relative_to(ROOT))]=digest(path)
    result.update(compile_commands=commands,public_python_input_sha256=dict(sorted(modules.items())))
    (output/('runtime117-'+case+'-proof.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--scene-only',action='store_true')
    parser.add_argument('--expect-initial-ui-red',action='store_true')
    args=parser.parse_args();diagnostic=args.scene_only
    if diagnostic and args.expect_initial_ui_red:
        parser.error('initial UI feature-off assertion excludes Scene diagnostic')
    if diagnostic: sys.argv.remove('--scene-only')
    if not CURRENT_SCOPE_FINALIZED and not diagnostic:
        raise SystemExit('TEST117 exact scope pending; no final Mac fixture executed')
    upstream,output=args.upstream.resolve(),args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    native=upstream/'LoopCtrlUITests'
    # This is the same sealed current source matched by the Swift builder.
    for name in ('NG2Controller.c','NG2Perception.c','NG2Navigation.c','NG2Beat.c'):
        if (native/name).read_bytes() != (HERE/'ngg2'/name).read_bytes():
            raise ValueError('TEST117 Scene source differs from sealed input: '+name)
    if not diagnostic and not shutil.which('clang'):
        raise SystemExit('clang unavailable; no TEST117 native cost assertion executed')
    mutation=None
    if args.expect_initial_ui_red:
        current=(native/'NG2Runtime.swift').read_bytes()
        if current != (HERE/'ngg2/NG2Runtime.swift').read_bytes():
            raise ValueError('feature-off base differs from sealed current Runtime')
        text=current.decode()
        if text.count(INITIAL_ENABLE_CALL)!=1:
            raise ValueError('initial UI feature-off requires exactly one enable call')
        disabled=text.replace(INITIAL_ENABLE_CALL,'1').encode()
        mutation=dict(schema='test117-current-initial-ui-feature-off-v1',
            original_runtime_sha256=hashlib.sha256(current).hexdigest(),
            mutant_runtime_sha256=hashlib.sha256(disabled).hexdigest(),
            exact_replacement_count=1,original_expression=INITIAL_ENABLE_CALL,
            replacement_expression='1',other_bytes_unchanged=True,
            current_flag_parser_and_provenance_unchanged=True)
        with tempfile.TemporaryDirectory(prefix='test117-initial-ui-feature-off-') as folder:
            path=Path(folder)/'NG2Runtime-feature-off.swift';path.write_bytes(disabled)
            (output/'runtime117-initial-feature-off.swift').write_bytes(disabled)
            original_argv=sys.argv[:]
            try:
                sys.argv=[sys.argv[0],str(upstream),str(output),'--expect-runtime-red','--before-runtime',str(path)]
                runtime_main(feature_off_sha=mutation['mutant_runtime_sha256'])
            finally: sys.argv=original_argv
    elif not diagnostic: runtime_main()
    receipt=output/'runtime117-result.json'
    proof=json.loads(receipt.read_bytes()) if receipt.exists() and not diagnostic else dict(cases={})
    if args.expect_initial_ui_red:
        if not proof.get('expected_runtime_red_qualified'):
            raise SystemExit('TEST117 initial UI feature-off assertion Red not qualified')
        lines=(output/'runtime117-single_face_restart.txt').read_text().splitlines()
        rows=[json.loads(line.split(' INITIAL_UI117 ',1)[1]) for line in lines
            if line.startswith('EVIDENCE TEST116 INITIAL_UI117 ')]
        if (len(rows)!=1 or rows[0].get('actual_start_accepted') is not True
                or rows[0].get('accepted_frames',0)<=0 or rows[0].get('last_capture_id',0)<=0
                or rows[0].get('actual_command_kind')!=1 or rows[0].get('actual_source_capture_id',0)<=0
                or rows[0].get('actual_source_start_ns',0)<=0 or rows[0].get('restart_count')!=0
                or proof.get('current_runtime_sha256')!=mutation['original_runtime_sha256']
                or proof.get('compiled_runtime_sha256')!=mutation['mutant_runtime_sha256']):
            raise SystemExit('TEST117 UI Red lacks accepted-start/capture/actual RESUME prerequisites')
        proof.update(scope='current Runtime parser and provenance, exact one-call feature-off mutant; accepted root PAUSE emits RESUME before any restart; no phone acceptance',
            final_scope_finalized=CURRENT_SCOPE_FINALIZED, phone_acceptance=False,
            feature_off_mutation=mutation,semantic_ui_preconditions=rows[0],initial_ui_assertion_red_qualified=True)
        receipt.write_text(json.dumps(proof,indent=2)+'\n')
        return
    # The retained fixtures compile production sources with their required
    # O0/O2 split. Existing public Scene helpers use cc; on Mac the actual
    # toolchain's cc is Apple clang, recorded and checked rather than assumed.
    import subprocess
    compiler=subprocess.run(['cc','--version'],capture_output=True,text=True,check=True)
    if not diagnostic and 'clang' not in compiler.stdout.lower()+compiler.stderr.lower():
        raise SystemExit('TEST117 Mac Scene cost profile requires clang cc')
    os.environ['NECRO117_STATIONARY_CORE']=str(native)
    for case in SCENE_CASES:
        proof['cases'][case]=scene_case(case,output)
        print(case+(': productive Green' if proof['cases'][case]['recovery_pass'] else ': safe deadline refusal only'),flush=True)
    proof.update(schema='ngg2-runtime117-host-proof-v1',
        scope='three actual Swift Runtime/normal RGBA/Ring/Spool procedural-world cases; two public C Scene cuts with measured host cost; no phone acceptance',
        required_cases=list(GREEN_CASES), final_scope_finalized=CURRENT_SCOPE_FINALIZED,
        diagnostic_only=diagnostic, product_pass=(not diagnostic and tuple(proof['cases'])==GREEN_CASES
            and all(row['qualified'] for row in proof['cases'].values())
            and all(proof['cases'][case]['recovery_pass'] for case in SCENE_CASES)),
        productive_recovery_cases={case:proof['cases'][case]['recovery_pass'] for case in SCENE_CASES},
        scene_compiler_identity=compiler.stdout+compiler.stderr,
        scene_source_sha256={name:digest(native/name) for name in ('NG2Controller.c','NG2Perception.c','NG2Navigation.c','NG2Beat.c')})
    receipt.write_text(json.dumps(proof,indent=2)+'\n')
    if not diagnostic and not proof['product_pass']:
        raise SystemExit('TEST117 final boundary proof incomplete')
    print('PASS TEST117 '+('C Scene diagnostic only' if diagnostic else 'five selected boundary cases'))


if __name__=='__main__': main()
