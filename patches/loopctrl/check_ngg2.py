"""Compile production NG-G2 helpers and require executable behavior evidence."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
EXPECTED_RED = 'FAIL cancelled_ticket_not_sent'


def execute(source, destination, label):
    destination.mkdir(parents=True, exist_ok=True)
    staged = destination / label
    staged.mkdir(exist_ok=True)
    (staged / 'NG2Ticket.swift').write_text(source)
    shutil.copyfile(HERE / 'ngg2_ticket_tests.swift', staged / 'main.swift')
    executable = staged / 'ticket-tests'
    built = subprocess.run(['swiftc', str(staged / 'NG2Ticket.swift'),
        str(staged / 'main.swift'), '-o', str(executable)],
        capture_output=True, text=True, timeout=120)
    (destination / (label + '-compile.txt')).write_text(built.stdout + built.stderr)
    built.check_returncode()
    result = subprocess.run([str(executable.resolve())], capture_output=True,
                            text=True, timeout=30)
    (destination / (label + '-tests.txt')).write_text(result.stdout + result.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--red-only', action='store_true')
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    if args.red_only:
        if len(args.paths) != 1:
            parser.error('--red-only requires output directory')
        output = args.paths[0]
        source = (HERE / 'ngg2/NG2Ticket.swift').read_text()
        observed = execute(source, output, 'baseline-red')
        if observed.returncode != 1 or observed.stdout.strip() != EXPECTED_RED or observed.stderr:
            raise RuntimeError('compiled_behavioral_red_not_observed')
        report = {'baseline_red': {'compiled': True, 'returncode': 1,
                  'observed': observed.stdout.strip()}, 'device_test': 'not_run'}
    else:
        if len(args.paths) != 2:
            parser.error('requires patched upstream and output directory')
        upstream, output = args.paths
        source = (upstream / 'LoopCtrlUITests/NG2Ticket.swift').read_text()
        observed = execute(source, output, 'production-green')
        observed.check_returncode()
        if not observed.stdout.startswith('PASS 12 pure Swift ticket contracts;') or observed.stderr:
            raise RuntimeError('missing_production_green')
        report = {'production_green': {'compiled': True, 'returncode': 0,
                  'observed': observed.stdout.strip()}, 'device_test': 'not_run'}
    (output / 'ngg2-swift-contract.json').write_text(json.dumps(report, indent=2)+'\n')
    print(observed.stdout, end='')


if __name__ == '__main__':
    main()
