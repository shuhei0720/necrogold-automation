import base64
import hashlib
import hmac
import json
import unittest
from unittest.mock import patch

from necroprobe.crypto import Crypto, mac, python_xor
from necroprobe.protocol import Client, GAME, select_record
from necroprobe.validation import ProbeError, b64, json_object, number
from timer_support import TimerTestCase

KEY = bytes(range(32))
TOK = hashlib.sha256(KEY).digest()[:4].hex()


def sealed_reply(body, *, result=None, response_id=None, corrupt_mac=False, rpc_error=False):
    envelope = json.loads(body)
    nonce = bytes.fromhex(envelope["nonce"])
    decoded = python_xor(mac(KEY, b"loopctrl-v1|enc-req" + nonce), nonce, base64.b64decode(envelope["ct"]))
    request = json.loads(decoded)
    response = {"jsonrpc": "2.0", "id": request["id"] if response_id is None else response_id}
    response["error" if rpc_error else "result"] = result if result is not None else {}
    cipher = python_xor(mac(KEY, b"loopctrl-v1|enc-resp" + nonce), nonce, json.dumps(response).encode())
    tag = mac(mac(KEY, b"loopctrl-v1|mac" + nonce), b"resp" + nonce + cipher).hex()
    return json.dumps({"ct": base64.b64encode(cipher).decode(), "tag": "00" * 32 if corrupt_mac else tag}).encode()


class ProtocolTests(TimerTestCase):
    def reply_client(self, **reply_args):
        return self.client(lambda body, timeout: sealed_reply(body, **reply_args), KEY, TOK, crypto=Crypto(native=False))
    def test_tap_is_rejected_before_any_network_call(self):
        for method in ("tap", "run_steps", "reset", "pair", "launch_app", "notify"):
            sent = []
            probe = self.client(lambda *args: sent.append(args), KEY, TOK, crypto=Crypto(native=False))
            with self.subTest(method=method), self.assertRaises(ProbeError) as caught:
                probe.call(method, {"x": 298, "y": 448})
            self.assertEqual("method_not_allowed", caught.exception.code)
            self.assertEqual([], sent)

    def test_authenticated_response_and_clock_boundaries(self):
        reply = self.reply_client(result={"ok": True}).call("device_info")
        self.assertEqual({"ok": True}, reply.result)
        keys = ("request_start_ns", "http_start_ns", "http_end_ns", "decrypt_start_ns", "decrypt_end_ns", "response_end_ns")
        self.assertEqual(sorted(reply.timings[key] for key in keys), [reply.timings[key] for key in keys])

    def test_bad_mac_wrong_id_and_error_are_rejected(self):
        for kwargs in ({"corrupt_mac": True}, {"response_id": 2}, {"response_id": True}, {"rpc_error": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ProbeError):
                self.reply_client(**kwargs).call("device_info")

    def test_rpc_error_does_not_expose_server_text(self):
        with self.assertRaises(ProbeError) as caught:
            self.reply_client(result={"message": "PRIVATE_SECRET"}, rpc_error=True).call("device_info")
        self.assertNotIn("PRIVATE_SECRET", str(caught.exception))

    def test_launch_is_exact_game_only_and_never_retried(self):
        calls = []
        def fail(body, timeout):
            calls.append(body)
            raise ProbeError("connection_error")
        probe = self.client(fail, KEY, TOK, allow_launch=True)
        with self.assertRaises(ProbeError):
            probe.call("launch_app", {"bundle_id": "other"})
        self.assertEqual([], calls)
        for _ in range(2):
            with self.assertRaises(ProbeError):
                probe.call("launch_app", {"bundle_id": GAME})
        self.assertEqual(1, len(calls))

    def test_screenshot_params_finite_and_bounded(self):
        for scale in (float("nan"), float("inf"), True, 0, 3):
            with self.subTest(scale=repr(scale)), self.assertRaises(ProbeError):
                self.reply_client().call("screenshot", {"format": "jpeg", "scale": scale})

    def test_pairing_only_unambiguous_existing_local_record(self):
        record = {"key": KEY.hex(), "tok": TOK, "addresses": ["@127.0.0.1:8300"]}
        self.assertEqual((KEY, TOK), select_record({"device:local": record}))
        otherkey = b"a" * 32
        other = {"key": otherkey.hex(), "tok": hashlib.sha256(otherkey).digest()[:4].hex()}
        with self.assertRaisesRegex(ProbeError, "pairing_ambiguous"):
            select_record({"device:local": record, "127.0.0.1:8300": other})
        with self.assertRaisesRegex(ProbeError, "pairing_missing"):
            select_record({"device:remote": other})
        self.assertEqual((KEY, TOK), select_record({"127.0.0.1:8300": record, "device:duplicate": record}))

    def test_json_depth_nodes_duplicates_nonfinite_and_bytes_limits(self):
        invalid = (b'{"x":NaN}', b'{"x":1e999}', b'{"x":1,"x":2}', b'[]', b'\xff',
                   b'{"a":' + b'[' * 16 + b'0' + b']' * 16 + b'}',
                   b'{"a":[' + b'0,' * 10000 + b'0]}')
        for raw in invalid:
            with self.subTest(size=len(raw)), self.assertRaises(ProbeError):
                json_object(raw)
        self.assertEqual({}, json_object(b'{}', 2))
        with self.assertRaisesRegex(ProbeError, "json_size"):
            json_object(b'{}', 1)
        allowed = b'{"a":' + b'[' * 15 + b'0' + b']' * 15 + b'}'
        self.assertIn("a", json_object(allowed))

    def test_brackets_and_escaped_quotes_in_json_string(self):
        expected = {"text": '["not nested]\\"' * 100}
        self.assertEqual(expected, json_object(json.dumps(expected).encode()))

    def test_base64_decoded_size_boundary(self):
        self.assertEqual(b'ab', b64('YWI=', 2))
        with self.assertRaises(ProbeError):
            b64('YWJj', 2)

    def test_crypto_matches_independent_hmac_counter_vector(self):
        nonce = bytes(range(16))
        for size in (0, 1, 31, 32, 33, 65, 1024):
            data = b'x' * size
            stream = b''.join(hmac.new(KEY, nonce + i.to_bytes(4, 'big'), hashlib.sha256).digest()
                              for i in range((size + 31) // 32))
            expected = bytes(a ^ b for a, b in zip(data, stream))
            self.assertEqual(expected, python_xor(KEY, nonce, data))
            self.assertEqual(data, python_xor(KEY, nonce, expected))

    def test_json_nodes_rejected_before_object_allocation(self):
        raw = b'{"x":[' + b'0,' * 20000 + b'0]}'
        with patch("necroprobe.validation.json.loads") as loads:
            with self.assertRaisesRegex(ProbeError, "json_nodes"):
                json_object(raw)
            loads.assert_not_called()
        boundary = b'{"x":[' + b'0,' * 9997 + b'0]}'
        self.assertEqual(9998, len(json_object(boundary)["x"]))

    def test_huge_integer_is_validation_error_not_overflow(self):
        with self.assertRaises(ProbeError):
            number(10 ** 1000, 0, 4096)
