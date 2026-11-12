"""Local bounded protocol bridge for the pinned TEST089 i386 ring engine."""
import errno
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import selectors
import stat
import struct
import subprocess
import sys
import time
import uuid

from .native_walk import ProbeError, json_object

_ROOT = Path(__file__).parent
_TIMEOUT = 30.0
_PROTOCOL = 'ngg2-ring-raw-v1'
_RAW_BYTES = 1484190


class NativeRingError(OSError):
    pass


def _require(condition, code):
    if not condition:
        raise NativeRingError(code)


def _check(cancelled):
    _require(not cancelled(), 'ring_native_cancelled')


def _safe(path):
    _require(not any(p.is_symlink() for p in (path, *path.parents)), 'ring_native_symlink')


def _read(path, limit):
    _safe(path)
    descriptor = os.open(str(path), os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as handle:
        info = os.fstat(handle.fileno())
        _require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'ring_native_integrity')
        raw = handle.read(limit+1)
    _require(len(raw) <= limit, 'ring_native_integrity')
    return raw


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _keys(value, expected):
    _require(type(value) is dict and set(value) == set(expected), 'ring_native_schema')


def _elf(raw):
    _require(len(raw) >= 84 and raw[:7] == b'\x7fELF\x01\x01\x01', 'ring_native_elf')
    kind, machine, version, _entry, offset, _shoff, _flags, size, stride, count = struct.unpack_from('<HHIIIIIHHH', raw, 16)
    _require((kind, machine, version, size, stride) == (2, 3, 1, 52, 32)
        and offset >= 52 and 0 < count <= 128 and offset+stride*count <= len(raw), 'ring_native_elf')
    loads = 0
    for at in range(offset, offset+stride*count, stride):
        entry = struct.unpack_from('<IIIIIIII', raw, at)
        _require(entry[0] not in (2, 3) and entry[1]+entry[4] <= len(raw), 'ring_native_elf')
        if entry[0] == 1:
            loads += 1
            _require(entry[5] >= entry[4], 'ring_native_elf')
    _require(loads > 0, 'ring_native_elf')


def _sync(path):
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        try:
            os.fsync(descriptor)
        except OSError as error:
            if error.errno not in (errno.EINVAL, errno.ENOTSUP, errno.ENOSYS):
                raise
    finally:
        os.close(descriptor)


def _engine(feature_sha256, cancelled):
    manifest = json_object(_read(_ROOT/'ring_native_manifest.json', 64*1024), 64*1024)
    _keys(manifest, ('schema', 'protocol', 'binary', 'binary_bytes', 'binary_sha256', 'features_sha256', 'sources', 'toolchain'))
    _require(manifest['schema'] == 'ngg2-ring-engine-v1' and manifest['protocol'] == _PROTOCOL
        and manifest['binary'] == 'ring-i386' and type(manifest['binary_bytes']) is int
        and 84 <= manifest['binary_bytes'] <= 16*1024*1024 and _sha(manifest['binary_sha256'])
        and manifest['features_sha256'] == feature_sha256, 'ring_native_manifest')
    _keys(manifest['toolchain'], ('name', 'version', 'target', 'cpu', 'flags', 'libc', 'source_date_epoch'))
    _require(all(type(v) is str and 0 < len(v) <= 4096 for v in manifest['toolchain'].values()), 'ring_native_manifest')
    pinned = dict(name='zig', version='0.15.2', target='x86-linux-musl', cpu='i386',
                  libc='musl-bundled-with-zig-0.15.2', source_date_epoch='0')
    _require(all(manifest['toolchain'][key] == value for key, value in pinned.items()), 'ring_native_manifest')
    sources = manifest['sources']
    _require(type(sources) is dict and 0 < len(sources) <= 32, 'ring_native_manifest')
    for name, digest in sources.items():
        _check(cancelled)
        _require(type(name) is str and name and '\\' not in name and ':' not in name
            and not name.startswith('/') and '/'.join(PurePosixPath(name).parts) == name
            and all(not part.startswith('.') for part in PurePosixPath(name).parts) and _sha(digest), 'ring_native_manifest')
        _require(hashlib.sha256(_read(_ROOT.parent/name, 2*1024*1024)).hexdigest() == digest, 'ring_native_integrity')
    _require(hashlib.sha256(_read(_ROOT/'target_ring_features.json', 64*1024)).hexdigest() == feature_sha256, 'ring_native_integrity')
    raw = _read(_ROOT/'bin/ring-i386', 16*1024*1024)
    signature = manifest['binary_sha256']
    _require((len(raw), hashlib.sha256(raw).hexdigest()) == (manifest['binary_bytes'], signature), 'ring_native_integrity')
    _elf(raw)
    directory = Path.home()/'.necroprobe/engines'
    _safe(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require(directory.is_dir() and directory.stat().st_mode & 0o077 == 0, 'ring_native_cache')
    final = directory/('ring-'+signature)
    _safe(final)
    if not final.exists():
        temporary = directory/('.install-'+uuid.uuid4().hex)
        try:
            descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
            with os.fdopen(descriptor, 'wb') as handle:
                for offset in range(0, len(raw), 64*1024):
                    _check(cancelled)
                    handle.write(raw[offset:offset+64*1024])
                handle.flush()
                os.fsync(handle.fileno())
            _require(hashlib.sha256(_read(temporary, len(raw))).hexdigest() == signature, 'ring_native_cache')
            _check(cancelled)
            try:
                os.link(str(temporary), str(final))
            except FileExistsError:
                pass
            _sync(directory)
        finally:
            if temporary.exists():
                temporary.unlink()
    _require(final.stat().st_mode & 0o777 == 0o700 and _read(final, len(raw)) == raw, 'ring_native_cache')
    return final.absolute()


def _popen(argv, **kwargs):
    return subprocess.Popen(argv, **kwargs)


def _exchange(engine, payload, cancelled):
    child = None
    selector = selectors.PollSelector()
    output = bytearray(); errors = bytearray(); offset = 0
    deadline = time.monotonic()+_TIMEOUT
    try:
        _check(cancelled)
        child = _popen([str(engine)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       shell=False, close_fds=True, env={}, cwd=str(engine.parent))
        for stream, event in ((child.stdin, selectors.EVENT_WRITE), (child.stdout, selectors.EVENT_READ),
                              (child.stderr, selectors.EVENT_READ)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, event)
        while selector.get_map() or child.poll() is None:
            _check(cancelled)
            remaining = deadline-time.monotonic()
            _require(remaining > 0, 'ring_native_timeout')
            for key, _event in selector.select(min(.05, remaining)):
                stream = key.fileobj
                if stream is child.stdin:
                    try:
                        offset += os.write(stream.fileno(), payload[offset:offset+64*1024])
                    except BlockingIOError:
                        continue
                    if offset == len(payload):
                        selector.unregister(stream)
                        stream.close()
                else:
                    buffer, limit = (output, 8192) if stream is child.stdout else (errors, 2048)
                    try:
                        chunk = os.read(stream.fileno(), min(64*1024, limit-len(buffer)+1))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                    else:
                        _require(len(buffer)+len(chunk) <= limit, 'ring_native_output')
                        buffer.extend(chunk)
        _require(child.wait() == 0 and offset == len(payload), 'ring_native_child')
        _check(cancelled)
        return bytes(output)
    finally:
        selector.close()
        if child is not None:
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream is not None:
                    stream.close()
            if child.poll() is None:
                try:
                    child.terminate()
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=.2)
                except subprocess.TimeoutExpired:
                    try:
                        child.kill()
                    except ProcessLookupError:
                        pass
                    child.wait()
            else:
                child.wait()


def _number(value, maximum):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum


def _box(value):
    return type(value) is list and len(value) == 4 and all(type(v) is int for v in value)


def _reply(raw, feature_sha256, input_sha256):
    reply = json_object(raw, 8192)
    _keys(reply, ('protocol', 'features_sha256', 'input_sha256', 'rows'))
    _require(reply['protocol'] == _PROTOCOL and reply['features_sha256'] == feature_sha256
        and reply['input_sha256'] == input_sha256 and type(reply['rows']) is list and len(reply['rows']) <= 4, 'ring_native_reply')
    seen = set()
    for row in reply['rows']:
        _keys(row, ('row', 'slots'))
        coordinates = row['row']
        _require(type(coordinates) is list and len(coordinates) == 2
            and all(type(v) is int for v in coordinates), 'ring_native_reply')
        left, sy = coordinates
        _require(18 <= left < 806 and 0 <= sy < 325 and tuple(coordinates) not in seen
            and type(row['slots']) is list and len(row['slots']) == 3, 'ring_native_reply')
        seen.add(tuple(coordinates))
        for index, slot in enumerate(row['slots']):
            _keys(slot, ('score', 'box', 'word'))
            _require(_number(slot['score'], 1.000001) and _box(slot['box']), 'ring_native_reply')
            x, y, width, height = slot['box']; cx = left+36*index
            _require((width, height) in ((32,28), (33,28), (34,29))
                and max(0, cx-width//2-8) <= x <= min(896-width, cx-width//2+8)
                and sy+24 <= y <= min(414-height, sy+57), 'ring_native_reply')
            word = slot['word']
            empty = max(0, cx-60) > min(812, cx-24) or max(0, sy-20) > min(403, sy+35)
            if empty:
                _require(word is None, 'ring_native_reply')
                continue
            _keys(word, ('iou', 'coverage', 'box'))
            _require(_number(word['iou'], 1) and _number(word['coverage'], 1) and _box(word['box']), 'ring_native_reply')
            x, y, width, height = word['box']
            _require((width, height) == (84,11) and max(0, cx-60) <= x <= min(812, cx-24)
                and max(0, sy-20) <= y <= min(403, sy+35), 'ring_native_reply')
    return reply['rows']


def classify_filtered(raw, feature_sha256, cancelled=lambda: False):
    try:
        _check(cancelled)
        _require(type(raw) is bytes and len(raw) == _RAW_BYTES and _sha(feature_sha256)
            and all(raw[y*3585] <= 4 for y in range(414)), 'ring_native_input')
        _require(sys.implementation.name == 'cpython' and (3,9) <= sys.version_info[:2] <= (3,12), 'ring_python_version')
        engine = _engine(feature_sha256, cancelled)
        digest = hashlib.sha256(raw).digest()
        header = b'NG2RING1'+struct.pack('<II', int(sys.version_info >= (3,12)), len(raw))
        header += bytes.fromhex(feature_sha256)+digest
        return _reply(_exchange(engine, header+raw, cancelled), feature_sha256, digest.hex())
    except NativeRingError:
        raise
    except (ProbeError, OSError, ValueError, TypeError, OverflowError, struct.error):
        raise NativeRingError('ring_native_failed') from None
