#!/usr/bin/env python3
"""Actual Swift/FS startup bounds; identical temporary counters on both sources.

No product hooks, parser substitutions, mock filesystem, or future API adapters.
The baseline must fail the specified bound after semantic/parity checks pass.
Compilation/toolchain failure never counts as assertion Red.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
BASELINE_SHA = '242cdabfaa3ce99fdebc34d15a88056dc74140681e692c43d7fad2945795682b'
CASES = {
    'work': 'FAIL startup_metadata_loads_linear',
    'retained': 'FAIL startup_recovered_sources_bounded',
    'hash': 'FAIL artifact_hash_scratch_64KiB',
}
REGRESSIONS = ('116-published_quota', '116-damaged_owner', '116-orphan_quota', '116-orphan_accounting',
    '116-alias_integrity', '116-recovered_quota', '116-recovery_namespace', '094-changed_snapshot')
COUNTERS = '''
// Temporary TEST126 observation only; this code is never packaged.
enum NG2DiscoveryMetrics126 {
    static var metadataLoads = 0
    static var liveSources = 0
    static var peakSources = 0
    static var hashDepth = 0
    static var hashScratchBytes = 0
    static func opened() { liveSources += 1; peakSources = max(peakSources, liveSources) }
    static func closed() { liveSources -= 1 }
    static func allocated(_ bytes: Int) {
        if hashDepth > 0 { hashScratchBytes = max(hashScratchBytes, bytes) }
    }
    static func reset() {
        metadataLoads = 0; peakSources = liveSources; hashScratchBytes = 0
    }
}
'''


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise SystemExit('TEST126 observation anchor is not unique: ' + old)
    return source.replace(old, new, 1)


def instrument(original):
    source = original.decode()
    source = replace_once(source, '    private var directoryFD: Int32 = -1\n',
        '    private var directoryFD: Int32 = -1\n    private var measuredRecovery126 = false\n')
    source = replace_once(source, '            if recover {\n                do { try loadRegistered',
        '            if recover {\n                measuredRecovery126 = true; NG2DiscoveryMetrics126.opened()\n'
        '                do { try loadRegistered')
    source = replace_once(source, '    deinit { if directoryFD >= 0 { close(directoryFD) } }',
        '    deinit { if measuredRecovery126 { NG2DiscoveryMetrics126.closed() }; '
        'if directoryFD >= 0 { close(directoryFD) } }')
    anchor = '    private func loadRegistered(verifyRasters: Bool) throws {\n'
    source = replace_once(source, anchor, anchor + '        NG2DiscoveryMetrics126.metadataLoads += 1\n')
    anchor = '    private func artifactEntries(hashes: Bool) throws -> [ArtifactRef] {\n'
    source = replace_once(source, anchor, anchor +
        '        if hashes { NG2DiscoveryMetrics126.hashDepth += 1 }\n'
        '        defer { if hashes { NG2DiscoveryMetrics126.hashDepth -= 1 } }\n')
    # Observe actual allocated Data sizes while executing artifact hashing. The
    # exact same expression runs first; the observer changes no allocation size.
    pattern = re.compile(r'^([ \t]*)var (\w+) = Data\(count: ([^\n]+)\)[ \t]*$', re.MULTILINE)
    allocations = []
    def observe(match):
        allocations.append(match.group(2))
        return match.group(0) + '\n' + match.group(1) + 'NG2DiscoveryMetrics126.allocated(' + match.group(2) + '.count)'
    source = pattern.sub(observe, source)
    if not allocations:
        raise SystemExit('TEST126 did not instrument an actual Data allocation')
    return (source + COUNTERS).encode(), allocations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--swiftc', default='swiftc')
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--before-spool', type=Path)
    args = parser.parse_args()
    compiler = shutil.which(args.swiftc)
    if compiler is None:
        raise SystemExit('Swift unavailable; no TEST126 semantic assertion executed')
    if args.baseline_only != bool(args.before_spool):
        raise SystemExit('--baseline-only requires exactly one --before-spool')
    path = args.before_spool if args.baseline_only else HERE/'ngg2/NG2CycleSpool.swift'
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if args.baseline_only and digest != BASELINE_SHA:
        raise SystemExit('TEST126 baseline differs from pinned TEST125 Spool')
    actual, allocations = instrument(original)
    helper = (HERE/'ngg2_cycle_spool116_tests.swift').read_bytes()
    marker = b'let selected116 = CommandLine.arguments.dropFirst().first ?? "all"'
    if helper.count(marker) != 1:
        raise SystemExit('TEST116 fixture helper boundary differs')
    fixture = (HERE/'ngg2_cycle_spool126_tests.swift').read_bytes()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    identity = subprocess.run([compiler, '--version'], text=True, capture_output=True, check=True)
    rows = {}
    with tempfile.TemporaryDirectory(prefix='spool126-') as temporary:
        stage = Path(temporary)
        (stage/'NG2CycleSpool.swift').write_bytes(actual)
        (stage/'main.swift').write_bytes(helper.split(marker)[0] + fixture)
        command = [compiler, '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', str(stage/'NG2CycleSpool.swift'),
            str(stage/'main.swift'), '-o', str(stage/'fixture')]
        result = subprocess.run(command, text=True, capture_output=True, timeout=180)
        (output/'compile.txt').write_text(result.stdout+result.stderr)
        if result.returncode:
            raise SystemExit('Compile failure is not assertion Red:\n'+result.stdout+result.stderr)
        selected = tuple(CASES) if args.baseline_only else tuple(CASES) + REGRESSIONS
        for case in selected:
            expected = CASES.get(case)
            value = subprocess.run([str(stage/'fixture'), case], text=True, capture_output=True, timeout=180)
            (output/(case+'.txt')).write_text(value.stdout+value.stderr)
            failures = [line for line in value.stdout.splitlines() if line.startswith('FAIL ')]
            metrics = [json.loads(line.removeprefix('METRICS126 ')) for line in value.stdout.splitlines()
                if line.startswith('METRICS126 ')]
            rows[case] = dict(returncode=value.returncode, compile_errors=0, failures=failures, metrics=metrics)
            if len(metrics) != 1:
                raise SystemExit('Missing TEST126 actual-call metrics for '+case+':\n'+value.stdout+value.stderr)
            if args.baseline_only:
                if value.returncode != 1 or failures != [expected]:
                    raise SystemExit('Wrong TEST126 assertion Red for '+case+':\n'+value.stdout+value.stderr)
            elif value.returncode or value.stdout.strip().splitlines()[-1:] != ['PASS TEST126 Spool '+case]:
                raise SystemExit(value.stdout+value.stderr or 'TEST126 assertion failure')
            print(value.stdout, end='')
    receipt = dict(schema='test126-spool-evidence-v1', baseline_only=args.baseline_only,
        cases=list(selected),
        source_sha256=digest, observed_source_sha256=hashlib.sha256(actual).hexdigest(),
        fixture_sha256=hashlib.sha256(fixture).hexdigest(), helpers116_sha256=hashlib.sha256(helper).hexdigest(),
        counter_sha256=hashlib.sha256(COUNTERS.encode()).hexdigest(), observed_data_variables=allocations,
        compiler=identity.stdout+identity.stderr, command=command, results=rows,
        device_acceptance=False, input_authority=False, rss_is_not_measured=True)
    (output/'spool126-evidence.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
