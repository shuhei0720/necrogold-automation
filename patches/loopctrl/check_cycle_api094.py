#!/usr/bin/env python3
"""TEST094 actual owner projection and public native-cycle schema, no UI/world."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fault-red', action='store_true')
    args = parser.parse_args()
    compiler = shutil.which('swiftc')
    if compiler is None:
        raise SystemExit('Swift unavailable; no cycle API fixture or semantic Red executed')
    upstream = args.upstream.resolve()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    server = (upstream / 'LoopCtrlKit/JSONRPCServer.swift').read_text()
    begin = '// NG-G2 BEGIN authenticated owner projection (tested verbatim).'
    end = '// NG-G2 END authenticated owner projection.'
    if server.count(begin) != 1 or server.count(end) != 1:
        raise ValueError('owner projection source boundary')
    helper = server[server.index(begin):server.index(end) + len(end)]
    types = (upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)
    if len(types) != 2:
        raise ValueError('RPCTypes source boundary')
    with tempfile.TemporaryDirectory(prefix='cycle-api094-') as temporary:
        stage = Path(temporary)
        (stage / 'RPCTypes.swift').write_text(types[0])
        (stage / 'Owner.swift').write_text('import Foundation\n' + helper + '\n')
        shutil.copyfile(HERE / 'ngg2_cycle_api094_tests.swift', stage / 'main.swift')
        sources = [stage / 'RPCTypes.swift', stage / 'Owner.swift',
                   upstream / 'LoopCtrlKit/RPCMethod.swift', upstream / 'LoopCtrlKit/BuildStamp.swift',
                   stage / 'main.swift']

        def execute(label, body):
            (stage / 'Owner.swift').write_text('import Foundation\n' + body + '\n')
            command = [compiler, '-Onone', *map(str, sources), '-o', str(stage / 'api-tests')]
            compiled = subprocess.run(command, capture_output=True, text=True, timeout=120)
            (output / (label + '-compile.txt')).write_text(compiled.stdout + compiled.stderr)
            if compiled.returncode:
                raise SystemExit(compiled.stdout + compiled.stderr)
            result = subprocess.run([str(stage / 'api-tests')], capture_output=True, text=True, timeout=30)
            (output / (label + '.txt')).write_text(result.stdout + result.stderr)
            return result

        if args.fault_red:
            marker = ', "necro_native_cycle"'
            if helper.count(marker) != 1:
                raise ValueError('cycle method fault source boundary')
            red = execute('cycle-api-mutation-red', helper.replace(marker, '', 1))
            if red.returncode != 1 or red.stdout.strip() != 'FAIL native_method_allowlist' or red.stderr:
                raise RuntimeError('cycle API allowlist semantic Red missing: ' + red.stdout + red.stderr)
            print('PASS TEST094 cycle RPC allowlist semantic Red')
        green = execute('cycle-api-production-green', helper)
        print(green.stdout, end='')
        if green.returncode or green.stderr or len(green.stdout.splitlines()) != 2:
            raise SystemExit(green.stderr or green.stdout or green.returncode)
        if not green.stdout.endswith('PASS TEST094 actual owner projection and native cycle schema; no network, UI or phone acceptance\n'):
            raise RuntimeError('cycle API fixture inventory changed')
        hashes = {}
        for path in ('LoopCtrlKit/JSONRPCServer.swift', 'LoopCtrlKit/RPCMethod.swift',
                     'LoopCtrlKit/RPCTypes.swift', 'LoopCtrlKit/BuildStamp.swift'):
            hashes[path] = hashlib.sha256((upstream / path).read_bytes()).hexdigest()
        (output / 'cycle-api-evidence.json').write_text(json.dumps(dict(
            compiled_source_sha256=hashes, fixture_sha256=hashlib.sha256((HERE / 'ngg2_cycle_api094_tests.swift').read_bytes()).hexdigest(),
            owner_projection_sha256=hashlib.sha256(helper.encode()).hexdigest(),
            semantic_fault_red=bool(args.fault_red),
            scope='actual five-method owner helper and registry/schema; network/auth envelopes, UI and iPhone not executed'),
            indent=2) + '\n')


if __name__ == '__main__': main()
