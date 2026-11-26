"""TEST122 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test121 import DeviceClient121, FiniteClient121


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes122_v1'


class DeviceClient122(DeviceClient121):
    trial_revision = 'native-device-failures-trial-v122'
    required_capabilities = DeviceClient121.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


class FiniteClient122(FiniteClient121):
    trial_revision = DeviceClient122.trial_revision
    required_capabilities = FiniteClient121.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='122', continuous_client=DeviceClient122, finite_client=FiniteClient122)


if __name__ == '__main__':
    raise SystemExit(main())
