"""Optional native PRF loop; OpenSSL owns HMAC and the official client verifies MACs."""
import ctypes as C
import hashlib
import hmac
from pathlib import Path
import shutil
import tempfile
import time
import diagnostics

SECONDS = 0.0
BYTES = 0
AVAILABLE = False
_native = _crypto = _api = _digest = None


def _native_xor(key, nonce, data):
    if len(key) > 2147483647 or len(data) > 32 * 4294967296:
        raise ValueError("PRF input too long")
    output = C.create_string_buffer(len(data))
    ok = _native.prf_xor(_api, _digest, key, len(key), nonce, len(nonce), data, output, len(data))
    if ok != 1:
        raise RuntimeError("OpenSSL HMAC failed")
    return output.raw


def _load():
    global _native, _crypto, _api, _digest
    for name in ("libcrypto.so.1.1", "libcrypto.so.3", "libcrypto.so"):
        try:
            _crypto = C.CDLL(name)
            names = ("HMAC_CTX_new", "HMAC_CTX_free", "HMAC_Init_ex",
                     "HMAC_Update", "HMAC_Final", "HMAC_CTX_copy")
            addresses = [C.cast(getattr(_crypto, name), C.c_void_p).value for name in names]
            break
        except (OSError, AttributeError):
            _crypto = None
    if _crypto is None:
        return False
    _api = (C.c_void_p * 6)(*addresses)
    _crypto.EVP_sha256.argtypes = []
    _crypto.EVP_sha256.restype = C.c_void_p
    _digest = _crypto.EVP_sha256()
    with tempfile.TemporaryDirectory() as folder:
        library = Path(folder) / "fast_crypto.so"
        shutil.copyfile(Path(__file__).with_name("fast_crypto_i386.so"), library)
        _native = C.CDLL(str(library))
    _native.prf_xor.argtypes = [C.c_void_p, C.c_void_p, C.c_char_p, C.c_int,
                              C.c_char_p, C.c_size_t, C.c_char_p, C.c_void_p, C.c_size_t]
    _native.prf_xor.restype = C.c_int
    # Independent known input, including a partial final block. A bad build
    # never changes encryption on the wire: fail back before any RPC.
    key, nonce, data = bytes(range(32)), bytes(range(16)), bytes(range(65))
    stream = b"".join(hmac.new(key, nonce+i.to_bytes(4,"big"), hashlib.sha256).digest()
                      for i in range(3))
    return _native_xor(key, nonce, data) == bytes(a ^ b for a,b in zip(data,stream))


try:
    AVAILABLE = _load()
except (OSError, AttributeError, RuntimeError, ValueError):
    AVAILABLE = False


def xor(key, nonce, data):
    global SECONDS, BYTES
    if not AVAILABLE:
        return None
    started = time.perf_counter()
    try:
        with diagnostics.stage("通信の暗号処理"):
            return _native_xor(key, nonce, data)
    finally:
        SECONDS += time.perf_counter() - started
        BYTES += len(data)
