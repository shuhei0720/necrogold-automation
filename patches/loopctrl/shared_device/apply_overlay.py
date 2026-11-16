"""Guarded source-only shared-device overlay; no build, IPA, device or signing actions.

Production CLI accepts only the upstream checkout. Its manifest/patch/assets and
the old baseline pins are fixed here, not supplied by a caller. ``_apply`` is the
private unit seam for synthetic independently trusted baseline maps. Per-file
rename is atomic; this is not a crash/power-loss-proof multi-file transaction.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
from types import MappingProxyType


UPSTREAM = '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767'
HERE = Path(__file__).resolve().parent
BASELINE_PINS = MappingProxyType({
    'source-manifest.json': '0ecd13d76591a5251f2df4614a59e69138812f80b6dcd06885dd7705df41ad92',
    'ngg1.patch': 'f9508cd394d3f57c0f44583effad8d43fb5de363dbf6f61df81bf5dbfa1215e2',
    'ngg2-manifest.json': '9d1737ba60623660a3167415ab1d6dca57357cd2d3406bbbc893af04eca8b2aa',
    'ngg2.patch': 'e6e764ae5e920ab8bd9e7b5527056ee52a68349f77afc1367524919509458438',
})
ALLOWED_TARGETS = frozenset({
    'LoopCtrlUITests/NG2Runtime.swift',
    'LoopCtrlUITests/NG2Perception.c', 'LoopCtrlUITests/NG2Navigation.c',
    'LoopCtrlUITests/XCTestPrivate-Bridging-Header.h', 'project.yml',
    'LoopCtrlApp/Info.plist', 'LoopCtrlApp/AllInOne-Info.plist',
})
ALLOWED_ASSETS = frozenset({
    'NG2DeviceGeometryProfile.h', 'NG2DeviceGeometryProfile.c',
    'NG2DeviceRaster.h', 'NG2DeviceRaster.c', 'NG2DeviceRaster.swift',
    'NG2Startup.swift', 'NG2DeviceBuildInfo.plist',
    'NG2MotionSupport.h', 'NG2WorldSupport.c', 'NG2WorldSupport.h',
})
MAX_SOURCE = 8 * 1024 * 1024
MAX_ADDITIONS = 32


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _name(value):
    if (type(value) is not str or not value or len(value) > 256
            or '\\' in value or '\0' in value or ':' in value
            or PurePosixPath(value).is_absolute()
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('unsafe_path')
    return value


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    if len(raw) > 1024 * 1024:
        raise ValueError('manifest_too_large')
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('invalid_json') from error


def _root(path):
    path = Path(path).absolute()
    if path.is_symlink() or not path.is_dir():
        raise ValueError('invalid_root')
    # Canonicalize OS aliases such as macOS /tmp; paths inside this root are
    # opened component-by-component without following a symlink.
    return path.resolve(strict=True)


def _directory(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('invalid_directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except OSError as error:
        os.close(fd)
        raise ValueError('invalid_directory') from error


def _parent(root_fd, name):
    parts = _name(name).split('/')
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except OSError as error:
        os.close(fd)
        raise ValueError('invalid_source_parent') from error


def _read_at(parent_fd, leaf):
    try:
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_SOURCE:
                raise ValueError('invalid_source_file')
            raw = stream.read(MAX_SOURCE + 1)
            after = os.fstat(stream.fileno())
        signature = lambda row: (row.st_dev, row.st_ino, row.st_size,
                                  row.st_mtime_ns, row.st_ctime_ns, row.st_mode)
        if len(raw) > MAX_SOURCE or signature(before) != signature(after):
            raise ValueError('source_changed_while_reading')
        return raw, after
    except OSError as error:
        raise ValueError('invalid_source_file') from error


def _read(root_fd, name):
    parent, leaf = _parent(root_fd, name)
    try:
        return _read_at(parent, leaf)
    finally:
        os.close(parent)


def _read_path(path):
    path = Path(path).absolute()
    if path.parent.resolve(strict=True) != path.parent:
        raise ValueError('invalid_source_parent')
    parent = _directory(path.parent)
    try:
        return _read_at(parent, path.name)[0]
    finally:
        os.close(parent)


def _absent(root_fd, name):
    parent, leaf = _parent(root_fd, name)
    try:
        try:
            os.stat(leaf, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise ValueError('destination_exists')
    finally:
        os.close(parent)


def _validate(manifest, baseline):
    manifest = copy.deepcopy(manifest)
    if (type(manifest) is not dict or set(manifest) != {
            'schema', 'upstream_commit', 'baseline', 'patch_sha256', 'files', 'additions'}
            or manifest['schema'] != 'ng2-shared-device-overlay-v1'
            or manifest['upstream_commit'] != UPSTREAM
            or manifest['baseline'] != dict(BASELINE_PINS)
            or not _sha(manifest['patch_sha256'])):
        raise ValueError('invalid_manifest_identity')
    files, additions = manifest['files'], manifest['additions']
    if (type(files) is not dict or not files or type(additions) is not dict
            or not additions or len(additions) > MAX_ADDITIONS):
        raise ValueError('invalid_manifest_inventory')
    for name, spec in files.items():
        _name(name)
        if name not in ALLOWED_TARGETS:
            raise ValueError('integration_target_forbidden')
        if (type(spec) is not dict or set(spec) != {'base_sha256', 'final_sha256'}
                or not _sha(spec['base_sha256']) or not _sha(spec['final_sha256'])
                or baseline.get(name) != spec['base_sha256']):
            raise ValueError('untrusted_base_preimage')
    seen = set()
    for name, spec in additions.items():
        _name(name)
        if type(spec) is not dict or set(spec) != {'source', 'sha256'} or not _sha(spec['sha256']):
            raise ValueError('invalid_addition')
        source = _name(spec['source'])
        if source not in ALLOWED_ASSETS:
            raise ValueError('invalid_asset_name')
        expected = 'LoopCtrlUITests/' + source
        if name != expected or name in baseline or name in files or source in seen:
            raise ValueError('invalid_addition_target')
        seen.add(source)
    return manifest


def _assets(assets_root, additions):
    supplied = Path(assets_root).absolute()
    if supplied.parent.resolve(strict=True) != supplied.parent:
        raise ValueError('invalid_source_parent')
    root = _root(assets_root)
    if {path.name for path in root.iterdir()} != {value['source'] for value in additions.values()}:
        raise ValueError('asset_inventory_mismatch')
    fd = _directory(root)
    try:
        result = {}
        for name, spec in additions.items():
            raw, _ = _read(fd, spec['source'])
            if digest(raw) != spec['sha256']:
                raise ValueError('asset_hash_mismatch')
            result[name] = raw
        return result
    finally:
        os.close(fd)


def _patch_headers(raw, expected):
    try:
        lines = raw.decode('utf-8').splitlines()
    except UnicodeError as error:
        raise ValueError('invalid_patch_encoding') from error
    if any(line.startswith(('rename ', 'copy ', 'new file mode ', 'deleted file mode ',
                            'old mode ', 'new mode ', 'GIT binary patch', 'Binary files ')) for line in lines):
        raise ValueError('unsupported_patch_operation')
    headers = [line for line in lines if line.startswith(('--- ', '+++ '))]
    required = [line for name in expected for line in ('--- a/' + name, '+++ b/' + name)]
    if headers != required:
        raise ValueError('patch_target_mismatch')


def _run_patch(stage, raw):
    for options in (['--check'], []):
        result = subprocess.run(['git', 'apply', '--no-index', *options, '-'],
                                input=raw, cwd=stage, capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError('patch_rejected')


def _verify_map(root_fd, expected):
    for name, sha in expected.items():
        if digest(_read(root_fd, name)[0]) != sha:
            raise ValueError('source_hash_mismatch')


def _new_inventory(root, additions):
    found = set()
    for directory in ('LoopCtrlKit', 'LoopCtrlUITests'):
        parent = root / directory
        if parent.is_symlink():
            raise ValueError('invalid_source_parent')
        if parent.is_dir():
            found.update(path.relative_to(root).as_posix() for path in parent.rglob('*')
                         if path.name.startswith(('NG2Device', 'NG2Startup', 'NG2MotionSupport', 'NG2WorldSupport')))
    if found != set(additions):
        raise ValueError('destination_inventory_mismatch')


def effective_expected_map(manifest, baseline):
    """Strict dual-seal source map; not an IPA/compiler acceptance report."""
    manifest = _validate(manifest, baseline)
    return {**baseline, **{name: spec['final_sha256'] for name, spec in manifest['files'].items()},
            **{name: spec['sha256'] for name, spec in manifest['additions'].items()}}


def _apply(root, manifest, patch_path, assets_root, baseline, *, production=False):
    """Private synthetic-unit seam; production independently derives baseline."""
    root = _root(root)
    manifest = _validate(manifest, baseline)
    files, additions = manifest['files'], manifest['additions']
    patch_raw = _read_path(patch_path)
    if digest(patch_raw) != manifest['patch_sha256']:
        raise ValueError('patch_hash_mismatch')
    _patch_headers(patch_raw, files)
    assets = _assets(assets_root, additions)
    expected = effective_expected_map(manifest, baseline)
    root_fd = _directory(root)
    installed = []
    try:
        root_identity = os.fstat(root_fd)
        _verify_map(root_fd, baseline)
        _new_inventory(root, {})
        for name in additions:
            _absent(root_fd, name)
        original = {name: _read(root_fd, name) for name in files}
        with tempfile.TemporaryDirectory(prefix='.ng2-shared-overlay-stage-', dir=root) as temporary:
            stage = Path(temporary)
            for name, (raw, mode) in original.items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                target.chmod(stat.S_IMODE(mode.st_mode))
            _run_patch(stage, patch_raw)
            if {p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file() or p.is_symlink()} != set(files):
                raise ValueError('unexpected_staged_inventory')
            for name, raw in assets.items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            backup = stage / '.rollback'
            backup.mkdir()
            for index, name in enumerate(files):
                (backup / str(index)).write_bytes(original[name][0])
                (backup / str(index)).chmod(stat.S_IMODE(original[name][1].st_mode))
            stage_fd, backup_fd = _directory(stage), _directory(backup)
            current = dict(baseline)
            pending = set(additions)
            try:
                _verify_map(stage_fd, {name: expected[name] for name in [*files, *additions]})
                try:
                    for index, name in enumerate([*files, *additions]):
                        now = os.stat(root, follow_symlinks=False)
                        if (now.st_dev, now.st_ino) != (root_identity.st_dev, root_identity.st_ino):
                            raise ValueError('source_root_changed')
                        _verify_map(root_fd, current)
                        for new_name in pending:
                            _absent(root_fd, new_name)
                        if _read_path(patch_path) != patch_raw or _assets(assets_root, additions) != assets:
                            raise ValueError('overlay_input_changed')
                        source_fd, source_leaf = _parent(stage_fd, name)
                        target_fd, target_leaf = _parent(root_fd, name)
                        try:
                            # Prepare rollback ownership before the first mutation:
                            # no post-rename dup/stat may leave an unrecorded write.
                            _, owned = _read_at(source_fd, source_leaf)
                            record = [index, name, os.dup(target_fd), target_leaf, owned, False]
                            installed.append(record)
                            if name in additions:
                                # An absence check is not atomic with replace.
                                # link creates the new destination without ever
                                # clobbering a last-moment concurrent writer.
                                os.link(source_leaf, target_leaf, src_dir_fd=source_fd,
                                        dst_dir_fd=target_fd, follow_symlinks=False)
                            else:
                                os.replace(source_leaf, target_leaf, src_dir_fd=source_fd, dst_dir_fd=target_fd)
                            record[5] = True
                            if name in additions:
                                os.unlink(source_leaf, dir_fd=source_fd)
                        finally:
                            os.close(source_fd)
                            os.close(target_fd)
                        current[name] = expected[name]
                        pending.discard(name)
                    _verify_map(root_fd, expected)
                    _new_inventory(root, additions)
                    if production:
                        _checkout_delta(root, files, additions, stage.name)
                except (OSError, ValueError):
                    conflict = False
                    for index, name, target_fd, leaf, owned, completed in reversed(installed):
                        if not completed:
                            continue
                        try:
                            raw, actual = _read_at(target_fd, leaf)
                            if (digest(raw) != expected[name] or (actual.st_dev, actual.st_ino) != (owned.st_dev, owned.st_ino)):
                                conflict = True
                                continue
                            if name in original:
                                os.replace(str(index), leaf, src_dir_fd=backup_fd, dst_dir_fd=target_fd)
                            else:
                                os.unlink(leaf, dir_fd=target_fd)
                        except (OSError, ValueError):
                            conflict = True
                    if conflict:
                        raise ValueError('rollback_concurrent_change')
                    raise
            finally:
                os.close(stage_fd)
                os.close(backup_fd)
        return expected
    finally:
        for _, _, fd, _, _, _ in installed:
            os.close(fd)
        os.close(root_fd)


def _git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('fixed_git_baseline_unavailable')
    return result.stdout


def _pinned_seals():
    old = HERE.parent
    sealed = {}
    for name, expected in BASELINE_PINS.items():
        raw = _read_path(old / name)
        if digest(raw) != expected:
            raise ValueError('pinned_baseline_changed')
        if name.endswith('.json'):
            sealed[name] = _json(raw)
    return sealed


def _trusted_baseline(root):
    """Read independent old seals/Git objects, never overlay-declared preimages."""
    sealed = _pinned_seals()
    if _git(root, 'rev-parse', 'HEAD').decode().strip() != UPSTREAM:
        raise ValueError('fixed_upstream_mismatch')
    g1, g2 = sealed['source-manifest.json'], sealed['ngg2-manifest.json']
    if g1['upstream_commit'] != UPSTREAM or g2['upstream_commit'] != UPSTREAM:
        raise ValueError('fixed_upstream_mismatch')
    expected = {name: row['patched_sha256'] for name, row in g1['files'].items()}
    expected.update({name: row['patched_sha256'] for name, row in g2['files'].items()})
    expected.update({name: row['sha256'] for name, row in g2['additions'].items()})
    for name in ALLOWED_TARGETS - set(expected):
        expected[name] = digest(_git(root, 'show', UPSTREAM + ':' + name))
    return expected


def _checkout_delta(root, overlay_files=(), additions=(), owned_stage=None):
    """Reject unrelated checkout edits; never bless an arbitrary dirty base."""
    sealed = _pinned_seals()
    g1, g2 = sealed['source-manifest.json'], sealed['ngg2-manifest.json']
    changed = set(g1['files']) | set(g2['files']) | set(overlay_files)
    added = set(g2['additions']) | set(additions)
    rows = _git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all').split(b'\0')
    for row in rows:
        if not row:
            continue
        try:
            state, name = row[:2].decode('ascii'), row[3:].decode('utf-8')
        except UnicodeError as error:
            raise ValueError('unexpected_checkout_delta') from error
        if owned_stage is not None and name.startswith(owned_stage + '/'):
            continue
        if not ((state == ' M' and name in changed) or (state == '??' and name in added)):
            raise ValueError('unexpected_checkout_delta')


def apply(root):
    root = _root(root)
    baseline = _trusted_baseline(root)
    _checkout_delta(root)
    manifest = _json(_read_path(HERE / 'manifest.json'))
    return _apply(root, manifest, HERE / 'overlay.patch', HERE / 'assets', baseline, production=True)


def verify_final(root):
    """Final-tree dual-seal source verification for a later package verifier."""
    root = _root(root)
    baseline = _trusted_baseline(root)
    manifest = _validate(_json(_read_path(HERE / 'manifest.json')), baseline)
    raw = _read_path(HERE / 'overlay.patch')
    if digest(raw) != manifest['patch_sha256']:
        raise ValueError('patch_hash_mismatch')
    _patch_headers(raw, manifest['files'])
    _assets(HERE / 'assets', manifest['additions'])
    expected = effective_expected_map(manifest, baseline)
    fd = _directory(root)
    try:
        _verify_map(fd, expected)
        _new_inventory(root, manifest['additions'])
        _checkout_delta(root, manifest['files'], manifest['additions'])
    finally:
        os.close(fd)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    args = parser.parse_args()
    print(json.dumps({'schema': 'ng2-shared-device-overlay-applied-v1', 'upstream_commit': UPSTREAM,
                      'effective_source_sha256': apply(args.upstream)}, indent=2))


if __name__ == '__main__':
    main()
