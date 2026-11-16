"""Create a public, complete source ZIP from the independently verified map."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile


LINKS = {'upstream/server/cli/loopctrl_rpc.py': 'upstream/Scripts/loopctrl_rpc.py'}
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


def _parts(name):
    if (type(name) is not str or '\\' in name or '\0' in name or ':' in name
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('unsafe_source_name')
    parts = name.split('/')
    if len(parts) < 2 or parts[0] not in ('driver', 'upstream'):
        raise ValueError('unsafe_source_prefix')
    return parts


def _source(roots, name, *, link=False):
    parts = _parts(name)
    path = roots[parts[0]]
    for index, part in enumerate(parts[1:]):
        path = path / part
        mode = path.lstat().st_mode
        leaf = index == len(parts) - 2
        if stat.S_ISLNK(mode):
            if not (leaf and link):
                raise ValueError('source_symlink')
        elif not (stat.S_ISREG(mode) if leaf else stat.S_ISDIR(mode)):
            raise ValueError('source_not_regular')
    return path


def package(upstream, driver, output, report):
    roots = {'upstream': Path(upstream).resolve(strict=True), 'driver': Path(driver).resolve(strict=True)}
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('source_archive_exists')
    inventory = report.get('complete_source_sha256')
    links = report.get('complete_source_materialized_links', {})
    if (type(inventory) is not dict or not 1 <= len(inventory) <= 20000
            or type(links) is not dict or (links and links != LINKS)
            or not set(links).issubset(inventory)):
        raise ValueError('invalid_source_inventory')
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.ng8-source-', suffix='.zip', dir=output.parent)
    os.close(handle)
    total = 0
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, expected in sorted(inventory.items()):
                if type(expected) is not str or re.fullmatch('[0-9a-f]{64}', expected) is None:
                    raise ValueError('invalid_source_hash')
                source = _source(roots, name, link=name in links)
                if name in links:
                    if not source.is_symlink() or os.readlink(source) != '../../Scripts/loopctrl_rpc.py':
                        raise ValueError('fixed_source_link_changed')
                    source = _source(roots, links[name])
                flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
                descriptor = os.open(source, flags)
                with os.fdopen(descriptor, 'rb') as stream:
                    metadata = os.fstat(stream.fileno())
                    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_FILE_BYTES:
                        raise ValueError('source_file_limit')
                    raw = stream.read(MAX_FILE_BYTES + 1)
                total += len(raw)
                if len(raw) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                    raise ValueError('source_archive_limit')
                if hashlib.sha256(raw).hexdigest() != expected:
                    raise ValueError('source_content_changed')
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                mode = 0o755 if metadata.st_mode & 0o111 else 0o644
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, raw)
        # Publish without ever replacing an existing output, including a raced
        # destination. The temporary is on the same filesystem.
        os.link(temporary, output)
    finally:
        os.unlink(temporary)
    return len(inventory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('driver', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = json.loads((args.upstream / 'release/iphone8-probe-build-manifest.json').read_text())
    count = package(args.upstream, args.driver, args.output, report)
    print(json.dumps({'complete_source_files': count, 'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
