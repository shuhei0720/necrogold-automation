"""固定元3ファイルを全検証してからNG-G1を適用する。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PATCH_PATH = HERE / 'ngg1.patch'
SOURCE_MANIFEST = json.loads((HERE / 'source-manifest.json').read_text())['files']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def safe_source(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('unsafe_manifest_path')
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError('symlink_source: ' + name)
    if not candidate.is_file():
        raise ValueError('missing_source: ' + name)
    return candidate


def apply_patch(root, manifest=None, patch_path=PATCH_PATH):
    """Validation failures write no source bytes; replacement errors roll back.

    Per-file os.replace is atomic. This is not a crash-proof multi-file filesystem
    transaction: abrupt process termination/power loss during installation is out
    of scope. The CI always starts with a disposable, clean checkout.
    """
    manifest = SOURCE_MANIFEST if manifest is None else manifest
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('invalid_source_root')
    patch_bytes = Path(patch_path).read_bytes()
    headers = [line for line in patch_bytes.decode('utf-8').splitlines()
               if line.startswith(('--- ', '+++ '))]
    expected_headers = []
    for name in manifest:
        expected_headers.extend(['--- a/' + name, '+++ b/' + name])
    if headers != expected_headers:
        raise ValueError('patch_target_mismatch')

    sources, original = {}, {}
    for name, expected in manifest.items():
        path = safe_source(root, name)
        raw = path.read_bytes()
        if digest(raw) != expected['sha256'] or git_blob(raw) != expected['blob']:
            raise ValueError('source_hash_mismatch: ' + name)
        sources[name], original[name] = path, raw

    with tempfile.TemporaryDirectory(prefix='.ngg1-stage-', dir=root) as temporary:
        stage = Path(temporary)
        for name, path in sources.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        # git apply runs against the isolated copy only, never the source tree.
        for options in (['--check'], []):
            result = subprocess.run(['git', 'apply', '--no-index', *options, '-'],
                input=patch_bytes, cwd=stage, capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError('patch_rejected: ' + result.stderr.decode('utf-8', errors='replace').strip())
        if {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()} != set(manifest):
            raise ValueError('unexpected_staged_files')
        for name, expected in manifest.items():
            if digest((stage / name).read_bytes()) != expected['patched_sha256']:
                raise ValueError('patched_hash_mismatch: ' + name)
        # Recheck before installation so a concurrent source edit is not lost.
        for name in manifest:
            if safe_source(root, name).read_bytes() != original[name]:
                raise ValueError('source_changed_during_staging: ' + name)
        backups = stage / '.rollback'
        backups.mkdir()
        for index, name in enumerate(manifest):
            shutil.copy2(sources[name], backups / str(index))
        installed = []
        try:
            for index, name in enumerate(manifest):
                os.replace(stage / name, sources[name])
                installed.append((index, name))
        except OSError:
            for index, name in reversed(installed):
                os.replace(backups / str(index), sources[name])
            raise
    return {name: expected['patched_sha256'] for name, expected in manifest.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    args = parser.parse_args()
    hashes = apply_patch(args.upstream)
    print(json.dumps({'patch_sha256': digest(PATCH_PATH.read_bytes()), 'patched_files': hashes}, indent=2))


if __name__ == '__main__':
    main()
