#!/usr/bin/env python3
"""TEST116 actual Swift/FS quota and terminal seal; no input or device acceptance.

The old-source adapter only exposes future method signatures around untouched
TEST115 Spool primitives. Its assertion Red proves an unimplemented NEW storage
contract, not that TEST115 exposed a continuous campaign to phone callers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
BASELINE_SHA = '074d76fc732a2287d14d8dd11256ac4d63462974556006b518f52ee66eefe84f'
GREEN_CASES = ('quota','slot','seal','export','fault','alias','recovered_quota',
    'diagnostic_unknown','record_integrity','preseal','alias_integrity','published_quota','orphan_accounting','orphan_quota','damaged_owner','recovery_namespace')
EXPECTED_RED = {
    'quota': 'FAIL accepted campaign_write_steals_other_slot_reservation',
    'slot': 'FAIL accepted campaign_unpublished_slot17',
    'seal': 'FAIL accepted control_frame_after_continuation_seal',
    'alias': 'FAIL sealed_original_png_readonly_alias',
    'recovered_quota': 'FAIL accepted recovered_export_steals_other_slot_reservation',
    'orphan_quota': 'FAIL accepted partial_child_export_steals_parent_cohort_reservation',
    'orphan_accounting': 'FAIL accepted second_atomic_part_exceeds_same_slot_two_MiB',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--swiftc', default='swiftc')
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--before-spool', type=Path)
    args = parser.parse_args()
    compiler = shutil.which(args.swiftc)
    if compiler is None:
        raise SystemExit('Swift unavailable; no TEST116 semantic assertion executed')
    if args.baseline_only != bool(args.before_spool):
        raise SystemExit('--baseline-only requires exactly one --before-spool')
    source = args.before_spool if args.baseline_only else HERE/'ngg2/NG2CycleSpool.swift'
    original = source.read_bytes()
    if args.baseline_only and hashlib.sha256(original).hexdigest() != BASELINE_SHA:
        raise SystemExit('TEST116 Spool baseline bytes differ from pinned TEST115')
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    identity = subprocess.run([compiler, '--version'], text=True, capture_output=True, check=True)
    rows = {}
    with tempfile.TemporaryDirectory(prefix='spool116-') as temporary:
        stage = Path(temporary)
        actual = stage/'NG2CycleSpool.swift'; actual.write_bytes(original)
        fixture = stage/'main.swift'; fixture.write_bytes((HERE/'ngg2_cycle_spool116_tests.swift').read_bytes())
        command = [compiler, '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', str(actual)]
        if args.baseline_only:
            adapter = stage/'before-adapter.swift'
            adapter.write_bytes((HERE/'ngg2_cycle_spool116_before_adapter.swift').read_bytes())
            command.append(str(adapter))
        command.extend([str(fixture), '-o', str(stage/'fixture')])
        result = subprocess.run(command, text=True, capture_output=True, timeout=180)
        (output/'compile.txt').write_text(result.stdout+result.stderr)
        if result.returncode:
            raise SystemExit('Compile failure is not assertion Red:\n'+result.stdout+result.stderr)
        for case in EXPECTED_RED if args.baseline_only else GREEN_CASES:
            value = subprocess.run([str(stage/'fixture'), case], text=True, capture_output=True, timeout=180)
            (output/(case+'.txt')).write_text(value.stdout+value.stderr)
            failures = [line for line in value.stdout.splitlines() if line.startswith('FAIL ')]
            rows[case] = dict(returncode=value.returncode, compile_errors=0, failures=failures)
            if args.baseline_only:
                if value.returncode != 1 or failures != [EXPECTED_RED[case]]:
                    raise SystemExit('Wrong TEST116 Spool assertion Red for '+case+':\n'+value.stdout+value.stderr)
            elif value.returncode or value.stdout.strip().splitlines()[-1:] != ['PASS TEST116 Spool '+case]:
                raise SystemExit(value.stdout+value.stderr or 'TEST116 Spool assertion failure')
            print(value.stdout, end='')
    receipt = dict(schema='test116-spool-evidence-v1', baseline_only=args.baseline_only,
        baseline_adapter_is_test_only=True, green_cases=list(GREEN_CASES), source_sha256=hashlib.sha256(original).hexdigest(),
        fixture_sha256=hashlib.sha256((HERE/'ngg2_cycle_spool116_tests.swift').read_bytes()).hexdigest(),
        adapter_sha256=hashlib.sha256((HERE/'ngg2_cycle_spool116_before_adapter.swift').read_bytes()).hexdigest(),
        compiler=identity.stdout+identity.stderr, command=command, results=rows,
        device_acceptance=False, input_authority=False)
    (output/'spool116-evidence.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__ == '__main__':
    main()
