"""TEST119 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test118 import DeviceClient118, FiniteClient118


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes119_v1'


class DeviceClient119(DeviceClient118):
    trial_revision = 'native-device-failures-trial-v119'
    required_capabilities = DeviceClient118.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient119(FiniteClient118):
    trial_revision = DeviceClient119.trial_revision
    required_capabilities = FiniteClient118.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='119', continuous_client=DeviceClient119, finite_client=FiniteClient119)


if __name__ == '__main__':
    raise SystemExit(main())
