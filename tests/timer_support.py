"""Test scopes explicitly own their process alarm; production owns only its worker."""
import signal
import unittest

from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import Client


class TimerTestCase(unittest.TestCase):
    def setUp(self):
        self.previous_handler = signal.getsignal(signal.SIGALRM)
        self.timer = OwnedRpcTimer()
        self.timer.__enter__()
        self.addCleanup(self.close_timer)

    def close_timer(self):
        try:
            self.timer.__exit__(None, None, None)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self.previous_handler)

    def client(self, *args, **kwargs):
        return Client(*args, deadline_owner=self.timer, **kwargs)
