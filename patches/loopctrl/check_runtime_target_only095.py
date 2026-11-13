#!/usr/bin/env python3
"""Focused TEST095 actual classifier call and Runtime/Wire integration."""
import argparse
import ast
import ctypes as C
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import check_runtime_cycle094 as prior

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = ['wire policy2 and legacy modes', 'binary negative durable restart',
         'visible candidate hold', 'partial candidate hold']
PASS = ('PASS TEST095 production Runtime four target-only policy/wire/negative/candidate/partial callbacks; '
        'procedural pixels and injected lifecycle result')
REDS = {'target-only-mode-red': 'FAIL cycle095_actual_classifier_uses_target_only_mode',
        'target-only-wire-red': 'FAIL cycle095_generic_wire_and_policy2'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fixture_source(selected=None):
    base = prior.fixture_source('lease')
    boundary = '// TEST094 ENTRYPOINTS BEGIN.\n'
    if base.count(boundary) != 1:
        raise ValueError('shared cycle declaration boundary')
    fixture = (HERE/'ngg2_target_only_runtime_tests.swift').read_text()
    cases = '// TEST095 CASE CALLS BEGIN.\n'
    if fixture.count(cases) != 1:
        raise ValueError('target-only entrypoint boundary')
    if selected is not None:
        calls = {'mode': 'testCycle095Hold(cycle095Root, partial: false)\n', 'wire': 'testCycle095Wire()\n'}
        if selected not in calls:
            raise ValueError('target-only mutation selection')
        fixture = fixture.split(cases)[0] + calls[selected]
    return base.split(boundary)[0] + fixture


def pause_source():
    values = [node.args[0].value for node in ast.walk(ast.parse((HERE/'check_runtime_cycle094.py').read_text()))
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'write_text'
              and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
              and 'void ng2_test_pause(uint8_t *out,size_t length)' in node.args[0].value]
    if len(values) != 1:
        raise ValueError('shared two-label pause source boundary')
    return values[0]


def direct_classifier(library, output):
    """Real C mode2 producer on explicit procedural pixels/Scene, no override."""
    sys.path.insert(0, str(ROOT))
    from tests.test_native_ring094 import Result, Options, Clock, Cancelled
    from tests.test_native_ring_bank094 import complete_shop, bank_data, auth_data
    from tests.test_native_perception import NativeScene
    lib = C.CDLL(str(library))
    lib.ng2_ring_assess_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(Options), C.POINTER(Result)]
    lib.ng2_ring_assess_rgba.restype = C.c_int
    lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
    lib.ng2_ring_negative_certificate.restype = C.c_int
    entries = [dict(entry, word=None) for entry in bank_data()['entries'][:3]]
    images = {'unregistered_names': complete_shop(entries, auth=auth_data()),
              'candidate': complete_shop(entries, auth=auth_data(), target=True)}
    records = []
    for name, mode, goods in (('unregistered_names', 0, 2), ('unregistered_names', 1, 2),
                              ('unregistered_names', 2, 2), ('candidate', 2, 2), ('unregistered_names', 2, 1)):
        now, cancelled = Clock(lambda _: 100), Cancelled(lambda _: 0)
        scene = NativeScene(abi_version=1, struct_size=C.sizeof(NativeScene), state=2, gold_state=2, goods=goods)
        scene.tiles[0] = 2
        options = Options(abi=1, size=C.sizeof(Options), mode=mode, deadline_ns=1000000000,
                          now_ns=now, cancelled=cancelled, scene=C.addressof(scene), fast=1)
        result, raw = Result(), C.create_string_buffer(images[name])
        status = lib.ng2_ring_assess_rgba(raw, len(images[name]), 896*4, C.byref(options), C.byref(result))
        if status != 0:
            raise AssertionError('actual mode preflight status ' + str((name, mode, goods, status)))
        if mode < 2:
            assert result.outcome != 3, 'legacy modes cannot certify unknown names'
        elif name == 'candidate':
            assert result.outcome in (1, 2), 'actual target sprite must veto negative'
        elif goods == 1:
            assert result.outcome != 3, 'partial scene cannot certify negative'
        else:
            assert (result.outcome, result.coverage, result.certificate.policy_version, result.partial_count) == (3, 2, 2, 2)
            assert lib.ng2_ring_negative_certificate(C.byref(result)) == 1
            slots = list(result.rows[result.selected_row].slots) + list(result.partial[:2])
            assert all(slot.kind == 3 and slot.non_target_id == 0 and slot.ignored_container_id == 0 for slot in slots)
        records.append(dict(input=name, mode=mode, scene_goods=goods, status=status, outcome=result.outcome,
                            coverage=result.coverage, policy=result.certificate.policy_version, rgba_sha256=digest(images[name])))
    (output/'target-only-direct-c.json').write_text(json.dumps(dict(
        scope='actual Ring C producer, procedural RGBA and explicit Scene; no Runtime override or phone accuracy', records=records), indent=2)+'\n')
    print('PASS TEST095 actual C target-only producer, unknown names, candidate and partial veto')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--fault-red', action='store_true')
    args = parser.parse_args()
    if not shutil.which('swiftc'):
        raise SystemExit('Swift unavailable; no TEST095 Runtime assertion Red or Green executed')
    native, output = args.upstream.resolve()/'LoopCtrlUITests', args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    installed = {}
    manifest = json.loads((HERE/'ngg2-manifest.json').read_text())
    for destination, spec in sorted(manifest['additions'].items()):
        source_root = spec.get('source_root')
        if source_root not in (None, 'ring_native'):
            raise ValueError('unknown sealed source root')
        source = (ROOT/'tools/ring_native' if source_root == 'ring_native' else HERE/'ngg2')/spec['source']
        target = args.upstream.resolve()/destination
        if target.read_bytes() != source.read_bytes() or digest(source.read_bytes()) != spec['sha256']:
            raise ValueError('patched sealed source differs: ' + destination)
        installed[destination] = digest(target.read_bytes())
    with tempfile.TemporaryDirectory(prefix='runtime-target-only095-') as temporary:
        stage = Path(temporary)
        (stage/'RPCTypes.swift').write_text((args.upstream/'LoopCtrlKit/RPCTypes.swift').read_text().split('// MARK: - Auth Types\n', 1)[0])
        (stage/'Bridge.h').write_text('#include "NG2Controller.h"\n#include "NG2Ring.h"\n#include "ngg2_runtime_scene_fixtures.h"\n#include "ngg2_cycle_runtime_fixture.h"\nvoid ng2_test_pause(uint8_t *,size_t);\n')
        (stage/'pause.c').write_text(pause_source())
        objects, commands, native_objects = [], [], {}
        for index, source in enumerate([native/name for name in prior.NATIVE] +
                                      [HERE/'ngg2_runtime_scene_fixtures.c', HERE/'ngg2_cycle_runtime_fixture.c', stage/'pause.c']):
            target = stage/('native-'+str(index)+'.o')
            flags = ['-O0'] if source.name in ('NG2Controller.c', 'NG2Beat.c') else ['-O2', '-fno-fast-math', '-ffp-contract=off']
            command = ['clang', '-std=c11', *flags, '-I', str(native), '-I', str(HERE), '-c', str(source), '-o', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            (output/(source.stem+'-compile.txt')).write_text(result.stdout+result.stderr)
            if result.returncode: raise SystemExit(result.stdout+result.stderr)
            objects.append(target); commands.append(command); native_objects[source.name] = target
        library = stage/'ring-direct.dylib'
        direct_command = ['clang', '-dynamiclib', *[str(native_objects[name]) for name in
                          ('NG2Perception.c', 'NG2Ring.c', 'observe.c', 'icon.c', 'word.c')], '-o', str(library)]
        subprocess.run(direct_command, check=True)
        direct_classifier(library, output)
        runtime, wire = (native/'NG2Runtime.swift').read_text(), (native/'NG2CycleWire.swift').read_text()
        sources = [stage/'RPCTypes.swift', native/'NG2Ticket.swift', native/'NG2Raster.swift',
                   stage/'NG2CycleWire.swift', native/'NG2CycleSpool.swift', native/'NG2CycleExport.swift',
                   HERE/'ngg2_runtime_fakes.swift', stage/'NG2Runtime.swift', stage/'main.swift']
        proofs = {}
        def execute(runtime_source, wire_source, name, selected=None):
            fixture = fixture_source(selected)
            for path, content in ((stage/'NG2Runtime.swift', runtime_source), (stage/'NG2CycleWire.swift', wire_source),
                                  (stage/'main.swift', fixture), (output/(name+'-fixture.swift'), fixture)):
                path.write_text(content)
            command = ['swiftc', '-Onone', '-D', 'NG2_RUNTIME_HOST_TEST', '-D', 'NG2_CYCLE_TEST094', '-D', 'NG2_PREPARATION_TEST058_GREEN',
                       '-Xcc', '-I'+str(native), '-Xcc', '-I'+str(HERE), '-import-objc-header', str(stage/'Bridge.h'),
                       *map(str, sources), *map(str, objects), '-o', str(stage/name)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (output/(name+'-compile.txt')).write_text(result.stdout+result.stderr)
            if result.returncode: raise SystemExit(result.stdout+result.stderr)
            result = subprocess.run([str(stage/name)], capture_output=True, text=True, timeout=180)
            (output/(name+'-tests.txt')).write_text(result.stdout+result.stderr)
            proof = dict(returncode=result.returncode, selected=selected, fixture_sha256=digest(fixture.encode()),
                         runtime_sha256=digest(runtime_source.encode()), wire_sha256=digest(wire_source.encode()),
                         stdout_bytes=len(result.stdout.encode()), stderr_bytes=len(result.stderr.encode()), swift_command=command,
                         expected_assertion=REDS.get(name))
            (output/(name+'-result.json')).write_text(json.dumps(proof, indent=2)+'\n'); proofs[name] = proof
            return result
        if args.fault_red:
            marker = 'options.mode = Int32(NG2_RING_MODE_TARGET_ONLY);'
            if runtime.count(marker) != 1: raise ValueError('mode2 mutation boundary')
            result = execute(runtime.replace(marker, 'options.mode = 0;', 1), wire, 'target-only-mode-red', 'mode')
            if result.returncode != 1 or REDS['target-only-mode-red'] not in result.stdout:
                raise SystemExit('meaningful TEST095 mode Red missing (returncode='+str(result.returncode)+'):\n'+result.stdout+result.stderr)
            marker = 'let targetOnly = mode == Int32(NG2_RING_MODE_TARGET_ONLY)'
            if wire.count(marker) != 1: raise ValueError('policy2 wire mutation boundary')
            result = execute(runtime, wire.replace(marker, 'let targetOnly = false', 1), 'target-only-wire-red', 'wire')
            if result.returncode != 1 or REDS['target-only-wire-red'] not in result.stdout:
                raise SystemExit('meaningful TEST095 wire Red missing (returncode='+str(result.returncode)+'):\n'+result.stdout+result.stderr)
        green = execute(runtime, wire, 'target-only-production-green')
        print(green.stdout, end='')
        if green.returncode or not green.stdout.strip().endswith(PASS):
            raise SystemExit(green.stderr or 'TEST095 Runtime Green failed (returncode='+str(green.returncode)+')')
        (output/'runtime-target-only095-evidence.json').write_text(json.dumps(dict(
            scope='actual C mode2 call, Runtime/Wire and durable filesystem with explicit injected lifecycle certificate; no game/phone acceptance',
            new_cases=CASES, old_cases=[], mutation_red=args.fault_red, expected_red=REDS, pass_line=PASS,
            runtime_sha256=digest(runtime.encode()), wire_sha256=digest(wire.encode()), fixture_sha256=digest(fixture_source().encode()),
            installed_source_sha256=installed, native_commands=commands, direct_command=direct_command, proofs=proofs), indent=2)+'\n')


if __name__ == '__main__':
    main()
