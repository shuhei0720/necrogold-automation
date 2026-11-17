#!/usr/bin/env python3
"""Selected TEST110 actual Swift Spool quota and filesystem fixture; no phone input."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'ngg2/NG2CycleSpool.swift'
FIXTURE = HERE / 'ngg2_cycle_spool110_tests.swift'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--swiftc', default='swiftc')
    parser.add_argument('--fault-red', action='store_true')
    args = parser.parse_args()
    compiler = shutil.which(args.swiftc)
    if compiler is None:
        raise SystemExit('Swift unavailable; TEST110 Spool assertions not executed')
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    original = SOURCE.read_text()
    compiler_identity = subprocess.run([compiler, '--version'], text=True, capture_output=True, check=True)
    results = {}
    with tempfile.TemporaryDirectory(prefix='spool110-') as temporary:
        stage = Path(temporary)
        source = stage / 'NG2CycleSpool.swift'; fixture = stage / 'main.swift'; binary = stage / 'fixture'
        fixture.write_bytes(FIXTURE.read_bytes())

        def execute(content, name, case=None):
            source.write_text(content)
            command = [compiler, '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', str(source), str(fixture), '-o', str(binary)]
            compiled = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (output / (name + '-compile.txt')).write_text(compiled.stdout + compiled.stderr)
            if compiled.returncode:
                raise SystemExit('Swift compile failure is not assertion Red:\n' + compiled.stdout + compiled.stderr)
            result = subprocess.run([str(binary), *([case] if case else [])], capture_output=True, text=True, timeout=180)
            (output / (name + '-tests.txt')).write_text(result.stdout + result.stderr)
            results[name] = {'returncode': result.returncode, 'source_sha256': hashlib.sha256(content.encode()).hexdigest(),
                             'compile_errors': 0, 'command': command, 'selected_case': case}
            return result

        if args.fault_red:
            marker = 'guard recordList.count + 1 + reservedRecords <= 512 else { throw Failure.limit("records") }'
            if original.count(marker) != 1:
                raise SystemExit('record reservation mutation boundary changed')
            red = execute(original.replace(marker, 'guard recordList.count + 1 <= 512 else { throw Failure.limit("records") }'),
                          'spool110-record-credit-fault-red', 'record_steal')
            failures = [line for line in red.stdout.splitlines() if line.startswith('FAIL ')]
            if red.returncode != 1 or failures != ['FAIL accepted record512_reserved_slots_not_stolen']:
                raise SystemExit('Meaningful record-credit fault Red missing:\n' + red.stdout + red.stderr)
            rollback = 'irregularBudget = nil; finalBudget = previousFinal'
            if original.count(rollback) != 1:
                raise SystemExit('preflight reservation rollback mutation boundary changed')
            red = execute(original.replace(rollback, '_ = previousFinal'),
                          'spool110-preflight-rollback-fault-red', 'space_rollback')
            failures = [line for line in red.stdout.splitlines() if line.startswith('FAIL ')]
            if red.returncode != 1 or failures != ['FAIL preflight_space_failure_rolls_back_unreturned_token']:
                raise SystemExit('Meaningful preflight rollback fault Red missing:\n' + red.stdout + red.stderr)
        green = execute(original, 'spool110-production-green')
        print(green.stdout, end='')
        if green.returncode or not green.stdout.strip().endswith(
                'PASS TEST110 Spool actual filesystem reservation/dedup/record512/finalization/fault/recovery'):
            raise SystemExit(green.stdout + green.stderr or 'Spool110 assertion failure')
    (output / 'spool110-evidence.json').write_text(json.dumps({
        'scope': 'actual Swift/filesystem plus deterministic space and FS-fault hooks; no device acceptance',
        'source_sha256': hashlib.sha256(original.encode()).hexdigest(),
        'fixture_sha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'compiler': compiler_identity.stdout + compiler_identity.stderr,
        'fault_red_is_postimplementation_sensitivity': args.fault_red, 'results': results}, indent=2) + '\n')


if __name__ == '__main__':
    main()
