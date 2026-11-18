#!/usr/bin/env python3
"""TEST116 selected actual Runtime checks using the immutable TEST115 builder.

Only the executable fixture and proof labels are replaced. The retained
compiler/build/source binding logic is used once, without eleven near-copy
checker files. A pinned old Runtime body is never edited for assertion Red.
"""
import hashlib
import inspect
import json
from pathlib import Path
import sys

import check_runtime115 as retained

HERE = Path(__file__).resolve().parent
CURRENT_SCOPE_FINALIZED = False
DIAGNOSTIC_CASES = ('new_mode', 'normal_chain')
GREEN_CASES = ('new_mode', 'normal_chain', 'candidate', 'late_hint',
    'cancel_before_swap', 'cancel_after_swap', 'bootstrap_cancel', 'bootstrap_deadline',
    'qualified_cancel', 'successor_owner', 'successor_locked', 'successor_foreground',
    'main_return', 'root_clock_before', 'root_clock_equal', 'root_clock_late',
    'root_clock_ticket_before', 'producer', 'classification_commit', 'capture_decode',
    'capture_control', 'seal_producer', 'seal_commit', 'writer:checkpoint',
    'commit:checkpoint', 'writer:intent', 'commit:intent', 'writer:outcome',
    'commit:outcome', 'writer:terminal', 'commit:terminal')
DATA_CASES = ('normal_chain', 'candidate', 'late_hint', 'cancel_before_swap',
    'cancel_after_swap', 'qualified_cancel', 'successor_owner', 'successor_locked',
    'successor_foreground', 'producer', 'classification_commit', 'capture_decode',
    'capture_control', 'seal_producer', 'seal_commit', 'writer:checkpoint',
    'commit:checkpoint', 'writer:intent', 'commit:intent', 'writer:outcome',
    'commit:outcome', 'writer:terminal', 'commit:terminal')
BEFORE_RUNTIME_SHA256 = 'e655aa10f0ba48a9e2f719e25a5cbd9c7f5c69f6e907de0ac1bcae9da228dbe0'
EXPECTED_RUNTIME_RED_ASSERTION = 'FAIL test116_continuous_native_mode_is_admitted_without_old_pause_yield'
ADMISSION_ENTRY_SHA256 = 'd3cab992b2883544d38e11b47b906ccd3fd6af8f7f98a8603d31395a9402e541'


def fixture_source(*, admission=False):
    prior = retained.fixture_source()
    marker = '\nlet root115 = FileManager.default.temporaryDirectory'
    if prior.count(marker) != 1:
        raise ValueError('exact retained TEST115 executable boundary')
    path = HERE/('ngg2_runtime116_admission.swift' if admission else 'ngg2_runtime116_tests.swift')
    raw = path.read_bytes()
    if admission and hashlib.sha256(raw).hexdigest() != ADMISSION_ENTRY_SHA256:
        raise ValueError('TEST116 original admission assertion entry changed')
    return prior.split(marker)[0] + '\n' + raw.decode()


def main():
    admission = '--expect-runtime-red' in sys.argv[1:]
    diagnostic = '--diagnostic' in sys.argv[1:]
    if diagnostic:
        if sys.argv.count('--diagnostic') != 1 or any(flag in sys.argv[1:] for flag in
                ('--expect-runtime-red', '--before-runtime', '--expect-red', '--before-controller')):
            raise SystemExit('TEST116 diagnostic is separate from the pinned assertion Red')
        sys.argv.remove('--diagnostic')
    if not CURRENT_SCOPE_FINALIZED and not admission and not diagnostic:
        raise SystemExit('TEST116 Green Runtime scope is pending; no fixture executed')
    # The original builder is kept byte-for-byte in its historical file. This
    # explicit adapter changes only version labels in its main executable;
    # every native/Swift compiler call and proof predicate is retained.
    source = inspect.getsource(retained.main)
    if source.count('def main():') != 1 or 'runtime115-result.json' not in source:
        raise ValueError('retained TEST115 main boundary changed')
    source = (source.replace('runtime115-', 'runtime116-')
        .replace("'runtime115'", "'runtime116'")
        .replace('TEST115', 'TEST116').replace('test115_', 'test116_'))
    old_reader = "fixture_inputs['check_runtime115.py'] = digest(Path(__file__).resolve())"
    if source.count(old_reader) != 1:
        raise ValueError('retained builder identity receipt boundary changed')
    source = source.replace(old_reader, "fixture_inputs['check_runtime116.py'] = digest(Path(__file__).resolve())")
    if diagnostic:
        source = source.replace('PASS TEST116 selected current Runtime callbacks',
            'PASS TEST116 diagnostic callbacks only; final scope pending')
    namespace = dict(vars(retained))
    cases = ('new_mode',) if admission else DIAGNOSTIC_CASES if diagnostic else GREEN_CASES
    namespace.update(__file__=__file__, fixture_source=lambda: fixture_source(admission=admission),
        SCOPE_FINALIZED=True, GREEN_CASES=cases, DATA_CASES=DATA_CASES,
        HOST_ALIASES=retained.HOST_ALIASES+('NG2RuntimeContinuousTestHooks',),
        RUNTIME_RED_CASE='new_mode', BEFORE_RUNTIME_SHA256=BEFORE_RUNTIME_SHA256,
        EXPECTED_RUNTIME_RED_ASSERTION=EXPECTED_RUNTIME_RED_ASSERTION,
        IMMUTABLE_FIXTURES=retained.IMMUTABLE_FIXTURES + ('check_runtime115.py',
            'ngg2_runtime116_admission.swift', 'ngg2_runtime116_tests.swift'))
    exec(compile(source, __file__+'::retained-main', 'exec'), namespace)
    try:
        namespace['main']()
    finally:
        if diagnostic:
            # Retained parser already validates both positional paths. This
            # final annotation cannot turn failed cases into a diagnostic pass.
            args = sys.argv[1:]
            output = Path(args[1]) if len(args) >= 2 else None
            receipt = output/'runtime116-result.json' if output else None
            if receipt is not None and receipt.is_file():
                proof = json.loads(receipt.read_bytes())
                proof.update(diagnostic_only=True, final_scope_finalized=CURRENT_SCOPE_FINALIZED,
                    diagnostic_pass=proof.get('product_pass') is True,
                    product_pass=False, limitation='Two fixed callbacks only; remaining TEST116 Runtime scope has not executed.')
                receipt.write_text(json.dumps(proof,indent=2)+'\n')


if __name__ == '__main__':
    main()
