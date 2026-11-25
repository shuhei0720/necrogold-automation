"""TEST121 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test120 import DeviceClient120, FiniteClient120


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes121_v1'


class DeviceClient121(DeviceClient120):
    trial_revision = 'native-device-failures-trial-v121'
    required_capabilities = DeviceClient120.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient121(FiniteClient120):
    trial_revision = DeviceClient121.trial_revision
    required_capabilities = FiniteClient120.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='121', continuous_client=DeviceClient121, finite_client=FiniteClient121)


if __name__ == '__main__':
    raise SystemExit(main())
