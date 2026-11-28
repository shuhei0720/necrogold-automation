"""TEST126 device fixes with an isolated collection namespace."""
from . import test116 as entry
from .test125 import DeviceClient125, FiniteClient125


IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes126_v1'


class DeviceClient126(DeviceClient125):
    trial_revision = 'native-device-failures-trial-v126'
    required_capabilities = DeviceClient125.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))
    start_admission_diagnostics = True


class FiniteClient126(FiniteClient125):
    trial_revision = DeviceClient126.trial_revision
    required_capabilities = FiniteClient125.required_capabilities | frozenset((IMPLEMENTATION_CAPABILITY,))


def main(argv=None):
    return entry._main(argv, test_number='126', continuous_client=DeviceClient126, finite_client=FiniteClient126)


if __name__ == '__main__':
    raise SystemExit(main())
