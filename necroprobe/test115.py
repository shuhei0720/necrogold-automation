"""TEST115 on-device passage, entry and goods-continuation trial.

The inherited capabilities, private diagnostics and publication contract stay
unchanged; only the trial revision and output directory identify this entry.
"""
from .native_cycle import IRREGULAR_PROTOCOL
from .test099 import main as device_main
from .test114 import DeviceClient114


class DeviceClient115(DeviceClient114):
    trial_revision = 'native-device-failures-trial-v115'


def main(argv=None):
    return device_main(argv, test_number='115', protocol_spec=IRREGULAR_PROTOCOL,
                       client_class=DeviceClient115)


if __name__ == '__main__':
    raise SystemExit(main())
