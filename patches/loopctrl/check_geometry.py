"""実ソースの純粋Swift契約を実行。コンパイル失敗をRedと混同しない。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from apply_patch import SOURCE_MANIFEST, digest

HERE = Path(__file__).resolve().parent
BEGIN = '// NG-G1 BEGIN: pure screenshot contract (extracted verbatim by the Swift tests).'
END = '// NG-G1 END: pure screenshot contract.'
EXPECTED_RED = 'FAIL landscape_scale1: expected=896x414 actual=414x896'


def prepare(root, destination):
    root, destination = Path(root), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    source_hashes = {}
    for name, expected in SOURCE_MANIFEST.items():
        raw = (root / name).read_bytes()
        if digest(raw) != expected['patched_sha256']:
            raise ValueError('patched_source_mismatch: ' + name)
        source_hashes[name] = digest(raw)
    handler = (root / 'LoopCtrlUITests/ActionHandler.swift').read_text()
    if handler.count(BEGIN) != 1 or handler.count(END) != 1:
        raise ValueError('pure_contract_markers_not_unique')
    helper = handler[handler.index(BEGIN):handler.index(END) + len(END)]
    helper = 'import Foundation\nimport CoreGraphics\n' + helper + '\n'
    # Preserve the actual JSONRPC/JSONValue definitions byte-for-byte. AuthSession
    # below this boundary needs AuthManager and crypto and is unrelated here.
    types_path = root / 'LoopCtrlKit/RPCTypes.swift'
    types_raw = types_path.read_bytes()
    types = types_raw.decode().split('// MARK: - Auth Types\n', 1)
    if len(types) != 2:
        raise ValueError('rpc_types_boundary_missing')
    source_hashes['LoopCtrlKit/RPCTypes.swift'] = digest(types_raw)
    (destination / 'RPCTypes.swift').write_text(types[0])
    (destination / 'ActionCommand.swift').write_bytes((root / 'LoopCtrlUITests/ActionCommand.swift').read_bytes())
    (destination / 'NGScreenshotGeometry.swift').write_text(helper)
    (destination / 'main.swift').write_bytes((HERE / 'geometry_tests.swift').read_bytes())
    # Mutate only the new target's dimension expressions to the fixed upstream
    # cached-size formulas. The same tests and request/encoding helpers run.
    replacements = {
        'let pixelWidth = imagePointWidth * effectiveScale': 'let pixelWidth = Double(cachedSize.width) * effectiveScale',
        'let pixelHeight = imagePointHeight * effectiveScale': 'let pixelHeight = Double(cachedSize.height) * effectiveScale',
    }
    mutated = helper
    for old, new in replacements.items():
        if mutated.count(old) != 1:
            raise ValueError('mutation_target_not_unique')
        mutated = mutated.replace(old, new)
    (destination / 'NGScreenshotGeometry-mutated.swift').write_text(mutated)
    return source_hashes


def execute(destination, label, helper):
    destination = Path(destination)
    executable = destination / (label + '-tests')
    sources = [destination / 'RPCTypes.swift', destination / 'ActionCommand.swift',
               destination / helper, destination / 'main.swift']
    compiled = subprocess.run(['swiftc', *(str(path) for path in sources), '-o', str(executable)],
                              capture_output=True, text=True, timeout=120)
    (destination / (label + '-compile.txt')).write_text(compiled.stdout + compiled.stderr)
    compiled.check_returncode()
    result = subprocess.run([str(executable.resolve())], capture_output=True, text=True, timeout=30)
    (destination / (label + '-swift-tests.txt')).write_text(result.stdout + result.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    sources = prepare(args.upstream, args.output)
    red = execute(args.output, 'mutation-red', 'NGScreenshotGeometry-mutated.swift')
    if red.returncode != 1 or red.stdout.strip() != EXPECTED_RED or red.stderr:
        raise RuntimeError('expected_behavioral_mutation_red_not_observed')
    green = execute(args.output, 'production-green', 'NGScreenshotGeometry.swift')
    green.check_returncode()
    if not green.stdout.strip().endswith('pure Swift contracts; UIKit/device not executed') or green.stderr:
        raise RuntimeError('missing_green_completion')
    report = {'source_sha256': sources, 'mutation_red': {'compiled': True, 'returncode': red.returncode,
        'observed': red.stdout.strip()}, 'production_green': {'compiled': True, 'returncode': green.returncode,
        'observed': green.stdout.strip().splitlines()[-1]},
        'scope': 'Actual extracted pure helper, ActionCommand and JSON RPC types; UIKit rendering/capture/device not executed',
        'device_test': 'not_run'}
    (args.output / 'geometry-contract.json').write_text(json.dumps(report, indent=2) + '\n')
    print(red.stdout, end='')
    print(green.stdout, end='')


if __name__ == '__main__':
    main()
