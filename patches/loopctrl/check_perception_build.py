"""Verify the generated, source-specific strict Perception build profile.

The baseline reconstructs the delivered TEST048 sources, generates a real
Xcode project, and requires the new contract to fail on its missing flags.
It never treats generation, missing sources, or API/setup errors as that Red.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = '8e72974a8ab93de853d7362c3d00b7cac1a39a42'
UPSTREAM = '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767'
TARGET = 'LoopCtrlUITests'
SOURCE = 'NG2Perception.c'
FLAGS = ['-O2', '-fno-fast-math', '-ffp-contract=off']
EXPECTED_RED = 'FAIL NG2Perception_strict_O2_is_applied_once'


class ProfileError(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_run(args, *, cwd=None, timeout=120):
    result = subprocess.run(list(map(str, args)), cwd=cwd, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('command_failed: ' + result.stdout + result.stderr)
    return result


def read_project(path):
    path = Path(path)
    if path.suffix == '.json':
        return json.loads(path.read_text())
    converted = checked_run(['plutil', '-convert', 'json', '-o', '-', path])
    return json.loads(converted.stdout)


def project_contract(project):
    """Resolve actual target/build-phase/file references, not YAML spelling."""
    objects = project.get('objects')
    if not isinstance(objects, dict):
        raise ProfileError('perception_project_objects')
    parents = {}
    for identifier, value in objects.items():
        if isinstance(value, dict) and value.get('isa') == 'PBXGroup':
            for child in value.get('children', []):
                parents.setdefault(child, []).append(identifier)

    def source_path(identifier, visited=()):
        if identifier in visited or len(visited) > 32:
            raise ProfileError('perception_project_reference_cycle')
        value = objects.get(identifier)
        if not isinstance(value, dict):
            raise ProfileError('perception_project_file_reference')
        path = value.get('path', '')
        if not isinstance(path, str) or Path(path).is_absolute() or '..' in Path(path).parts:
            raise ProfileError('perception_project_file_path')
        tree = value.get('sourceTree')
        if tree == 'SOURCE_ROOT':
            return Path(path)
        if tree != '<group>':
            raise ProfileError('perception_project_source_tree')
        candidates = set(parents.get(identifier, []))
        if len(candidates) > 1:
            raise ProfileError('perception_project_multiple_parents')
        parent = next(iter(candidates), None)
        base = source_path(parent, (*visited, identifier)) if parent else Path()
        return base / path
    matches = [value for value in objects.values() if isinstance(value, dict)
               and value.get('isa') == 'PBXNativeTarget' and value.get('name') == TARGET]
    if len(matches) != 1:
        raise ProfileError('perception_project_target')
    phases = []
    for identifier in matches[0].get('buildPhases', []):
        value = objects.get(identifier)
        if isinstance(value, dict) and value.get('isa') == 'PBXSourcesBuildPhase':
            phases.append(value)
    if len(phases) != 1:
        raise ProfileError('perception_project_sources_phase')
    records = []
    for identifier in phases[0].get('files', []):
        build = objects.get(identifier)
        if not isinstance(build, dict) or build.get('isa') != 'PBXBuildFile':
            raise ProfileError('perception_project_build_file')
        reference = objects.get(build.get('fileRef'))
        if not isinstance(reference, dict) or reference.get('isa') != 'PBXFileReference':
            raise ProfileError('perception_project_file_reference')
        path = reference.get('path')
        if not isinstance(path, str):
            raise ProfileError('perception_project_file_path')
        if Path(path).name == SOURCE:
            resolved = source_path(build['fileRef']).as_posix()
            if resolved != 'LoopCtrlUITests/' + SOURCE:
                raise ProfileError('perception_project_wrong_source')
            flags = build.get('settings', {}).get('COMPILER_FLAGS', '')
            if isinstance(flags, str):
                flags = shlex.split(flags)
            elif not isinstance(flags, list) or not all(isinstance(flag, str) for flag in flags):
                raise ProfileError('perception_project_compiler_flags_type')
            records.append({'file_ref': build['fileRef'], 'path': resolved, 'flags': flags})
    if len(records) != 1:
        raise ProfileError('perception_project_source_count')
    for target in objects.values():
        if not isinstance(target, dict) or target.get('isa') != 'PBXNativeTarget' or target is matches[0]:
            continue
        for identifier in target.get('buildPhases', []):
            phase = objects.get(identifier, {})
            if phase.get('isa') != 'PBXSourcesBuildPhase':
                continue
            for build_id in phase.get('files', []):
                build = objects.get(build_id, {})
                reference = objects.get(build.get('fileRef'), {})
                path = reference.get('path')
                if isinstance(path, str) and Path(path).name == SOURCE:
                    raise ProfileError('perception_project_extra_target')
    if records[0]['flags'] != FLAGS:
        raise ProfileError('NG2Perception_strict_O2_is_applied_once')
    return {'format_version': 1, 'target': TARGET, 'source': SOURCE,
            'source_count': 1, 'compiler_flags': FLAGS}


def inspect_project(upstream):
    upstream = Path(upstream).resolve()
    path = upstream / 'LoopCtrl.xcodeproj/project.pbxproj'
    if path.is_symlink() or not path.is_file():
        raise ProfileError('perception_project_missing')
    result = project_contract(read_project(path))
    result['project_sha256'] = digest(path.read_bytes())
    result['source_sha256'] = digest((upstream / 'LoopCtrlUITests' / SOURCE).read_bytes())
    return result


def old_blob(path):
    return subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=REPO)


def baseline_red(upstream, output):
    upstream, output = Path(upstream).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    current = checked_run(['git', 'rev-parse', 'HEAD'], cwd=upstream).stdout.strip()
    if current != UPSTREAM:
        raise ValueError('perception_baseline_upstream')
    stage = output / 'baseline-driver'
    stage.mkdir(exist_ok=True)
    for name in ('apply_patch.py', 'source-manifest.json', 'ngg1.patch',
                 'apply_ngg2.py', 'ngg2-manifest.json', 'ngg2.patch'):
        (stage / name).write_bytes(old_blob('patches/loopctrl/' + name))
    manifest = json.loads((stage / 'ngg2-manifest.json').read_text())
    assets = stage / 'ngg2'
    assets.mkdir(exist_ok=True)
    for value in manifest['additions'].values():
        name = value['source']
        (assets / name).write_bytes(old_blob('patches/loopctrl/ngg2/' + name))
    for name in ('apply_patch.py', 'apply_ngg2.py'):
        result = checked_run([sys.executable, stage / name, upstream])
        (output / (name + '.txt')).write_text(result.stdout + result.stderr)
    generated = checked_run(['xcodegen', 'generate', '--spec', 'project.yml'], cwd=upstream)
    (output / 'xcodegen-baseline.txt').write_text(generated.stdout + generated.stderr)
    # A separate executable invocation proves the assertion was reached only
    # after generation and source installation succeeded.
    observed = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--project',
        str(upstream), str(output / 'old-project')], capture_output=True, text=True, timeout=120)
    (output / 'perception-project-baseline-red.txt').write_text(observed.stdout + observed.stderr)
    if (observed.returncode != 1 or observed.stderr
            or observed.stdout.strip().splitlines()[-1:] != [EXPECTED_RED]):
        raise RuntimeError('perception_generated_project_assertion_red_missing: '
                           + observed.stdout + observed.stderr)
    result = {'format_version': 1, 'baseline_commit': BASELINE,
              'upstream_commit': UPSTREAM, 'generated_project': True,
              'assertion_returncode': 1, 'assertion_red': EXPECTED_RED,
              'device_acceptance': 'not_run'}
    (output / 'perception-project-baseline.json').write_text(json.dumps(result, indent=2) + '\n')
    print(EXPECTED_RED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--red-only', action='store_true')
    mode.add_argument('--project', action='store_true')
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.red_only:
        baseline_red(args.upstream, args.output)
    else:
        try:
            result = inspect_project(args.upstream)
        except ProfileError as error:
            print('FAIL ' + str(error))
            return 1
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'perception-project-profile.json').write_text(json.dumps(result, indent=2) + '\n')
        print('PASS NG2Perception_strict_O2_is_applied_once')
    return 0


if __name__ == '__main__':
    sys.exit(main())
