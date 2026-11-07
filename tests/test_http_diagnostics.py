"""TEST044: bounded, credential-free readiness and closed transport evidence."""
from contextlib import contextmanager
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import threading
import time
import unittest
from unittest.mock import patch

from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from timer_support import TimerTestCase


@contextmanager
def reply_server(raw=b'{"server_version":"1.98.14-ngg2"}', *, status=200, length=True,
                 declared=None, location=None, delay=0, drip=0):
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass
        def respond(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            calls.append((self.command, self.path, dict(self.headers), body))
            if delay:
                time.sleep(delay)
            self.send_response(status)
            if length:
                self.send_header('Content-Length', str(len(raw) if declared is None else declared))
            if location:
                self.send_header('Location', location)
            self.send_header('Connection', 'close')
            self.end_headers()
            try:
                if drip:
                    for byte in raw:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(drip)
                else:
                    self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass
        do_GET = respond
        do_POST = respond
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    try:
        yield server.server_port, calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


class HttpDiagnosticTests(unittest.TestCase):
    def test_public_schema_is_get_without_credentials_or_request_body(self):
        with reply_server() as (port, calls):
            transport = HttpTransport(port)
            self.assertEqual({'server_version': '1.98.14-ngg2'}, json.loads(transport.schema(.5)))
            self.assertEqual(('GET', '/schema'), calls[0][:2])
            self.assertEqual(b'', calls[0][3])
            headers = {k.lower(): v for k, v in calls[0][2].items()}
            self.assertNotIn('authorization', headers)
            self.assertNotIn('cookie', headers)
            self.assertNotIn('tok', headers)

    def test_refusal_records_closed_kind_and_monotonic_bounds(self):
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            transport = HttpTransport(reserved.getsockname()[1])
            with self.assertRaisesRegex(ProbeError, '^connection_error$'):
                transport(b'PRIVATE_REQUEST', .1)
        diagnostic = transport.last_diagnostic
        self.assertEqual('refused', diagnostic.get('kind'))
        self.assertEqual('connect', diagnostic['stage'])
        self.assertEqual(errno.ECONNREFUSED, diagnostic['errno'])
        self.assertLessEqual(diagnostic['started_ns'], diagnostic['ended_ns'])
        self.assertEqual({'stage', 'kind', 'errno', 'status', 'started_ns', 'ended_ns'}, set(diagnostic))
        self.assertNotIn('PRIVATE', json.dumps(diagnostic))

    def test_schema_size_boundary_with_and_without_content_length(self):
        for length in (True, False):
            for size in (512 * 1024, 512 * 1024 + 1):
                with self.subTest(length=length, size=size), reply_server(b'x' * size, length=length) as (port, _):
                    transport = HttpTransport(port)
                    if size == 512 * 1024:
                        self.assertEqual(size, len(transport.schema(.5)))
                        self.assertEqual('ok', transport.last_diagnostic['kind'])
                    else:
                        with self.assertRaisesRegex(ProbeError, '^http_body_limit$'):
                            transport.schema(.5)
                        self.assertEqual('body_limit', transport.last_diagnostic['kind'])

    def test_legacy_post_retains_its_larger_response_budget(self):
        raw = b'x' * (512 * 1024 + 1)
        for length in (True, False):
            with self.subTest(length=length), reply_server(raw, length=length) as (port, calls):
                self.assertEqual(raw, HttpTransport(port)(b'PRIVATE_SEALED_BODY', .5))
                self.assertEqual(('POST', '/rpc'), calls[0][:2])

    def test_redirect_is_not_followed_and_error_body_is_not_saved(self):
        with reply_server() as (target, target_calls):
            with reply_server(b'PRIVATE_RESPONSE', status=302,
                              location='http://127.0.0.1:%d/private' % target) as (port, _):
                transport = HttpTransport(port)
                with self.assertRaisesRegex(ProbeError, '^http_status_302$'):
                    transport.schema(.5)
                self.assertEqual('http_status', transport.last_diagnostic['kind'])
                self.assertEqual(302, transport.last_diagnostic['status'])
                self.assertNotIn('PRIVATE', json.dumps(transport.last_diagnostic))
            self.assertEqual([], target_calls)

    def test_http_failure_keeps_numeric_status_only(self):
        for status in (401, 500, 503):
            with self.subTest(status=status), reply_server(b'PRIVATE_ERROR_BODY', status=status) as (port, _):
                transport = HttpTransport(port)
                with self.assertRaisesRegex(ProbeError, '^http_status_%d$' % status):
                    transport.schema(.5)
                self.assertEqual(('http_status', status),
                                 (transport.last_diagnostic['kind'], transport.last_diagnostic['status']))
                self.assertNotIn('PRIVATE', json.dumps(transport.last_diagnostic))

    def test_unread_error_response_is_closed_before_return(self):
        import http.client
        original = http.client.HTTPConnection.getresponse
        responses = []
        def remember(connection):
            response = original(connection)
            responses.append(response)
            return response
        with reply_server(b'PRIVATE_BODY', status=401) as (port, _):
            with patch('necroprobe.protocol.http.client.HTTPConnection.getresponse', remember):
                with self.assertRaisesRegex(ProbeError, '^http_status_401$'):
                    HttpTransport(port).schema(.5)
        try:
            self.assertTrue(responses[0].isclosed())
        finally:
            for response in responses:
                response.close()

    def test_declared_body_truncation_is_distinct_from_a_refusal(self):
        with reply_server(b'abc', declared=8) as (port, _):
            transport = HttpTransport(port)
            with self.assertRaisesRegex(ProbeError, '^http_body_truncated$'):
                transport.schema(.5)
            self.assertEqual(('body_truncated', 'body'),
                             (transport.last_diagnostic['kind'], transport.last_diagnostic['stage']))

    def test_socket_header_timeout_is_classified(self):
        with reply_server(delay=.05) as (port, _):
            transport = HttpTransport(port)
            with self.assertRaisesRegex(ProbeError, '^connection_error$'):
                transport.schema(.01)
            self.assertEqual(('timeout', 'headers'),
                             (transport.last_diagnostic['kind'], transport.last_diagnostic['stage']))

    def test_errno_classes_do_not_copy_exception_messages(self):
        cases = ((errno.ECONNRESET, 'reset'), (errno.ECONNABORTED, 'reset'),
                 (errno.EPIPE, 'reset'), (errno.EHOSTUNREACH, 'unreachable'),
                 (errno.ENETUNREACH, 'unreachable'), (errno.EACCES, 'io_error'))
        for code, expected in cases:
            with self.subTest(code=code), patch('necroprobe.protocol.http.client.HTTPConnection.connect',
                                             side_effect=OSError(code, 'PRIVATE_EXCEPTION')):
                transport = HttpTransport()
                with self.assertRaisesRegex(ProbeError, '^connection_error$'):
                    transport.schema(.1)
                self.assertEqual(expected, transport.last_diagnostic['kind'])
                self.assertNotIn('PRIVATE', json.dumps(transport.last_diagnostic))

    def test_http_disconnect_and_protocol_errors_are_distinct(self):
        from http.client import RemoteDisconnected, BadStatusLine, IncompleteRead
        for exc, kind in ((RemoteDisconnected('PRIVATE'), 'disconnected'),
                          (BadStatusLine('PRIVATE'), 'protocol_error'),
                          (IncompleteRead(b'PRIVATE'), 'body_truncated'),
                          (ValueError('PRIVATE'), 'protocol_error')):
            with self.subTest(kind=kind), patch('necroprobe.protocol.http.client.HTTPConnection.getresponse',
                                              side_effect=exc), reply_server() as (port, _):
                transport = HttpTransport(port)
                with self.assertRaisesRegex(ProbeError, '^connection_error$'):
                    transport.schema(.5)
                self.assertEqual(kind, transport.last_diagnostic['kind'])
                self.assertNotIn('PRIVATE', json.dumps(transport.last_diagnostic))

    def test_next_request_replaces_prior_failure_diagnostic(self):
        transport = HttpTransport()
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0)); transport.port = reserved.getsockname()[1]
            with self.assertRaises(ProbeError):
                transport.schema(.1)
        old = dict(transport.last_diagnostic)
        with reply_server() as (port, _):
            transport.port = port
            transport.schema(.5)
        self.assertEqual(('ok', None, 200), (transport.last_diagnostic['kind'],
                         transport.last_diagnostic['errno'], transport.last_diagnostic['status']))
        self.assertLessEqual(old['ended_ns'], transport.last_diagnostic['started_ns'])


class SchemaDeadlineTests(TimerTestCase):
    def test_readiness_slow_drip_has_an_owned_total_deadline(self):
        with reply_server(b'x' * 100, drip=.005) as (port, _):
            transport = HttpTransport(port)
            began = time.monotonic()
            with self.assertRaisesRegex(ProbeError, '^rpc_deadline$'):
                with self.timer.deadline(.04):
                    transport.schema(.3)
            self.assertLess(time.monotonic() - began, .5)
            self.assertEqual(('deadline', 'body'),
                             (transport.last_diagnostic['kind'], transport.last_diagnostic['stage']))


if __name__ == '__main__':
    unittest.main()
