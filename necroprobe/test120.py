"""TEST120 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test119 import DeviceClient119, FiniteClient119


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes120_v1'


class DeviceClient120(DeviceClient119):
    trial_revision = 'native-device-failures-trial-v120'
    required_capabilities = DeviceClient119.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient120(FiniteClient119):
    trial_revision = DeviceClient120.trial_revision
    required_capabilities = FiniteClient119.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='120', continuous_client=DeviceClient120, finite_client=FiniteClient120)


if __name__ == '__main__':
    raise SystemExit(main())
