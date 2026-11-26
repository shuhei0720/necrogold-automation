"""TEST124 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test123 import DeviceClient123, FiniteClient123


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes124_v1'


class DeviceClient124(DeviceClient123):
    trial_revision = 'native-device-failures-trial-v124'
    required_capabilities = DeviceClient123.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient124(FiniteClient123):
    trial_revision = DeviceClient124.trial_revision
    required_capabilities = FiniteClient123.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='124', continuous_client=DeviceClient124, finite_client=FiniteClient124)


if __name__ == '__main__':
    raise SystemExit(main())
