"""TEST117 visible-shop implementation and separately named collection."""
from . import test116 as entry


VISIBLE_GOODS_CAPABILITY = 'necrogold_native_visible_goods_v1'


class DeviceClient117(entry.DeviceClient116):
    trial_revision = 'native-device-failures-trial-v117'
    required_capabilities = entry.DeviceClient116.required_capabilities | frozenset((VISIBLE_GOODS_CAPABILITY,))
    initial_restart = True


class FiniteClient117(entry.FiniteClient116):
    trial_revision = DeviceClient117.trial_revision
    required_capabilities = entry.FiniteClient116.required_capabilities | frozenset((VISIBLE_GOODS_CAPABILITY,))
    initial_restart = True


def main(argv=None):
    return entry._main(argv,test_number='117',continuous_client=DeviceClient117,finite_client=FiniteClient117)


if __name__=='__main__':
    raise SystemExit(main())
