"""Verify the generated, source-specific strict Perception build profile.

The baseline reconstructs the delivered TEST048 sources, generates a real
Xcode project, and requires the new contract to fail on its missing flags.
It never treats generation, missing sources, or API/setup errors as that Red.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = '8e72974a8ab93de853d7362c3d00b7cac1a39a42'
UPSTREAM = '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767'
TARGET = 'LoopCtrlUITests'
SOURCE = 'NG2Perception.c'
FLAGS = ['-O2', '-fno-fast-math', '-ffp-contract=off']
EXPECTED_RED = 'FAIL NG2Perception_strict_O2_is_applied_once'
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_RESPONSE_TOTAL = 2 * 1024 * 1024
MAX_RESPONSE_FILES = 32
MAX_RESPONSE_DEPTH = 8
MAX_RESPONSE_TOKENS = 32768
MAX_BUILD_LOG_BYTES = 64 * 1024 * 1024
NATIVE_C = ('NG2Beat.c', 'NG2Controller.c', 'NG2Navigation.c', SOURCE)
SWIFT_TARGETS = {'LoopCtrl', 'LoopCtrlAllInOne', TARGET,
                 'LoopCtrlBroadcast', 'LoopCtrlLiveActivity'}


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


def _bounded_tokens(value):
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    result = []
    try:
        for token in lexer:
            if len(result) >= MAX_RESPONSE_TOKENS or len(token) > MAX_RESPONSE_BYTES:
                raise ProfileError('perception_response_token_limit')
            result.append(token)
    except ValueError as error:
        raise ProfileError('perception_response_quoting') from error
    return result


def effective_flags(args, expected_optimization='-O2'):
    """Audit final optimization and reject independent unsafe FP switches.

    A canonical strict profile rejects unsafe enabling switches even if a
    later disabling option happens to override them. This makes the evidence
    fail closed for ambiguous driver/frontend interactions.
    """
    if not isinstance(args, (list, tuple)) or not all(isinstance(x, str) for x in args):
        raise ProfileError('perception_arguments_type')
    flattened = []
    index = 0
    while index < len(args):
        token = args[index]
        # This build profile has no legitimate frontend/LLVM forwarding.
        # Accepting arbitrary forwarded aliases makes a small math denylist
        # unsound. A future legitimate exception needs an explicit review.
        if token in ('-Xclang', '-mllvm') or token.startswith(('-Xclang=', '-mllvm=')):
            raise ProfileError('perception_forwarded_argument')
        flattened.append(token)
        index += 1
    unsafe = {'-ffast-math', '-funsafe-math-optimizations', '-fassociative-math',
              '-freciprocal-math', '-ffinite-math-only', '-fno-signed-zeros',
              '-fno-trapping-math', '-fapprox-func', '-fno-honor-infinities',
              '-fno-honor-nans', '-menable-unsafe-fp-math',
              '-enable-unsafe-fp-math', '-enable-no-infs-fp-math',
              '-enable-no-nans-fp-math', '-enable-no-signed-zeros-fp-math',
              '-enable-no-trapping-fp-math', '-menable-no-infs',
              '-menable-no-nans', '-mreassociate'}
    if any(token in unsafe or token in ('-Ofast', '-ffp-model', '-mdaz-ftz', '-fdenormal-fp-math')
           or token.startswith(('-ffp-model=', '-ffp-math=', '-fdenormal-fp-math=',
                                '-fdenormal-fp-math-f32=', '-ffp-exception-behavior=',
                                '-fexcess-precision=', '-ffp-eval-method='))
           or token.startswith(('-D__FAST_MATH__', '-D__FINITE_MATH_ONLY__=1'))
           for token in flattened):
        raise ProfileError('perception_unsafe_fp_option')
    optimizations = [token for token in flattened if re.fullmatch(r'-O(?:[0-9]+|s|z|g|fast)?', token)]
    if not optimizations or optimizations[-1] != expected_optimization:
        raise ProfileError('perception_effective_optimization')
    contracts = [token.split('=', 1)[1] for token in flattened if token.startswith('-ffp-contract=')]
    contract = contracts[-1] if contracts else 'default'
    if expected_optimization == '-O2':
        if '-fno-fast-math' not in flattened or contract != 'off':
            raise ProfileError('perception_strict_fp_options')
    return {'optimization': optimizations[-1], 'fast_math': False, 'fp_contract': contract}


def _safe_build_file(upstream, name):
    upstream = Path(upstream).resolve()
    supplied = Path(name)
    if '..' in supplied.parts or not str(name):
        raise ProfileError('perception_response_path')
    candidate = supplied if supplied.is_absolute() else upstream / supplied
    build = upstream / 'build'
    try:
        relative = candidate.relative_to(build)
    except ValueError as error:
        raise ProfileError('perception_response_outside_build') from error
    current = build
    if current.is_symlink():
        raise ProfileError('perception_response_symlink')
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            raise ProfileError('perception_response_symlink')
    if not current.is_file():
        raise ProfileError('perception_response_missing')
    return current, current.relative_to(upstream).as_posix()


def expand_response_args(args, upstream, proofdir):
    """Expand response files as data, relative to the actual command cwd."""
    if not isinstance(args, (list, tuple)) or not all(isinstance(x, str) for x in args):
        raise ProfileError('perception_arguments_type')
    upstream, proofdir = Path(upstream).resolve(), Path(proofdir)
    records = []
    total_bytes = 0
    total_tokens = 0
    previous_token = None

    def read_response(relative, before):
        # Walk from an opened source root. Every path component is admitted
        # without following symlinks, including replacements after validation.
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        descriptors = []
        file_descriptor = None

        def identity(info):
            return (info.st_dev, info.st_ino, info.st_size,
                    info.st_mtime_ns, info.st_ctime_ns)

        try:
            descriptors.append(os.open(upstream, directory_flags))
            descriptors.append(os.open('build', directory_flags, dir_fd=descriptors[-1]))
            components = Path(relative).parts[1:]
            for component in components[:-1]:
                descriptors.append(os.open(component, directory_flags,
                                           dir_fd=descriptors[-1]))
            file_descriptor = os.open(components[-1], file_flags, dir_fd=descriptors[-1])
            opened = os.fstat(file_descriptor)
            if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
                raise ProfileError('perception_response_changed')
            with os.fdopen(file_descriptor, 'rb') as source:
                file_descriptor = None  # fdopen owns and closes the descriptor.
                raw = source.read(MAX_RESPONSE_BYTES + 1)
                after = os.fstat(source.fileno())
            if identity(after) != identity(opened):
                raise ProfileError('perception_response_changed')
            return raw
        except OSError as error:
            raise ProfileError('perception_response_changed') from error
        finally:
            if file_descriptor is not None:
                os.close(file_descriptor)
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def expand(tokens, active=()):
        nonlocal total_bytes, total_tokens, previous_token
        result = []
        for token in tokens:
            # Swift driver link commands contain Mach-O install names/rpaths.
            # These are linker data only when they are the direct flattened
            # payload of -Xlinker; every other @ token remains a response file.
            loader_literal = previous_token == '-Xlinker' and any(
                token == prefix or token.startswith(prefix + '/')
                for prefix in ('@rpath', '@executable_path', '@loader_path'))
            if token.startswith('@') and not loader_literal:
                if len(active) >= MAX_RESPONSE_DEPTH or len(records) >= MAX_RESPONSE_FILES:
                    raise ProfileError('perception_response_expansion_limit')
                path, relative = _safe_build_file(upstream, token[1:])
                if relative in active:
                    raise ProfileError('perception_response_cycle')
                try:
                    before = path.stat(follow_symlinks=False)
                except OSError as error:
                    raise ProfileError('perception_response_changed') from error
                if not stat.S_ISREG(before.st_mode):
                    raise ProfileError('perception_response_changed')
                if before.st_size > MAX_RESPONSE_BYTES or total_bytes + before.st_size > MAX_RESPONSE_TOTAL:
                    raise ProfileError('perception_response_byte_limit')
                # Enforce both individual and cumulative budgets before opening
                # the next file, then retain a bound in the read itself.
                total_bytes += before.st_size
                raw = read_response(relative, before)
                if len(raw) != before.st_size or len(raw) > MAX_RESPONSE_BYTES:
                    raise ProfileError('perception_response_changed')
                try:
                    contents = raw.decode('utf-8')
                except UnicodeDecodeError as error:
                    raise ProfileError('perception_response_encoding') from error
                sha = digest(raw)
                saved = 'response-' + sha + '.rsp'
                records.append({'path': relative, 'sha256': sha,
                                'bytes': len(raw), 'saved_as': saved})
                proofdir.mkdir(parents=True, exist_ok=True)
                (proofdir / saved).write_bytes(raw)
                result.extend(expand(_bounded_tokens(contents), (*active, relative)))
            else:
                total_tokens += 1
                if total_tokens > MAX_RESPONSE_TOKENS:
                    raise ProfileError('perception_response_token_limit')
                result.append(token)
                previous_token = token
        return result

    return expand(args), records


def _option(args, option):
    indexes = [index for index, value in enumerate(args) if value == option]
    if len(indexes) != 1 or indexes[0] + 1 >= len(args):
        raise ProfileError('perception_compile_option_' + option.lstrip('-'))
    return args[indexes[0] + 1]


def inspect_compile_log(upstream, log, proofdir):
    upstream, log, proofdir = Path(upstream).resolve(), Path(log), Path(proofdir)
    if log.is_symlink() or not log.is_file() or log.stat().st_size > MAX_BUILD_LOG_BYTES:
        raise ProfileError('perception_compile_log_size')
    with log.open('rb') as source:
        raw = source.read(MAX_BUILD_LOG_BYTES + 1)
    if len(raw) > MAX_BUILD_LOG_BYTES:
        raise ProfileError('perception_compile_log_size')
    try:
        lines = raw.decode('utf-8').splitlines()
    except UnicodeDecodeError as error:
        raise ProfileError('perception_compile_log_encoding') from error
    project = inspect_project(upstream)
    compiles = {name: [] for name in NATIVE_C}
    swift = {}
    swift_compiles = []
    responses = {}

    def retain_responses(used):
        for record in used:
            previous = responses.get(record['path'])
            if previous is not None and previous != record:
                raise ProfileError('perception_response_changed_between_compiles')
            responses[record['path']] = record

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if 'clang' not in stripped and 'swiftc' not in stripped:
            continue
        command_shape = stripped.startswith(('/', "'", '"', 'builtin-SwiftDriver '))
        if len(stripped) > MAX_RESPONSE_TOTAL:
            if command_shape:
                raise ProfileError('perception_compile_line_limit')
            continue
        try:
            args = _bounded_tokens(stripped)
        except ProfileError:
            if command_shape:
                raise
            continue
        if not args:
            continue
        if args[0] == 'builtin-SwiftDriver' and len(args) > 2 and args[1] == '--':
            args = args[2:]
        executable = Path(args[0]).name
        if executable not in ('swiftc', 'clang'):
            continue
        # Both compiler selection flags and optimization flags may be hidden
        # entirely in a response file. Expand before looking for -c/module.
        expanded, used = expand_response_args(args, upstream, proofdir)
        if executable == 'swiftc':
            if '-module-name' not in expanded:
                continue
            module = _option(expanded, '-module-name')
            if module in SWIFT_TARGETS:
                modes = [value for value in expanded if value in ('-Onone', '-O', '-Osize', '-Ounchecked')]
                if not modes or modes[-1] != '-Onone':
                    raise ProfileError('perception_swift_optimization_changed')
                swift[module] = modes[-1]
                swift_compiles.append({'module': module, 'compiler': expanded[0],
                    'optimization': modes[-1], 'arguments': expanded,
                    'raw_arguments': args, 'command_sha256': digest(stripped.encode()),
                    'response_sha256': [item['sha256'] for item in used]})
                retain_responses(used)
            continue
        # Dependency scanners quote the same Clang command. They do not compile
        # an object and must not become duplicate evidence records.
        if '-c' not in expanded:
            continue
        source_name = Path(_option(expanded, '-c')).name
        if source_name not in NATIVE_C:
            continue
        supplied = Path(_option(expanded, '-c'))
        if not supplied.is_absolute():
            supplied = upstream / supplied
        expected_source = upstream / 'LoopCtrlUITests' / source_name
        if supplied != expected_source or supplied.is_symlink() or not supplied.is_file():
            raise ProfileError('perception_compile_wrong_source')
        target = _option(expanded, '-target')
        if not target.startswith('arm64-apple-ios'):
            raise ProfileError('perception_compile_wrong_arch')
        output = Path(_option(expanded, '-o'))
        if not output.is_absolute():
            output = upstream / output
        try:
            output_relative = output.relative_to(upstream / 'build')
        except ValueError as error:
            raise ProfileError('perception_compile_wrong_output') from error
        if ('..' in output_relative.parts or 'Debug-iphoneos' not in output_relative.parts
                or TARGET + '.build' not in output_relative.parts
                or output.name != Path(source_name).stem + '.o'):
            raise ProfileError('perception_compile_wrong_target')
        profile = effective_flags(expanded, '-O2' if source_name == SOURCE else '-O0')
        compiles[source_name].append(dict(profile, target=TARGET, arch='arm64',
            source='LoopCtrlUITests/' + source_name,
            source_sha256=digest(supplied.read_bytes()),
            object=output.relative_to(upstream).as_posix(),
            compiler=expanded[0], target_triple=target,
            arguments=expanded, raw_arguments=args,
            command_sha256=digest(stripped.encode()),
            response_sha256=[item['sha256'] for item in used]))
        retain_responses(used)
    if any(not records for records in compiles.values()) or TARGET not in swift:
        raise ProfileError('perception_compile_evidence_missing')
    return {'format_version': 1, 'profile': 'strict-O2-v1', 'target': TARGET,
            'arch': 'arm64', 'source_sha256': project['source_sha256'],
            'project_profile': project, 'perception_compiles': compiles[SOURCE],
            'other_c_profiles': {name: compiles[name] for name in NATIVE_C if name != SOURCE},
            'swift_optimization': '-Onone', 'swift_profiles': swift,
            'swift_compiles': swift_compiles, 'upstream_root': str(upstream),
            'response_files': sorted(responses.values(), key=lambda item: item['path']),
            'build_log_sha256': digest(raw)}


def read_compile_profile(upstream):
    """Require the actual compile evidence at the package-writing callsite."""
    upstream = Path(upstream).resolve()
    path = upstream / 'release/native-perception-profile.json'
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        raise ProfileError('perception_compile_profile_missing')
    limit = 4 * 1024 * 1024
    if path.stat().st_size > limit:
        raise ProfileError('perception_compile_profile_size')
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ProfileError('perception_compile_profile_size')
    try:
        profile = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise ProfileError('perception_compile_profile_json') from error
    if (not isinstance(profile, dict) or type(profile.get('format_version')) is not int
            or profile['format_version'] != 1 or profile.get('profile') != 'strict-O2-v1'
            or profile.get('target') != TARGET or profile.get('arch') != 'arm64'
            or profile.get('upstream_root') != str(upstream)):
        raise ProfileError('perception_compile_profile_identity')
    def is_digest(value):
        return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None

    if not is_digest(profile.get('build_log_sha256')):
        raise ProfileError('perception_compile_profile_digest')
    project = inspect_project(upstream)
    if profile.get('project_profile') != project or profile.get('source_sha256') != project['source_sha256']:
        raise ProfileError('perception_compile_profile_source')
    project_record = profile['project_profile']
    if (type(project_record.get('format_version')) is not int
            or type(project_record.get('source_count')) is not int):
        raise ProfileError('perception_compile_profile_project_type')
    other = profile.get('other_c_profiles')
    if not isinstance(other, dict) or set(other) != set(NATIVE_C) - {SOURCE}:
        raise ProfileError('perception_compile_profile_other_sources')
    records = {SOURCE: profile.get('perception_compiles'), **other}
    actual_responses = {}
    with tempfile.TemporaryDirectory(prefix='perception-profile-check-') as temporary:
        def check_arguments(record):
            if not isinstance(record, dict):
                raise ProfileError('perception_compile_profile_record')
            if not is_digest(record.get('command_sha256')):
                raise ProfileError('perception_compile_profile_digest')
            args = record.get('raw_arguments')
            expanded, used = expand_response_args(args, upstream, temporary)
            if (expanded != record.get('arguments') or not expanded
                    or record.get('compiler') != expanded[0]
                    or [item['sha256'] for item in used] != record.get('response_sha256')):
                raise ProfileError('perception_compile_profile_arguments')
            for response in used:
                previous = actual_responses.get(response['path'])
                if previous is not None and previous != response:
                    raise ProfileError('perception_response_changed_between_compiles')
                actual_responses[response['path']] = response
            return expanded

        for name, rows in records.items():
            if not isinstance(rows, list) or not 1 <= len(rows) <= 16:
                raise ProfileError('perception_compile_profile_count')
            source_path = upstream / 'LoopCtrlUITests' / name
            expected_sha = digest(source_path.read_bytes())
            for row in rows:
                args = check_arguments(row)
                expected = '-O2' if name == SOURCE else '-O0'
                flags = effective_flags(args, expected)
                if (Path(args[0]).name != 'clang' or row.get('target') != TARGET
                        or row.get('arch') != 'arm64' or row.get('source') != 'LoopCtrlUITests/' + name
                        or row.get('source_sha256') != expected_sha
                        or row.get('fast_math') is not False
                        or type(row.get('object')) is not str
                        or any(row.get(key) != value for key, value in flags.items())):
                    raise ProfileError('perception_compile_profile_record')
                supplied = Path(_option(args, '-c'))
                if not supplied.is_absolute():
                    supplied = upstream / supplied
                triple = _option(args, '-target')
                supplied_object = Path(_option(args, '-o'))
                if not supplied_object.is_absolute():
                    supplied_object = upstream / supplied_object
                if (supplied != source_path or not triple.startswith('arm64-apple-ios')
                        or row.get('target_triple') != triple
                        or supplied_object != upstream / row.get('object', '')
                        or 'Debug-iphoneos' not in supplied_object.parts
                        or TARGET + '.build' not in supplied_object.parts
                        or supplied_object.name != Path(name).stem + '.o'
                        or '..' in Path(row.get('object', '')).parts
                        or Path(row['object']).as_posix() != row['object']
                        or not str(row.get('object', '')).startswith('build/')):
                    raise ProfileError('perception_compile_profile_paths')
        swift_rows = profile.get('swift_compiles')
        if not isinstance(swift_rows, list) or not 1 <= len(swift_rows) <= 32:
            raise ProfileError('perception_compile_profile_swift')
        modules = {}
        for row in swift_rows:
            args = check_arguments(row)
            module = _option(args, '-module-name')
            modes = [value for value in args if value in ('-Onone', '-O', '-Osize', '-Ounchecked')]
            if (Path(args[0]).name != 'swiftc' or module not in SWIFT_TARGETS
                    or row.get('module') != module or not modes or modes[-1] != '-Onone'
                    or row.get('optimization') != '-Onone'):
                raise ProfileError('perception_compile_profile_swift')
            modules[module] = '-Onone'
        if (TARGET not in modules or profile.get('swift_profiles') != modules
                or profile.get('swift_optimization') != '-Onone'):
            raise ProfileError('perception_compile_profile_swift')
    response_records = profile.get('response_files')
    if not isinstance(response_records, list) or len(response_records) > 4096:
        raise ProfileError('perception_compile_profile_responses')
    for record in response_records:
        if (not isinstance(record, dict) or set(record) != {'path', 'sha256', 'bytes', 'saved_as'}
                or type(record.get('path')) is not str or not record['path'].startswith('build/')
                or '..' in Path(record['path']).parts or Path(record['path']).as_posix() != record['path']
                or not is_digest(record.get('sha256')) or type(record.get('bytes')) is not int
                or not 0 <= record['bytes'] <= MAX_RESPONSE_BYTES
                or record.get('saved_as') != 'response-' + record['sha256'] + '.rsp'):
            raise ProfileError('perception_compile_profile_responses')
    if response_records != sorted(actual_responses.values(), key=lambda item: item['path']):
        raise ProfileError('perception_compile_profile_responses')
    return profile


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
    mode.add_argument('--compile-profile', action='store_true')
    parser.add_argument('upstream', type=Path)
    parser.add_argument('paths', type=Path, nargs='+')
    args = parser.parse_args()
    if args.red_only:
        if len(args.paths) != 1:
            parser.error('--red-only requires upstream and output directory')
        baseline_red(args.upstream, args.paths[0])
    elif args.compile_profile:
        if len(args.paths) != 2:
            parser.error('--compile-profile requires upstream, actual build log and output directory')
        log, output = args.paths
        output.mkdir(parents=True, exist_ok=True)
        result = inspect_compile_log(args.upstream, log, output)
        (output / 'perception-project-profile.json').write_text(json.dumps(result['project_profile'], indent=2) + '\n')
        project_path = args.upstream / 'LoopCtrl.xcodeproj/project.pbxproj'
        (output / 'perception-project-model.json').write_text(json.dumps(read_project(project_path), indent=2) + '\n')
        (output / 'perception-compile-profile.json').write_text(json.dumps(result, indent=2) + '\n')
        release = args.upstream / 'release'
        release.mkdir(exist_ok=True)
        (release / 'native-perception-profile.json').write_text(json.dumps(result, indent=2) + '\n')
        # Apply the same validation that the package-writing callsite requires.
        read_compile_profile(args.upstream)
        print('PASS actual_Clang_Perception_strict_O2_and_other_profiles_unchanged')
    else:
        if len(args.paths) != 1:
            parser.error('--project requires upstream and output directory')
        output = args.paths[0]
        try:
            result = inspect_project(args.upstream)
        except ProfileError as error:
            print('FAIL ' + str(error))
            return 1
        output.mkdir(parents=True, exist_ok=True)
        (output / 'perception-project-profile.json').write_text(json.dumps(result, indent=2) + '\n')
        (output / 'perception-project-model.json').write_text(json.dumps(read_project(args.upstream / 'LoopCtrl.xcodeproj/project.pbxproj'), indent=2) + '\n')
        print('PASS NG2Perception_strict_O2_is_applied_once')
    return 0


if __name__ == '__main__':
    sys.exit(main())
