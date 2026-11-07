"""既存ペアリングを使う計測通信。タップを送るAPIは提供しない。"""
import base64
from dataclasses import dataclass
import errno
import hashlib
import hmac
import http.client
import json
from pathlib import Path
import secrets
import time

from .crypto import Crypto, mac
from .deadlines import OwnedRpcTimer
from .rpc_diagnostics import remote_error
from .validation import MAX_HTTP, MAX_PLAIN, ProbeError, b64, json_object, number

GAME = "jp.co.spike-chunsoft.necrodancerjp"
HOST = "127.0.0.1:8300"
SCHEMA_LIMIT = 512 * 1024




class HttpTransport:
    def __init__(self, port=8300):
        self.port = int(number(port, 1, 65535))
        self.last_diagnostic = {}

    def schema(self, timeout):
        """Read fixed, public readiness metadata; never send pairing material."""
        number(timeout, .001, 30)
        return self._exchange("GET", "/schema", None, timeout, SCHEMA_LIMIT)

    def __call__(self, body, timeout):
        return self._exchange("POST", "/rpc", body, timeout, MAX_HTTP)

    @staticmethod
    def _error_kind(exc):
        if isinstance(exc, TimeoutError):
            return "timeout"
        code = getattr(exc, "errno", None)
        if code == errno.ECONNREFUSED:
            return "refused"
        if code in (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE):
            return "reset"
        if code in (errno.EHOSTUNREACH, errno.ENETUNREACH):
            return "unreachable"
        if isinstance(exc, http.client.RemoteDisconnected):
            return "disconnected"
        if isinstance(exc, http.client.IncompleteRead):
            return "body_truncated"
        if isinstance(exc, (http.client.HTTPException, ValueError)):
            return "protocol_error"
        return "io_error"

    def _exchange(self, method, path, body, timeout, limit):
        diagnostic = {"stage": "connect", "kind": "io_error", "errno": None,
                      "status": None, "started_ns": time.monotonic_ns(), "ended_ns": 0}
        self.last_diagnostic = diagnostic
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        response = None
        try:
            conn.connect()
            diagnostic["stage"] = "request"
            headers = {"Connection": "close"}
            headers["Accept" if method == "GET" else "Content-Type"] = "application/json"
            conn.request(method, path, body=body, headers=headers)
            diagnostic["stage"] = "headers"
            response = conn.getresponse()
            diagnostic["status"] = response.status if 100 <= response.status <= 599 else None
            if response.status != 200:
                raise ProbeError("http_status_" + str(response.status))
            length = response.getheader("Content-Length")
            if length is not None and (not length.isdigit() or int(length) > limit):
                raise ProbeError("http_body_limit")
            diagnostic["stage"] = "body"
            chunks = bytearray()
            while True:
                part = response.read1(min(65536, limit + 1 - len(chunks)))
                if not part:
                    break
                chunks.extend(part)
                if len(chunks) > limit:
                    raise ProbeError("http_body_limit")
            if length is not None and len(chunks) != int(length):
                raise ProbeError("http_body_truncated")
            diagnostic.update(stage="complete", kind="ok")
            return bytes(chunks)
        except ProbeError as exc:
            diagnostic["kind"] = {"rpc_deadline": "deadline", "http_body_limit": "body_limit",
                                  "http_body_truncated": "body_truncated"}.get(
                                      exc.code, "http_status" if exc.code.startswith("http_status_")
                                      else "protocol_error")
            raise
        except (OSError, http.client.HTTPException, ValueError) as exc:
            diagnostic["kind"] = self._error_kind(exc)
            code = getattr(exc, "errno", None)
            diagnostic["errno"] = code if type(code) is int and 0 <= code <= 4095 else None
            raise ProbeError("connection_error") from None
        finally:
            diagnostic["ended_ns"] = time.monotonic_ns()
            try:
                if response is not None:
                    response.close()
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
    def __init__(self, transport, key=None, tok=None, *, timeout=8, allow_launch=False, crypto=None, deadline_owner=None,
                 source_geometry=False):
        self.transport = transport
        self.deadline_owner = deadline_owner
        self.key, self.tok = key, tok
        self.timeout = number(timeout, 0.1, 30)
        self.allow_launch = allow_launch
        self.source_geometry = source_geometry
        self.crypto = crypto or Crypto()
        self.sequence = 0
        self.launched = False

    def _validate(self, method, params):
        if not isinstance(params, dict):
            raise ProbeError("invalid_params")
        if method == "device_info" and not params:
            return
        if method == "screenshot" and set(params) <= {"format", "scale", "quality", "geometry"}:
            if "geometry" in params and params["geometry"] != "image_size_v1":
                raise ProbeError("invalid_params")
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
        if not isinstance(self.deadline_owner, OwnedRpcTimer):
            raise ProbeError("timer_owner_required")
        with self.deadline_owner.deadline(timeout):
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
                raise remote_error(response, method, params) from None
            if not isinstance(response.get("result"), dict):
                raise ProbeError("rpc_result_type")
            times["response_end_ns"] = time.monotonic_ns()
            times["request_bytes"] = len(sealed)
            times["encrypted_response_bytes"] = len(cipher)
            return RpcReply(response["result"], times)
