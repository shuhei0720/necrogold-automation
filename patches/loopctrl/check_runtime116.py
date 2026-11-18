#!/usr/bin/env python3
"""TEST116 selected actual Runtime checks using the immutable TEST115 builder.

Only the executable fixture and proof labels are replaced. The retained
compiler/build/source binding logic is used once, without eleven near-copy
checker files. A pinned old Runtime body is never edited for assertion Red.
"""
import hashlib
import inspect
from pathlib import Path
import sys

import check_runtime115 as retained

HERE = Path(__file__).resolve().parent
CURRENT_SCOPE_FINALIZED = False
GREEN_CASES = ('new_mode',)
BEFORE_RUNTIME_SHA256 = 'e655aa10f0ba48a9e2f719e25a5cbd9c7f5c69f6e907de0ac1bcae9da228dbe0'
EXPECTED_RUNTIME_RED_ASSERTION = 'FAIL test116_continuous_native_mode_is_admitted_without_old_pause_yield'


def fixture_source():
    prior = retained.fixture_source()
    marker = '\nlet root115 = FileManager.default.temporaryDirectory'
    if prior.count(marker) != 1:
        raise ValueError('exact retained TEST115 executable boundary')
    return prior.split(marker)[0] + '\n' + (HERE/'ngg2_runtime116_tests.swift').read_text()


def main():
    if not CURRENT_SCOPE_FINALIZED and '--expect-runtime-red' not in sys.argv[1:]:
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
    namespace = dict(vars(retained))
    namespace.update(__file__=__file__, fixture_source=fixture_source,
        SCOPE_FINALIZED=True, GREEN_CASES=GREEN_CASES, DATA_CASES=(),
        RUNTIME_RED_CASE='new_mode', BEFORE_RUNTIME_SHA256=BEFORE_RUNTIME_SHA256,
        EXPECTED_RUNTIME_RED_ASSERTION=EXPECTED_RUNTIME_RED_ASSERTION,
        IMMUTABLE_FIXTURES=retained.IMMUTABLE_FIXTURES + ('check_runtime115.py', 'ngg2_runtime116_tests.swift'))
    exec(compile(source, __file__+'::retained-main', 'exec'), namespace)
    namespace['main']()


if __name__ == '__main__':
    main()
