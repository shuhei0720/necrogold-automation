"""TEST-018: 原寸格子の中央値・分散判定をiSHのnative演算へ渡す。

寸法・hash・自己検証が不一致なら既存Pillow経路を使う。画像の変形なし。
"""
import ctypes as C
import hashlib
from pathlib import Path
import sys

_RGB_LENGTH=896*414*3
_OUTPUT_LENGTH=230*4
_EXPECTED_SHA256='fb88fcc4be55b5a6b674e996452ad6d26e9a71ef313613e29ac208be67fa2a4a'


def _invoke(native,rgb):
    out=(C.c_ubyte*_OUTPUT_LENGTH)()
    if native.necro_navigation_stats(rgb,len(rgb),out,_OUTPUT_LENGTH)!=0:return None
    result=bytes(out)
    if any(v>1 for v in result[3::4]):return None
    return result


def _load():
    if sys.platform!='linux' or C.sizeof(C.c_void_p)!=4:return None
    try:
        path=Path(__file__).with_name('navigation_stats_i386.so')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=_EXPECTED_SHA256:return None
        native=C.CDLL(str(path))
        native.necro_navigation_stats.argtypes=[C.c_char_p,C.c_uint32,C.POINTER(C.c_ubyte),C.c_uint32]
        native.necro_navigation_stats.restype=C.c_int
        # One image covers flat bright cells and a nonuniform first cell whose
        # median is20 and population stddev is exactly2 in the red channel.
        raw=bytearray(bytes((200,210,220))*(896*414))
        values=[18]*310+[22]*310+[17,23,19,21,20]
        for n,value in enumerate(values):raw[((15+n//25)*896+40+n%25)*3]=value
        expected=bytes((20,210,220,1))+bytes((200,210,220,0))*229
        if _invoke(native,bytes(raw))!=expected:return None
        return native
    except (OSError,AttributeError,TypeError,ValueError,C.ArgumentError):return None


_native=_load()
ENGINE='native_i386' if _native is not None else 'pillow'


def scan(rgb):
    """固定RGB bytesから230セル×4byte、またはfallbackのNoneを返す。"""
    global _native,ENGINE
    if type(rgb) is not bytes or len(rgb)!=_RGB_LENGTH or _native is None:return None
    try:
        result=_invoke(_native,rgb)
        if result is not None:return result
    except (OSError,AttributeError,TypeError,ValueError,C.ArgumentError):pass
    _native,ENGINE=None,'pillow'
    return None
