"""Cycle export wire sizes include Swift JSON slash escaping and sealing."""
import base64
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import native_cycle as cycle
from necroprobe.crypto import Crypto, mac
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from test_native_cycle_client094 import Server, RUN, EXPORT, png
from test_protocol import KEY, TOK


class Response:
    status = 200

    def __init__(self, raw):
        self.body = io.BytesIO(raw)
        self.length = len(raw)
        self.read_bytes = 0
        self.closed = False

    def getheader(self, name):
        return str(self.length) if name == 'Content-Length' else None

    def read1(self, count):
        raw = self.body.read(count)
        self.read_bytes += len(raw)
        return raw

    def close(self):
        self.closed = True


class EncryptedHTTP:
    """Use real HttpTransport admission/auth/crypto with an in-memory socket peer."""
    def __init__(self, server, *, corrupt=False, oversized=None):
        self.server, self.corrupt, self.oversized = server, corrupt, oversized
        self.responses = []
        self.wire_sizes = []
        self.crypto = Crypto(native=True)

    def connection(self, *_args, **_kwargs):
        peer = self
        class Connection:
            def connect(self):
                pass

            def request(self, method, path, body=None, headers=None):
                assert (method, path) == ('POST', '/rpc')
                self.body = body

            def getresponse(self):
                envelope = json.loads(self.body)
                nonce = bytes.fromhex(envelope['nonce'])
                request = json.loads(peer.crypto.xor(mac(KEY, b'loopctrl-v1|enc-req'+nonce),
                    nonce, base64.b64decode(envelope['ct'])))
                if peer.oversized is not None:
                    raw = b'x' * peer.oversized
                else:
                    result = peer.server.call(request['method'], request['params'])
                    # Production JSONRPCServer uses JSONEncoder's slash escaping,
                    # then SecureEnvelope seals it with unescaped base64 ciphertext.
                    plain = json.dumps(dict(jsonrpc='2.0', id=request['id'], result=result),
                        separators=(',', ':')).replace('/', r'\/').encode()
                    cipher = peer.crypto.xor(mac(KEY, b'loopctrl-v1|enc-resp'+nonce), nonce, plain)
                    tag = mac(mac(KEY, b'loopctrl-v1|mac'+nonce), b'resp'+nonce+cipher).hex()
                    raw = json.dumps(dict(v=1, nonce=nonce.hex(), ct=base64.b64encode(cipher).decode(),
                        tag='0'*64 if peer.corrupt else tag), separators=(',', ':')).encode()
                reply = Response(raw)
                peer.responses.append(reply)
                peer.wire_sizes.append((request['params'].get('mode'), len(raw)))
                return reply

            def close(self):
                pass
        return Connection()


class CycleHTTP098Tests(unittest.TestCase):
    def test_explicit_recovery_entry_keeps_098_spool_and_forwards_no_start_mode(self):
        from necroprobe import test094 as entry
        parser_exit = None
        result = None
        with patch.object(entry, 'load_pairing', return_value=(KEY, TOK)), \
             patch.object(entry, 'run', return_value=({'last_error':'http_body_limit'}, None)) as run, \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            try:
                result = entry.main(['--recovery'], test_number='098')
            except SystemExit as exc:
                parser_exit = exc.code
        self.assertIsNone(parser_exit, 'explicit recovery must be accepted without starting a new run')
        self.assertEqual(2, result)
        self.assertEqual(1, run.call_count)
        self.assertTrue(run.call_args.kwargs['recovery_only'])
        self.assertEqual(Path.home()/'.necroprobe'/'runtime'/'test-098', run.call_args.kwargs['spool'])

    def test_valid_slash_heavy_four_chunk_png_passes_authenticated_http_and_full_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)/'test-098'
            base.mkdir()
            # A valid PNG ancillary field can contain Latin-1 255. Its base64
            # requires slash escaping; no classifier or pixel interpretation runs.
            image = png(300000).replace(b'x'*300000, b'\xff'*300000)
            import struct, zlib
            start = image.index(b'tEXt')
            length = struct.unpack('>I', image[start-4:start])[0]
            crc_at = start+4+length
            image = image[:crc_at]+struct.pack('>I', zlib.crc32(image[start:crc_at])&0xffffffff)+image[crc_at+4:]
            server = Server(base, raw=image)
            peer = EncryptedHTTP(server)
            record = cycle.fresh_record(RUN)
            record['start_intent'] = True
            cycle._journal(base, record)
            failure = None
            with OwnedRpcTimer() as timer, patch('necroprobe.protocol.http.client.HTTPConnection', peer.connection):
                client = cycle.CycleClient(HttpTransport(), KEY, TOK, crypto=Crypto(native=True), deadline_owner=timer)
                try:
                    cycle.collect(client, base, record, notice=lambda _: None)
                except ProbeError as exc:
                    failure = exc.code
            self.assertIsNone(failure, 'valid encrypted four-chunk PNG must finish recovery: '+str(peer.wire_sizes))
            self.assertTrue(record['resolved'])
            self.assertEqual(server.manifest, cycle.verify_evidence(base, record))
            self.assertEqual(image, (base/('cycle-'+RUN)/'images'/'capture-000007.png').read_bytes())
            large = [size for mode,size in peer.wire_sizes if mode == 'batch']
            self.assertGreater(max(large), 512*1024)
            self.assertLessEqual(max(large), 1024*1024)
            self.assertTrue(all(reply.closed for reply in peer.responses))
            self.assertFalse(any(method == 'necro_native_start' for method,_ in server.calls))

    def test_bulk_allowance_does_not_bypass_response_mac(self):
        server = Server(raw=b'\xff'*(4*65536))
        peer = EncryptedHTTP(server, corrupt=True)
        with OwnedRpcTimer() as timer, patch('necroprobe.protocol.http.client.HTTPConnection', peer.connection):
            client = cycle.CycleClient(HttpTransport(), KEY, TOK, crypto=Crypto(native=True), deadline_owner=timer)
            with self.assertRaisesRegex(ProbeError, '^response_mac_mismatch$'):
                client.call('necro_native_cycle', dict(run_id=RUN, mode='batch', export_id=EXPORT,
                    capture_id=7, offset=0, count=4))
        self.assertGreater(peer.wire_sizes[0][1], 512*1024)

    def test_oversized_bulk_and_unchanged_single_status_limits_reject_at_headers(self):
        for mode, maximum in (('batch',1024*1024), ('manifest',1024*1024),
                              ('chunk',256*1024), ('record',256*1024), ('status',512*1024)):
            with self.subTest(mode=mode):
                peer = EncryptedHTTP(Server(), oversized=maximum+1)
                params = dict(run_id=RUN, mode=mode)
                if mode in ('batch','chunk','record'):
                    params.update(export_id=EXPORT, offset=0)
                    params['sequence' if mode == 'record' else 'capture_id'] = 1 if mode == 'record' else 7
                if mode == 'batch': params['count'] = 4
                if mode == 'status': params['keepalive'] = False
                with OwnedRpcTimer() as timer, patch('necroprobe.protocol.http.client.HTTPConnection', peer.connection):
                    transport = HttpTransport()
                    client = cycle.CycleClient(transport, KEY, TOK, crypto=Crypto(native=True), deadline_owner=timer)
                    with self.assertRaisesRegex(ProbeError, '^http_body_limit$'):
                        client.call('necro_native_cycle', params)
                    self.assertEqual('http', client.last_failure['stage'])
                self.assertEqual(0, peer.responses[0].read_bytes)
                self.assertTrue(peer.responses[0].closed)


if __name__ == '__main__':
    unittest.main()
