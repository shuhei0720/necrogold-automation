"""固定元ソースの寸法式をSwiftで実行し、横長契約のRedを観測する。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE_BLOB = 'b8d988bb4ac80ef376a15491cd98db21853a5c50'
BASE_COMMIT = '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767'


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def program(raw):
    if git_blob(raw) != BASE_BLOB:
        raise ValueError('baseline_source_mismatch')
    source = raw.decode('utf-8')
    statements = ('let targetPixelW = frame.width * targetScale',
                  'let targetPixelH = frame.height * targetScale')
    if any(source.count(line) != 1 for line in statements):
        raise ValueError('baseline_statements_not_unique')
    # この2式は元ActionHandlerから取り出す。UIImage/XCTestの実行ではない。
    return '''import Foundation
let frame = CGRect(x: 0, y: 0, width: 414, height: 896)
let targetScale = 1.0
''' + '\n'.join(source[source.index(line):source.index(line)+len(line)] for line in statements) + '''
if targetPixelW != 896 || targetPixelH != 414 {
    print("FAIL baseline_landscape_scale1: expected=896x414 actual=\\(Int(targetPixelW))x\\(Int(targetPixelH))")
    exit(1)
}
print("PASS baseline_landscape_scale1")
'''


def main():
    root, destination = map(Path, sys.argv[1:])
    destination.mkdir(parents=True, exist_ok=True)
    raw = (root/'LoopCtrlUITests/ActionHandler.swift').read_bytes()
    swift = destination/'baseline.swift'
    swift.write_text(program(raw))
    executable = destination/'baseline-test'
    # コンパイル失敗をRedと見なさない。先にcheck=Trueで独立して検査する。
    subprocess.run(['swiftc', str(swift), '-o', str(executable)], check=True, timeout=120)
    result = subprocess.run([str(executable.resolve())], capture_output=True, text=True, timeout=10)
    (destination/'baseline-swift-tests.txt').write_text(result.stdout+result.stderr)
    expected = 'FAIL baseline_landscape_scale1: expected=896x414 actual=414x896'
    if result.returncode != 1 or result.stdout.strip() != expected or result.stderr:
        raise RuntimeError('expected_behavioral_red_not_observed')
    report = {'upstream_commit': BASE_COMMIT, 'source_blob': BASE_BLOB, 'compiled': True,
              'returncode': result.returncode, 'observed': result.stdout.strip(),
              'scope':'exact original dimension statements in a Swift harness; UIKit/device not executed',
              'device_test':'not_run'}
    (destination/'baseline-contract.json').write_text(json.dumps(report,indent=2)+'\n')
    print(result.stdout.strip())


if __name__ == '__main__':
    main()
