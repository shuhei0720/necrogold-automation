"""Execute TEST059's public-C assertion against fixed old, current and faulty C.

Synthetic HUD/clock/texture: these are controller contract checks, not game E2E.
Compilation/setup failures are never accepted as behavioral Red.
"""
import argparse
import hashlib
import importlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASELINE = 'f65c45d5963eb6440bca02604b164cbb670b90b9'
BASELINE_SHA = '61df3ba3edceadc1eb76114485ce836edbb2b90ac327bb119decb74760b3c47f'
METHOD = 'test_next_unreserved_slot_candidate_uses_current_corrected_target_window'
ASSERTION = 'new_unreserved_slot_candidate_uses_current_corrected_target_window'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
    module = importlib.import_module('test_native_controller')
    core = HERE/'ngg2'
    current = (core/'NG2Controller.c').read_bytes()
    old = subprocess.check_output(['git', 'show', BASELINE+':patches/loopctrl/ngg2/NG2Controller.c'], cwd=ROOT)
    if hashlib.sha256(old).hexdigest() != BASELINE_SHA:
        raise ValueError('fixed_TEST058_controller_hash')
    anchor = b'    p->next_deadline=not_before+10000000;'
    if current.count(anchor) != 1:
        raise ValueError('TEST059_rollback_mutation_anchor')
    mutant = current.replace(anchor, b'    p->next_deadline=p->next_nominal-p->s.lead_ns+10000000;')
    variants = [('baseline-red', old, False), ('current-green', current, True), ('rollback-red', mutant, False)]
    records = {}
    for name, source, positive in variants:
        with tempfile.TemporaryDirectory(prefix='next-slot-') as folder:
            staged = Path(folder)/'core'
            shutil.copytree(core, staged)
            (staged/'NG2Controller.c').write_bytes(source)
            module.CORE = staged
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                unittest.TestSuite([module.NativeControllerTests(METHOD)]))
            log = stream.getvalue()
            (args.output/(name+'.txt')).write_text(log)
            if result.testsRun != 1 or result.errors or result.skipped:
                raise RuntimeError(name+': compile/setup/skipped result is not evidence\n'+log)
            if positive:
                if not result.wasSuccessful():
                    raise RuntimeError(name+': current public-C assertion failed\n'+log)
            elif len(result.failures) != 1 or ASSERTION not in result.failures[0][1]:
                raise RuntimeError(name+': required semantic assertion Red not observed\n'+log)
            records[name] = {'compiled': True, 'tests': 1, 'semantic_result': 'green' if positive else 'red',
                'controller_sha256': hashlib.sha256(source).hexdigest(), 'assertion': ASSERTION,
                'source_commit': BASELINE if name == 'baseline-red' else None}
    report = {'schema': 'test059-next-slot-contract-v1', 'variants': records,
        'fixture_method': METHOD, 'fixture_sha256': hashlib.sha256((ROOT/'tests/test_native_controller.py').read_bytes()).hexdigest(),
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(core.glob('*')) if p.is_file()},
        'legacy_runtime_faults': 'separate unchanged inventory59 plus TEST058 faults2',
        'device_test': 'not_run', 'scope': 'real C public APIs with synthetic HUD/clock; no missing future frame replay'}
    (args.output/'next-slot-contract.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS TEST059 fixed old assertion Red / current Green / independent rollback Red')


if __name__ == '__main__':
    main()
