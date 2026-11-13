#!/usr/bin/env python3
"""Focused terminal-export unit: actual Swift helpers, C ABI and filesystem."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fault-red', action='store_true')
    args = parser.parse_args()
    native = args.upstream.resolve() / 'LoopCtrlUITests'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not shutil.which('swiftc'):
        raise SystemExit('Swift unavailable; export fixture was not executed')
    with tempfile.TemporaryDirectory(prefix='ngg2-export094-') as temporary:
        stage = Path(temporary)
        types = (args.upstream / 'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)[0]
        (stage / 'RPCTypes.swift').write_text(types)
        (stage / 'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n')
        shutil.copyfile(HERE / 'ngg2_cycle_export094_tests.swift', stage / 'main.swift')
        objects = []
        for relative in ('NG2Perception.c', 'NG2Ring.c', 'NG2RingKernel/observe.c', 'NG2RingKernel/icon.c', 'NG2RingKernel/word.c'):
            obj = stage / (Path(relative).stem + '.o')
            subprocess.run(['clang', '-std=c11', '-O2', '-fno-fast-math', '-ffp-contract=off',
                            '-I', str(native), '-c', str(native / relative), '-o', str(obj)], check=True)
            objects.append(obj)
        sources = [stage / 'RPCTypes.swift', *(native / name for name in
            ('NG2Raster.swift', 'NG2CycleWire.swift', 'NG2CycleSpool.swift', 'NG2CycleExport.swift')), stage / 'main.swift']
        command = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-Xcc', '-I' + str(native),
                   '-import-objc-header', str(stage / 'Bridge.h'), *map(str, sources),
                   *map(str, objects), '-o', str(stage / 'export-tests')]
        if args.fault_red:
            original = (native/'NG2CycleExport.swift').read_text()
            import re
            mutated, count = re.subn(r'        if let reason = preflight\(\{.*?        \}\) \{ return \(nil, reason\) \}\n',
                                     '', original, flags=re.S)
            if count != 3:
                raise SystemExit('export range-regression mutation boundary differs')
            mutant = stage/'NG2CycleExport.swift'
            mutant.write_text(mutated)
            red_command = [str(mutant) if value == str(native/'NG2CycleExport.swift') else value for value in command]
            compiled = subprocess.run(red_command, capture_output=True, text=True)
            (output/'export-fault-red-compile.txt').write_text(compiled.stdout + compiled.stderr)
            if compiled.returncode:
                raise SystemExit(compiled.stdout + compiled.stderr)
            red = subprocess.run([str(stage/'export-tests')], capture_output=True, text=True, timeout=60)
            (output/'export-fault-red.txt').write_text(red.stdout + red.stderr)
            if red.returncode == 0 or 'FAIL unknown capture is request-local' not in red.stdout:
                raise SystemExit('meaningful export range-regression Red missing: ' + red.stdout + red.stderr)
            print('PASS semantic range-regression Red: malformed request cannot poison session export')
        result = subprocess.run(command, capture_output=True, text=True)
        (output / 'export-compile.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)
        result = subprocess.run([str(stage / 'export-tests')], capture_output=True, text=True, timeout=60,
                                env=dict(os.environ, NG2_EXPORT_OUTPUT=str(stage / 'roundtrip')))
        (output / 'export-tests.txt').write_text(result.stdout + result.stderr)
        print(result.stdout, end='')
        if result.returncode:
            raise SystemExit(result.stderr or result.returncode)
        with Image.open(stage / "roundtrip.png") as image:
            image.load()
            assert image.size == (896, 414)
            assert image.convert("RGBA").tobytes() == (stage / "roundtrip.rgba").read_bytes()
        passes = [line for line in result.stdout.splitlines() if line.startswith('PASS ')]
        if len(passes) != 6:
            raise SystemExit('focused export fixture inventory differs')
        (output / 'export-evidence.json').write_text(json.dumps(dict(
            scope='immutable terminal export, real Swift/C helpers and filesystem; no game/phone acceptance',
            passes=passes), indent=2) + '\n')


if __name__ == '__main__':
    main()
