"""TEST125 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test124 import DeviceClient124, FiniteClient124


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes125_v1'


class DeviceClient125(DeviceClient124):
    trial_revision = 'native-device-failures-trial-v125'
    required_capabilities = DeviceClient124.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient125(FiniteClient124):
    trial_revision = DeviceClient125.trial_revision
    required_capabilities = FiniteClient124.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='125', continuous_client=DeviceClient125, finite_client=FiniteClient125)


if __name__ == '__main__':
    raise SystemExit(main())
