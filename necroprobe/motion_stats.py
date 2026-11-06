"""TEST-020: exact motion statistics in a separate, hash-pinned i386 library.

Return None for the entire comparison when unavailable; the caller retains the
old Pillow path. Python keeps Pillow's variance, sqrt and gain calculations;
the native helper generates identical byte LUTs with ties-to-even rounding.
"""
import ctypes as C
import hashlib
import math
from pathlib import Path
import sys

_SIGNATURE_LENGTH = 224 * 104
_CANDIDATES = ((0, 0),) + tuple(
    (amount * dx, amount * dy) for amount in range(1, 19)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
_STATS_LENGTH = 73 * 5 * 4
_LUT_LENGTH = 73 * 256
_GAIN_LENGTH = 73 * 8
_DIFF_LENGTH = 73 * 4
_EXPECTED_SHA256 = 'ec67f829ac85f6ba81f0bf9562449c09c327ae567e3bbe7af35d5d109a00a44a'
# Independently generated with the original Pillow crops, mask and statistics.
_SELFCHECK_SHA256 = '46ff7e2259267792cb673f6d0fec06f606bb1f5ec79a11b454399fc0d8d1256d'
_LUT_SELFCHECK_SHA256 = '76671780e7b9a6dcfac2533dbbd367bb42ef4ce50ccd55de389eebba9b462026'


def _selfcheck_gains():
    gains = [0.0 if k % 13 == 0 else .65 + .9 * ((17 * k) % 73) / 72 for k in range(73)]
    gains[:9] = [0.0, .65, 1.55, 1.5, 1.25, math.nextafter(1.5, -math.inf),
                 math.nextafter(1.5, math.inf), math.nextafter(.65, math.inf),
                 math.nextafter(1.55, -math.inf)]
    return gains


def _statistics(native, before, after):
    out = (C.c_uint32 * (73 * 5))()
    if native.necro_motion_stats(before, len(before), after, len(after), out, _STATS_LENGTH) != 0:
        return None
    return out


def _differences(native, before, after, luts):
    out = (C.c_uint32 * 73)()
    if native.necro_motion_diffs(before, len(before), after, len(after), luts, len(luts), out, _DIFF_LENGTH) != 0:
        return None
    return out


def _luts(native, gains):
    inputs = (C.c_double * 73)(*gains)
    out = (C.c_ubyte * _LUT_LENGTH)()
    if native.necro_motion_luts(inputs, _GAIN_LENGTH, out, _LUT_LENGTH) != 0:
        return None
    return bytes(out)


def _load():
    if sys.platform != 'linux' or C.sizeof(C.c_void_p) != 4:
        return None
    try:
        path = Path(__file__).with_name('motion_stats_i386.so')
        if hashlib.sha256(path.read_bytes()).hexdigest() != _EXPECTED_SHA256:
            return None
        native = C.CDLL(str(path))
        args = [C.c_char_p, C.c_uint32, C.c_char_p, C.c_uint32]
        output = [C.POINTER(C.c_uint32), C.c_uint32]
        native.necro_motion_stats.argtypes = args + output
        native.necro_motion_stats.restype = C.c_int
        native.necro_motion_diffs.argtypes = args + [C.c_char_p, C.c_uint32] + output
        native.necro_motion_diffs.restype = C.c_int
        native.necro_motion_luts.argtypes = [C.POINTER(C.c_double), C.c_uint32,
                                             C.POINTER(C.c_ubyte), C.c_uint32]
        native.necro_motion_luts.restype = C.c_int
        before = bytes((i * 37 + i // 224 * 11) % 256 for i in range(_SIGNATURE_LENGTH))
        after = bytes((i * 17 + i // 224 * 29 + 5) % 256 for i in range(_SIGNATURE_LENGTH))
        luts = bytes((v * 3 + k) % 256 for k in range(73) for v in range(256))
        stats = _statistics(native, before, after)
        diffs = _differences(native, before, after, luts)
        if stats is None or diffs is None:
            return None
        if hashlib.sha256(bytes(stats) + bytes(diffs)).hexdigest() != _SELFCHECK_SHA256:
            return None
        checked_luts = _luts(native, _selfcheck_gains())
        if checked_luts is None or hashlib.sha256(checked_luts).hexdigest() != _LUT_SELFCHECK_SHA256:
            return None
        return native
    except (OSError, AttributeError, TypeError, ValueError, C.ArgumentError):
        return None


_native = _load()
ENGINE = 'native_i386' if _native is not None else 'pillow'


def _invoke(native, before, after):
    stats = _statistics(native, before, after)
    if stats is None:
        return None
    contrasts = []
    gains = [0.0] * 73
    for k in range(73):
        count, sum_a, sum_b, square_a, square_b = stats[5 * k:5 * k + 5]
        if count < 300:
            contrasts.append(None)
            continue
        # Preserve ImageStat's operation order rather than E[x*x]-E[x]**2.
        contrast = (math.sqrt((square_a - sum_a ** 2 / count) / count) +
                    math.sqrt((square_b - sum_b ** 2 / count) / count)) / 2
        mean_a, mean_b = sum_a / count, sum_b / count
        if contrast < 2.5 or min(mean_a, mean_b) < 6:
            contrasts.append(None)
            continue
        contrasts.append(contrast)
        gains[k] = max(.65, min(1.55, mean_a / mean_b))
    luts = _luts(native, gains)
    if luts is None:
        return None
    diffs = _differences(native, before, after, luts)
    if diffs is None:
        return None
    return [(float('inf') if contrast is None else diffs[k] / stats[5 * k] / contrast, sx, sy)
            for k, ((sx, sy), contrast) in enumerate(zip(_CANDIDATES, contrasts))]


def scores(before_signature, after_signature):
    """Return 73 (score, sx, sy) tuples in original order, or None for fallback."""
    global _native, ENGINE
    if (type(before_signature) is not bytes or type(after_signature) is not bytes or
            len(before_signature) != _SIGNATURE_LENGTH or len(after_signature) != _SIGNATURE_LENGTH or
            _native is None):
        return None
    try:
        result = _invoke(_native, before_signature, after_signature)
        if result is not None:
            return result
    except (OSError, AttributeError, TypeError, ValueError, ZeroDivisionError, C.ArgumentError):
        pass
    _native, ENGINE = None, 'pillow'
    return None
