"""実JSONRPCServerの認証済みowner投影呼出しを退行させ、挙動失敗を確認する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

TARGET = 'params = NG2AuthenticatedOwner.inject(method: method, params: params, owner: opened.tokId)'
TEST = 'LoopCtrlKitTests/NG2RPCContractsTests/testAuthenticatedOwnerProjectionUsesEnvelopeIdentityAtActualCallsite'
EXPECTED = 'NG2_AUTHENTICATED_OWNER_CALLSITE'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.upstream / 'LoopCtrlKit/JSONRPCServer.swift'
    original = source.read_bytes()
    text = original.decode()
    if text.count(TARGET) != 1:
        raise ValueError('actual_owner_projection_callsite_not_unique')
    result_path = (args.output / 'ngg2-rpc-mutation.xcresult').absolute()
    if result_path.exists():
        raise ValueError('mutation_result_destination_exists')
    try:
        source.write_text(text.replace(TARGET, '// NG-G2 test mutation: owner projection removed.'))
        run = subprocess.run(['xcodebuild', 'test', '-project', 'LoopCtrl.xcodeproj',
            '-scheme', 'LoopCtrlKitTests', '-destination', 'platform=macOS',
            '-only-testing:' + TEST, '-resultBundlePath', str(result_path)], cwd=args.upstream,
            capture_output=True, text=True, timeout=300)
        output = run.stdout + run.stderr
        (args.output / 'ngg2-rpc-callsite-mutation.txt').write_text(output)
        # A build error or test-runner failure is not a behavioral Red. Require
        # the actual XCTest assertion's diagnostic and an executed failed test.
        if (run.returncode == 0 or EXPECTED not in output
                or not re.search(r'Executed 1 test, with [1-9][0-9]* failures?', output)
                or '** TEST FAILED **' not in output):
            raise RuntimeError('expected_actual_callsite_assertion_red_not_observed')
        report = {'mutation': 'delete-real-authenticated-owner-injection-callsite',
            'source_sha256': hashlib.sha256(original).hexdigest(),
            'compiled_and_executed': True, 'returncode': run.returncode,
            'expected_assertion': EXPECTED,
            'scope': 'actual encrypted loopback JSONRPCServer plus fake execution handler',
            'device_test': 'not_run'}
        (args.output / 'ngg2-rpc-callsite-contract.json').write_text(json.dumps(report, indent=2) + '\n')
        print('PASS actual encrypted RPC owner-callsite mutation produced the expected assertion failure')
    finally:
        source.write_bytes(original)


if __name__ == '__main__':
    main()
