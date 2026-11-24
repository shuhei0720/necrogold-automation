"""TEST118 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test117 import DeviceClient117, FiniteClient117


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes118_v1'


class DeviceClient118(DeviceClient117):
    trial_revision = 'native-device-failures-trial-v118'
    required_capabilities = DeviceClient117.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient118(FiniteClient117):
    trial_revision = DeviceClient118.trial_revision
    required_capabilities = FiniteClient117.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='118', continuous_client=DeviceClient118, finite_client=FiniteClient118)


if __name__ == '__main__':
    raise SystemExit(main())
