"""TEST123 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test122 import DeviceClient122, FiniteClient122


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes123_v1'


class DeviceClient123(DeviceClient122):
    trial_revision = 'native-device-failures-trial-v123'
    required_capabilities = DeviceClient122.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient123(FiniteClient122):
    trial_revision = DeviceClient123.trial_revision
    required_capabilities = FiniteClient122.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='123', continuous_client=DeviceClient123, finite_client=FiniteClient123)


if __name__ == '__main__':
    raise SystemExit(main())
