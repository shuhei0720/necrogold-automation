"""固定NG-G1取得元へ、検証済みNG-G2差分とnativeソースを導入する。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
UPSTREAM_COMMIT = '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767'
PATCH_PATH = HERE / 'ngg2.patch'
MANIFEST_PATH = HERE / 'ngg2-manifest.json'
ASSETS_ROOT = HERE / 'ngg2'
ALLOWED_TARGETS = {
    'LoopCtrlUITests/ActionHandler.swift',
    'LoopCtrlUITests/LoopCtrlUITests.swift',
    'LoopCtrlUITests/ScreenStream.swift',
    'LoopCtrlUITests/ObjCException.m',
    'LoopCtrlUITests/XCTestPrivate-Bridging-Header.h',
    'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlKit/JSONRPCServer.swift',
    'LoopCtrlKit/RemoteSession.swift',
    'project.yml',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def safe_path(root, name, *, exists=True):
    relative = Path(name)
    if (not name or relative.is_absolute() or '..' in relative.parts
            or '.' in relative.parts or relative.as_posix() != name):
        raise ValueError('unsafe_manifest_path: ' + name)
    candidate = root
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            raise ValueError('symlink_source: ' + name)
    if exists and not candidate.is_file():
        raise ValueError('missing_source: ' + name)
    if not exists and candidate.exists():
        raise ValueError('destination_exists: ' + name)
    return candidate


def headers(patch_bytes):
    lines = [line for line in patch_bytes.decode('utf-8').splitlines()
             if line.startswith(('--- ', '+++ '))]
    names = []
    if not lines or len(lines) % 2:
        raise ValueError('patch_target_mismatch')
    for old, new in zip(lines[::2], lines[1::2]):
        if not old.startswith('--- a/') or not new.startswith('+++ b/'):
            raise ValueError('patch_target_mismatch')
        name = old[6:]
        if new[6:] != name or name not in ALLOWED_TARGETS or name in names:
            raise ValueError('patch_target_mismatch')
        names.append(name)
    return names


def run_patch(stage, raw):
    for options in (['--check'], []):
        result = subprocess.run(['git', 'apply', '--no-index', *options, '-'],
            input=raw, cwd=stage, capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError('patch_rejected: ' + result.stderr.decode('utf-8', errors='replace').strip())


def valid_addition(name, source):
    path = Path(name)
    if source == 'NG2RPCContractsTests.swift':
        return name == 'Tests/LoopCtrlKitTests/NG2RPCContractsTests.swift'
    return (path.parent.as_posix() == 'LoopCtrlUITests' and path.name == source
            and path.name.startswith('NG2') and path.suffix in ('.swift', '.c', '.h', '.m'))


def apply(root, manifest=None, patch_path=None, assets_root=None):
    """Validate everything before replacement; roll back replacement errors.

    Installation is per-file atomic, not a power-loss-proof filesystem
    transaction. CI always starts with a disposable fixed-commit checkout.
    """
    production = manifest is None
    if production:
        manifest = json.loads(MANIFEST_PATH.read_text())
    patch_path = PATCH_PATH if patch_path is None else Path(patch_path)
    assets_root = ASSETS_ROOT if assets_root is None else Path(assets_root)
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir() or assets_root.is_symlink() or not assets_root.is_dir():
        raise ValueError('invalid_source_root')
    if manifest.get('format_version') != 1:
        raise ValueError('manifest_format')
    if production:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        if commit != UPSTREAM_COMMIT or manifest.get('upstream_commit') != UPSTREAM_COMMIT:
            raise ValueError('upstream_commit_mismatch')
    raw_patch = patch_path.read_bytes()
    if digest(raw_patch) != manifest['patch_sha256']:
        raise ValueError('patch_hash_mismatch')
    files, additions = manifest['files'], manifest['additions']
    if headers(raw_patch) != list(files):
        raise ValueError('patch_target_mismatch')
    original, sources = {}, {}
    for name, expected in files.items():
        source = safe_path(root, name)
        raw = source.read_bytes()
        if digest(raw) != expected['sha256'] or git_blob(raw) != expected['blob']:
            raise ValueError('source_hash_mismatch: ' + name)
        sources[name], original[name] = source, raw
    assets, destinations = {}, {}
    for name, expected in additions.items():
        # Validate paths before checking the fixed destination policy.
        destination = safe_path(root, name, exists=False)
        source = safe_path(assets_root, expected['source'])
        if not valid_addition(name, expected['source']):
            raise ValueError('unsafe_addition: ' + name)
        raw = source.read_bytes()
        if digest(raw) != expected['sha256']:
            raise ValueError('asset_hash_mismatch: ' + name)
        assets[name], destinations[name] = raw, destination
    inventory = {p.name for p in assets_root.iterdir()
                 if p.name.startswith('NG2') and p.suffix in ('.swift', '.c', '.h', '.m')}
    if inventory != {spec['source'] for spec in additions.values()}:
        raise ValueError('asset_inventory_mismatch')
    with tempfile.TemporaryDirectory(prefix='.ngg2-stage-', dir=root) as temporary:
        stage = Path(temporary)
        for name, raw in original.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        run_patch(stage, raw_patch)
        if {p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()} != set(files):
            raise ValueError('unexpected_staged_files')
        for name, expected in files.items():
            if digest((stage / name).read_bytes()) != expected['patched_sha256']:
                raise ValueError('patched_hash_mismatch: ' + name)
        for name, raw in assets.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        # A concurrent edit must not be overwritten, including a newly created
        # native destination or an asset changed while patching.
        for name, raw in original.items():
            if safe_path(root, name).read_bytes() != raw:
                raise ValueError('source_changed_during_staging: ' + name)
        for name, expected in additions.items():
            safe_path(root, name, exists=False)
            if safe_path(assets_root, expected['source']).read_bytes() != assets[name]:
                raise ValueError('asset_changed_during_staging: ' + name)
        backup = stage / '.rollback'
        backup.mkdir()
        for index, name in enumerate(files):
            (backup / str(index)).write_bytes(original[name])
        installed = []
        try:
            for index, name in enumerate([*files, *additions]):
                destination = sources.get(name, destinations.get(name))
                os.replace(stage / name, destination)
                installed.append((index, name, destination))
        except OSError:
            for index, name, destination in reversed(installed):
                if name in original:
                    os.replace(backup / str(index), destination)
                else:
                    destination.unlink()
            raise
    return {name: expected['patched_sha256'] for name, expected in files.items()} | {
        name: expected['sha256'] for name, expected in additions.items()}


def seal(root):
    """Developer command: pin patch outputs and every added production source.

    Input must be the fixed upstream commit with exactly the NG-G1 source bytes
    in the three NG-G1 files. This command is never run by build CI.
    """
    root = Path(root).absolute()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if commit != UPSTREAM_COMMIT:
        raise ValueError('upstream_commit_mismatch')
    ngg1 = json.loads((HERE / 'source-manifest.json').read_text())['files']
    raw_patch = PATCH_PATH.read_bytes()
    files = {}
    with tempfile.TemporaryDirectory(prefix='ngg2-seal-') as temporary:
        stage = Path(temporary)
        for name in headers(raw_patch):
            raw = safe_path(root, name).read_bytes()
            expected = (ngg1[name]['patched_sha256'] if name in ngg1 else
                digest(subprocess.check_output(['git', 'show', UPSTREAM_COMMIT + ':' + name], cwd=root)))
            if digest(raw) != expected:
                raise ValueError('seal_baseline_mismatch: ' + name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            files[name] = {'sha256': digest(raw), 'blob': git_blob(raw)}
        run_patch(stage, raw_patch)
        for name in files:
            files[name]['patched_sha256'] = digest((stage / name).read_bytes())
    additions = {}
    for source in sorted(ASSETS_ROOT.iterdir()):
        if source.name.startswith('NG2') and source.suffix in ('.swift', '.c', '.h', '.m'):
            raw = safe_path(ASSETS_ROOT, source.name).read_bytes()
            directory = ('Tests/LoopCtrlKitTests/' if source.name == 'NG2RPCContractsTests.swift'
                         else 'LoopCtrlUITests/')
            additions[directory + source.name] = {'source': source.name, 'sha256': digest(raw)}
    if not additions:
        raise ValueError('no_native_sources')
    manifest = {'format_version': 1, 'upstream_commit': UPSTREAM_COMMIT,
        'api_version': '1.98.14-ngg2', 'capability': 'necrogold_native_v1',
        'client_capability': 'necrogold_native_v5',
        'patch_sha256': digest(raw_patch), 'files': files, 'additions': additions}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true', help='pin reviewed sources; developer use only')
    parser.add_argument('upstream', type=Path)
    args = parser.parse_args()
    if args.seal:
        print(json.dumps(seal(args.upstream), indent=2))
    else:
        print(json.dumps({'api_version': '1.98.14-ngg2', 'files': apply(args.upstream)}, indent=2))


if __name__ == '__main__':
    main()
