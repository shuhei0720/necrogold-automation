"""既存ペアリングを使う計測通信。タップを送るAPIは提供しない。"""
import base64
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import http.client
import json
from pathlib import Path
import secrets
import signal
import time

from .crypto import Crypto, mac
from .validation import MAX_HTTP, MAX_PLAIN, ProbeError, b64, json_object, number

GAME = "jp.co.spike-chunsoft.necrodancerjp"
HOST = "127.0.0.1:8300"


@contextmanager
def deadline(seconds):
    number(seconds, 0.001, 60)
    if not hasattr(signal, "setitimer"):
        raise ProbeError("posix_timer_required")
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    if old_timer != (0.0, 0.0):
        raise ProbeError("timer_already_in_use")
    def expired(_signal, _frame):
        raise ProbeError("rpc_deadline")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


class HttpTransport:
    def __init__(self, port=8300):
        self.port = int(number(port, 1, 65535))

    def __call__(self, body, timeout):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            conn.request("POST", "/rpc", body=body, headers={"Content-Type": "application/json", "Connection": "close"})
            response = conn.getresponse()
            if response.status != 200:
                raise ProbeError("http_status_" + str(response.status))
            length = response.getheader("Content-Length")
            if length is not None and (not length.isdigit() or int(length) > MAX_HTTP):
                raise ProbeError("http_body_limit")
            chunks = bytearray()
            while True:
                part = response.read1(min(65536, MAX_HTTP + 1 - len(chunks)))
                if not part:
                    break
                chunks.extend(part)
                if len(chunks) > MAX_HTTP:
                    raise ProbeError("http_body_limit")
            if length is not None and len(chunks) != int(length):
                raise ProbeError("http_body_truncated")
            return bytes(chunks)
        except ProbeError:
            raise
        except (OSError, http.client.HTTPException, ValueError):
            raise ProbeError("connection_error") from None
        finally:
            conn.close()


def select_record(store, store_key=None):
    candidates = []
    if store_key is not None:
        candidates = [store.get(store_key)]
    else:
        for name, record in store.items():
            if not isinstance(record, dict):
                continue
            addresses = record.get("addresses", record.get("hosts", []))
            if not isinstance(addresses, list):
                addresses = []
            if name == HOST or any(address in (HOST, "@" + HOST) for address in addresses):
                candidates.append(record)
    valid = {}
    for record in candidates:
        try:
            if not isinstance(record, dict) or not isinstance(record.get("key"), str) or len(record["key"]) != 64:
                raise ValueError()
            key = bytes.fromhex(record["key"])
            if len(key) != 32:
                raise ValueError()
            tok = record.get("tok")
            if not isinstance(tok, str) or len(tok) != 8 or tok.lower() != hashlib.sha256(key).digest()[:4].hex():
                raise ValueError()
            valid[(key, tok.lower())] = (key, tok.lower())
        except (ValueError, TypeError):
            raise ProbeError("invalid_pairing_record") from None
    if len(valid) != 1:
        raise ProbeError("pairing_missing" if not valid else "pairing_ambiguous")
    return next(iter(valid.values()))


def load_pairing(path, store_key=None):
    try:
        with Path(path).open("rb") as file:
            raw = file.read(65537)
        store = json_object(raw, 65536)
    except OSError:
        raise ProbeError("pairing_missing") from None
    return select_record(store, store_key)


@dataclass
class RpcReply:
    result: dict
    timings: dict


class Client:
    def __init__(self, transport, key=None, tok=None, *, timeout=8, allow_launch=False, crypto=None):
        self.transport = transport
        self.key, self.tok = key, tok
        self.timeout = number(timeout, 0.1, 30)
        self.allow_launch = allow_launch
        self.crypto = crypto or Crypto()
        self.sequence = 0
        self.launched = False

    def _validate(self, method, params):
        if not isinstance(params, dict):
            raise ProbeError("invalid_params")
        if method == "device_info" and not params:
            return
        if method == "screenshot" and set(params) <= {"format", "scale", "quality"}:
            if params.get("format") not in ("jpeg", "png"):
                raise ProbeError("invalid_params")
            number(params.get("scale"), 1, 2)
            if "quality" in params:
                number(params["quality"], 0.1, 1)
            return
        if method == "launch_app" and self.allow_launch and not self.launched and params == {"bundle_id": GAME}:
            return
        raise ProbeError("method_not_allowed")

    def call(self, method, params=None, *, timeout=None):
        params = {} if params is None else params
        self._validate(method, params)
        if not isinstance(self.key, bytes) or len(self.key) != 32 or not isinstance(self.tok, str):
            raise ProbeError("pairing_missing")
        timeout = self.timeout if timeout is None else number(timeout, 0.001, self.timeout)
        if method == "launch_app":
            self.launched = True
        self.sequence += 1
        rpc_id = self.sequence
        times = {"request_start_ns": time.monotonic_ns(), "crypto_engine": self.crypto.engine}
        with deadline(timeout):
            nonce = secrets.token_bytes(16)
            ts = int(time.time())
            body = json.dumps({"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}, separators=(",", ":")).encode()
            k_mac = mac(self.key, b"loopctrl-v1|mac" + nonce)
            ct = self.crypto.xor(mac(self.key, b"loopctrl-v1|enc-req" + nonce), nonce, body)
            tag = mac(k_mac, b"v1" + bytes.fromhex(self.tok) + ts.to_bytes(8, "big") + nonce + ct)
            sealed = json.dumps({"v": 1, "tok": self.tok, "ts": ts, "nonce": nonce.hex(),
                                 "ct": base64.b64encode(ct).decode(), "tag": tag.hex()}).encode()
            times["http_start_ns"] = time.monotonic_ns()
            response = self.transport(sealed, timeout)
            times["http_end_ns"] = time.monotonic_ns()
            envelope = json_object(response, MAX_HTTP)
            cipher = b64(envelope.get("ct"), MAX_PLAIN)
            tag_text = envelope.get("tag")
            try:
                if not isinstance(tag_text, str) or len(tag_text) != 64:
                    raise ValueError()
                response_tag = bytes.fromhex(tag_text)
            except ValueError:
                raise ProbeError("invalid_response_tag") from None
            if not hmac.compare_digest(mac(k_mac, b"resp" + nonce + cipher), response_tag):
                raise ProbeError("response_mac_mismatch")
            times["decrypt_start_ns"] = time.monotonic_ns()
            plain = self.crypto.xor(mac(self.key, b"loopctrl-v1|enc-resp" + nonce), nonce, cipher)
            times["decrypt_end_ns"] = time.monotonic_ns()
            response = json_object(plain)
            if response.get("jsonrpc") != "2.0" or type(response.get("id")) is not int or response["id"] != rpc_id:
                raise ProbeError("response_id_mismatch")
            if "error" in response:
                raise ProbeError("rpc_error")
            if not isinstance(response.get("result"), dict):
                raise ProbeError("rpc_result_type")
            times["response_end_ns"] = time.monotonic_ns()
            times["request_bytes"] = len(sealed)
            times["encrypted_response_bytes"] = len(cipher)
            return RpcReply(response["result"], times)
