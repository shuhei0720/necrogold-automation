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
import re
import sys

import check_runtime115 as retained

HERE = Path(__file__).resolve().parent
CURRENT_SCOPE_FINALIZED = True
DIAGNOSTIC_CASES = ('new_mode', 'normal_chain')
GREEN_CASES = ('new_mode', 'normal_chain', 'history_mode', 'nil_core', 'candidate', 'late_hint',
    'cancel_before_swap', 'cancel_after_swap', 'bootstrap_cancel', 'bootstrap_deadline',
    'qualified_cancel', 'successor_owner', 'successor_locked', 'successor_foreground',
    'main_return', 'heartbeat', 'root_clock_before', 'root_clock_equal', 'root_clock_late',
    'root_clock_ticket_before', 'producer', 'classification_commit', 'capture_decode',
    'capture_control', 'capture_thread_return', 'seal_producer', 'seal_commit', 'writer:checkpoint',
    'commit:checkpoint', 'writer:intent', 'commit:intent', 'writer:outcome',
    'commit:outcome', 'writer:terminal', 'commit:terminal', 'post_begin_clock')
DATA_CASES = ('normal_chain', 'history_mode', 'candidate', 'late_hint', 'cancel_before_swap',
    'cancel_after_swap', 'qualified_cancel', 'successor_owner', 'successor_locked',
    'successor_foreground', 'producer', 'classification_commit', 'capture_decode',
    'capture_control', 'capture_thread_return', 'seal_producer', 'seal_commit', 'writer:checkpoint',
    'commit:checkpoint', 'writer:intent', 'commit:intent', 'writer:outcome',
    'commit:outcome', 'writer:terminal', 'commit:terminal')
BEFORE_RUNTIME_SHA256 = 'e655aa10f0ba48a9e2f719e25a5cbd9c7f5c69f6e907de0ac1bcae9da228dbe0'
EXPECTED_RUNTIME_RED_ASSERTION = 'FAIL test116_continuous_native_mode_is_admitted_without_old_pause_yield'
ADMISSION_ENTRY_SHA256 = 'd3cab992b2883544d38e11b47b906ccd3fd6af8f7f98a8603d31395a9402e541'


def artifact_case_slug(case):
    if not isinstance(case, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', case):
        raise ValueError('TEST116 artifact case identity is empty')
    return case if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', case) else 'case-'+case.encode('utf-8').hex()


def finalize_artifact_paths(output, proof, cases):
    """Rename transport paths only; logical cases and all assertion bytes stay exact."""
    slugs = {case: artifact_case_slug(case) for case in cases}
    if len(slugs) != len(cases) or len(set(slugs.values())) != len(cases):
        raise ValueError('TEST116 artifact case slugs collide')
    mapped = {}
    for case, slug in slugs.items():
        paths = (('runtime116-'+case+'.txt', 'runtime116-'+slug+'.txt'),
            ('synthetic-runtime-exports/'+case, 'synthetic-runtime-exports/'+slug))
        for original, safe in paths:
            source, destination = output/original, output/safe
            if source.is_symlink() or destination.is_symlink():
                raise ValueError('TEST116 artifact path is a symlink')
            if original != safe and source.exists():
                if destination.exists():
                    raise ValueError('TEST116 artifact destination already exists')
                source.rename(destination)
        mapped[case] = dict(slug=slug, log=paths[0][1], export_directory=paths[1][1],
            original_log=paths[0][0], original_export_directory=paths[1][0])
    def safe_relative(name):
        for row in mapped.values():
            old = row['original_export_directory']+'/'
            if name.startswith(old):
                return row['export_directory']+'/'+name[len(old):]
        return name
    exports = proof.get('synthetic_exports', {})
    rewritten = {safe_relative(name): digest for name, digest in exports.items()}
    if len(rewritten) != len(exports):
        raise ValueError('TEST116 remapped export identities collide')
    for name, digest in rewritten.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or not name.startswith('synthetic-runtime-exports/'):
            raise ValueError('TEST116 export receipt escaped the artifact root')
        if hashlib.sha256((output/name).read_bytes()).hexdigest() != digest:
            raise ValueError('TEST116 renamed export bytes differ')
    for path in output.rglob('*'):
        if any(character in path.relative_to(output).as_posix() for character in ':"<>|?*\\'):
            raise ValueError('TEST116 unsupported artifact path remains')
    logs = {row['log']: hashlib.sha256((output/row['log']).read_bytes()).hexdigest()
        for row in mapped.values() if (output/row['log']).is_file()}
    transport = dict(schema='test116-artifact-paths-v1', case_paths=mapped,
        case_log_sha256=logs, logical_case_identities_unchanged=True,
        unsafe_case_slug_encoding='case- followed by the original UTF-8 hexadecimal bytes')
    raw = (json.dumps(transport, indent=2)+'\n').encode()
    (output/'runtime116-artifact-paths.json').write_bytes(raw)
    proof.update(synthetic_exports=rewritten, artifact_case_paths=mapped,
        artifact_path_map_sha256=hashlib.sha256(raw).hexdigest(), artifact_paths_safe=True)


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
        args = sys.argv[1:]
        output = Path(args[1]) if len(args) >= 2 else None
        receipt = output/'runtime116-result.json' if output else None
        if receipt is not None and receipt.is_file():
            proof = json.loads(receipt.read_bytes())
            finalize_artifact_paths(output, proof, cases)
        if diagnostic:
            # Retained parser already validates both positional paths. This
            # final annotation cannot turn failed cases into a diagnostic pass.
            if receipt is not None and receipt.is_file():
                proof.update(diagnostic_only=True, final_scope_finalized=CURRENT_SCOPE_FINALIZED,
                    diagnostic_pass=proof.get('product_pass') is True,
                    product_pass=False, limitation='Two fixed callbacks only; remaining TEST116 Runtime scope has not executed.')
        if receipt is not None and receipt.is_file():
            receipt.write_text(json.dumps(proof,indent=2)+'\n')


if __name__ == '__main__':
    main()
