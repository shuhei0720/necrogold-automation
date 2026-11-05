"""LoopCtrl v1互換。既存i386ライブラリはハッシュと既知入力を検査。"""
import ctypes as C
import hashlib
import hmac
from pathlib import Path


def mac(key, data):
    return hmac.new(key, data, hashlib.sha256).digest()


def python_xor(key, nonce, data):
    base = hmac.new(key, digestmod=hashlib.sha256)
    output = bytearray()
    for offset in range(0, len(data), 32):
        block = base.copy()
        block.update(nonce + (offset // 32).to_bytes(4, "big"))
        output.extend(block.digest())
    size = len(data)
    return (int.from_bytes(data, "big") ^ int.from_bytes(output[:size], "big")).to_bytes(size, "big")


class Crypto:
    def __init__(self, native=True):
        self.engine = "python"
        self.native = self.openssl = self.api = self.digest = None
        if native:
            self._load_native()

    def _load_native(self):
        path = Path(__file__).resolve().parents[1] / "legacy/r12/fast_crypto_i386.so"
        try:
            if path.stat().st_size > 65536:
                return
            if hashlib.sha256(path.read_bytes()).hexdigest() != "cf049d2049c273974ff8d53819a7b7294de50775ba3570849e33261fcfd38b9d":
                return
            native = C.CDLL(str(path))
            openssl = None
            for name in ("libcrypto.so.1.1", "libcrypto.so.3", "libcrypto.so"):
                try:
                    openssl = C.CDLL(name)
                    names = ("HMAC_CTX_new", "HMAC_CTX_free", "HMAC_Init_ex", "HMAC_Update", "HMAC_Final", "HMAC_CTX_copy")
                    addresses = [C.cast(getattr(openssl, n), C.c_void_p).value for n in names]
                    break
                except (OSError, AttributeError):
                    openssl = None
            if openssl is None:
                return
            openssl.EVP_sha256.argtypes = []
            openssl.EVP_sha256.restype = C.c_void_p
            native.prf_xor.argtypes = [C.c_void_p, C.c_void_p, C.c_char_p, C.c_int,
                                      C.c_char_p, C.c_size_t, C.c_char_p, C.c_void_p, C.c_size_t]
            native.prf_xor.restype = C.c_int
            self.native, self.openssl = native, openssl
            self.api = (C.c_void_p * 6)(*addresses)
            self.digest = openssl.EVP_sha256()
            if not self.digest:
                return
            key, nonce, data = bytes(range(32)), bytes(range(16)), bytes(range(65))
            if self._native_xor(key, nonce, data) == python_xor(key, nonce, data):
                self.engine = "native_i386"
        except (OSError, AttributeError, ValueError, RuntimeError):
            self.engine = "python"

    def _native_xor(self, key, nonce, data):
        output = C.create_string_buffer(len(data))
        ok = self.native.prf_xor(self.api, self.digest, key, len(key), nonce, len(nonce), data, output, len(data))
        if ok != 1:
            raise RuntimeError("native_crypto_failed")
        return output.raw

    def xor(self, key, nonce, data):
        if self.engine == "native_i386" and data:
            return self._native_xor(key, nonce, data)
        return python_xor(key, nonce, data)
