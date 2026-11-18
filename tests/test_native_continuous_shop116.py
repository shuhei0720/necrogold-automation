"""TEST116 shop proofs repeated with the actual continuous C profile.

Only the profile constructor changes. The calibrated partial/early-FULL
procedural pixels, normal Ring, original ACK and all assertions remain the
existing TEST116 tests. This is profile integration, not phone acceptance.
"""
import ctypes as C

from tests import test_native_controller as native
from tests import test_native_partial116 as partial
from tests import test_native_early_full116 as early


class _ContinuousLibrary:
    def __init__(self, original):
        self.original = original
        self.enabled = 0
        original.ng2_controller_enable_continuous.argtypes = [
            C.c_void_p, C.c_int32, C.c_uint64]

    def __getattr__(self, name):
        return getattr(self.original, name)

    def ng2_controller_enable_restart_yield(self, engine):
        status = native.Status()
        self.original.ng2_controller_status(engine, C.byref(status))
        accepted = self.original.ng2_controller_enable_continuous(
            engine, 0, status.started_ns + 2880_000_000_000)
        self.enabled += accepted == 1
        return accepted


class NativeContinuousPartial116Tests(partial.NativePartial116Tests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lib = _ContinuousLibrary(cls.lib)

    def setUp(self):
        self.enabled_before = self.lib.enabled

    def tearDown(self):
        self.assertGreater(self.lib.enabled, self.enabled_before,
            'the existing partial proof must actually use continuous C enable')


class NativeContinuousEarlyFull116Tests(early.NativeEarlyFull116Tests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lib = _ContinuousLibrary(cls.lib)

    def setUp(self):
        self.enabled_before = self.lib.enabled
        super().setUp()

    def tearDown(self):
        self.assertGreater(self.lib.enabled, self.enabled_before,
            'the existing late ACK proof must actually use continuous C enable')
