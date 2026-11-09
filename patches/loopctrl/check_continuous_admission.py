"""Check TEST060 public C admission against fixed old/current/three faults.

Synthetic clock and textures prove controller contracts, not game acceptance.
Compile/setup errors and skipped cases are never accepted as behavioral Red.
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
BASELINE = '5ef0ec3ab2c534b3dda05c65ec9613871a305352'
BASELINE_SHA = 'b3fe3644eb5d3041f18bafa1771186e5a1e091c99e55468f7ccf73d28d2e0a08'
METHODS = {
    'test_continuous_first_reservation_waits_until_publication_window':
        'continuous_first_reservation_requires_publication_100ms',
    'test_continuous_first_reservation_requires_source_start_window':
        'continuous_first_reservation_requires_source_start_200ms',
}
EXPIRY_METHOD = 'test_continuous_candidate_expiry_precedes_delayed_commit_tick'
EXPIRY_ASSERTION = 'continuous_unreserved_candidate_expiry_precedes_commit_tick'
ANCHORS = {
    'publication-disabled': b'            if(now<not_before&&not_before-now>CONTINUOUS_PUBLICATION)return 0;',
    'source-window-disabled': b'            if(p->s.last_capture_start_ns<not_before&&not_before-p->s.last_capture_start_ns>CONTINUOUS_SOURCE)return 0;',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
    module = importlib.import_module('test_native_controller')
    core = HERE/'ngg2'
    current = (core/'NG2Controller.c').read_bytes()
    old = subprocess.check_output(
        ['git', 'show', BASELINE+':patches/loopctrl/ngg2/NG2Controller.c'], cwd=ROOT)
    if hashlib.sha256(old).hexdigest() != BASELINE_SHA:
        raise ValueError('fixed_TEST059_controller_hash')
    all_methods = {**METHODS, EXPIRY_METHOD: EXPIRY_ASSERTION}
    variants = [
        ('baseline-red', old, set(METHODS), METHODS),
        ('current-green', current, set(), all_methods),
    ]
    for name, method in zip(ANCHORS, METHODS):
        anchor = ANCHORS[name]
        if current.count(anchor) != 1:
            raise ValueError('TEST060_unique_mutation_anchor_'+name)
        mutant = current.replace(anchor, b'            /* TEST060 injected missing admission gate. */')
        variants.append((name+'-red', mutant, {method}, all_methods))
    expiry_anchor = b'    return now>deadline;'
    if current.count(expiry_anchor) != 1:
        raise ValueError('TEST060_unique_expiry_mutation_anchor')
    expiry_mutant = current.replace(expiry_anchor, b'    (void)now; (void)deadline; return 0;')
    variants.append(('candidate-expiry-disabled-red', expiry_mutant, {EXPIRY_METHOD}, all_methods))
    records = {}
    for name, source, expected, methods in variants:
        with tempfile.TemporaryDirectory(prefix='continuous-admission-') as folder:
            staged = Path(folder)/'core'
            shutil.copytree(core, staged)
            (staged/'NG2Controller.c').write_bytes(source)
            module.CORE = staged
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                unittest.TestSuite(module.NativeControllerTests(method) for method in methods))
            log = stream.getvalue()
            (args.output/(name+'.txt')).write_text(log)
            if result.testsRun != len(methods) or result.errors or result.skipped:
                raise RuntimeError(name+': compile/setup/skipped result is not evidence\n'+log)
            failures = {}
            for case, traceback in result.failures:
                method = case.id().rsplit('.', 1)[-1]
                if method not in methods or methods[method] not in traceback or method in failures:
                    raise RuntimeError(name+': unexpected assertion failure\n'+log)
                failures[method] = methods[method]
            if set(failures) != expected or result.wasSuccessful() != (not expected):
                raise RuntimeError(name+': required exact semantic result not observed\n'+log)
            records[name] = {
                'compiled': True, 'tests': result.testsRun,
                'semantic_result': 'red' if expected else 'green',
                'errors': 0, 'skipped': 0, 'assertion_failures': failures,
                'fixture_methods': methods,
                'controller_sha256': hashlib.sha256(source).hexdigest(),
                'source_commit': BASELINE if name == 'baseline-red' else None,
            }
    report = {
        'schema': 'test060-continuous-admission-contract-v1',
        'variants': records, 'fixture_methods': all_methods,
        'fixture_sha256': hashlib.sha256((ROOT/'tests/test_native_controller.py').read_bytes()).hexdigest(),
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(core.glob('*')) if p.is_file()},
        'legacy_faults_separate': 'Runtime59 plus TEST058 faults2 plus TEST059 C rollback1',
        'device_test': 'not_run',
        'scope': 'public C with synthetic clock/texture; no missing recorded future frames',
    }
    (args.output/'continuous-admission-contract.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS TEST060 fixed old admission Red / current Green / two admission and one expiry faults Red')


if __name__ == '__main__':
    main()
