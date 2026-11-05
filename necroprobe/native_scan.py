"""TEST-015の任意native検出。利用不可なら同じPillow判定に戻せる。"""
import ctypes as C
import hashlib
from pathlib import Path
import sys

_RGB_LENGTH = 896 * 414 * 3
_OUTPUT_LENGTH = 49
_EXPECTED_SHA256 = "c48eb11cc16ab72f2144f53c08b902e68b8b1452dacae96059ca085b8a3b73dc"


def _invoke(native, rgb):
    output = (C.c_ubyte * _OUTPUT_LENGTH)()
    if native.necro_gold_scan(rgb, len(rgb), output, _OUTPUT_LENGTH) != 0:
        return None
    return output[0], list(output[1:])


def _load():
    if sys.platform != "linux" or C.sizeof(C.c_void_p) != 4:
        return None
    try:
        path = Path(__file__).with_name("gold_scan_i386.so")
        if hashlib.sha256(path.read_bytes()).hexdigest() != _EXPECTED_SHA256:
            return None
        native = C.CDLL(str(path))
        native.necro_gold_scan.argtypes = [C.c_char_p, C.c_uint32, C.POINTER(C.c_ubyte), C.c_uint32]
        native.necro_gold_scan.restype = C.c_int
        if _invoke(native, bytes(_RGB_LENGTH)) != (0, [0] * 48):
            return None
        expected = [0 if 2 <= col <= 5 and 2 <= row <= 4 else 166
                    for row in range(6) for col in range(8)]
        if _invoke(native, bytes((210, 170, 30)) * (896 * 414)) != (255, expected):
            return None
        return native
    except (OSError, AttributeError, TypeError, ValueError, C.ArgumentError):
        return None


_native = _load()
ENGINE = "native_i386" if _native is not None else "pillow"


def scan(rgb):
    """原寸RGB bytesを検査し、(peak, fingerprint)かfallback用Noneを返す。"""
    global _native, ENGINE
    if type(rgb) is not bytes or len(rgb) != _RGB_LENGTH or _native is None:
        return None
    try:
        result = _invoke(_native, rgb)
        if result is not None:
            return result
    except (OSError, AttributeError, TypeError, ValueError, C.ArgumentError):
        pass
    _native, ENGINE = None, "pillow"
    return None
