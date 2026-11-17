"""TEST113 device failures, native observation, and drain-aware trial entry."""
from .native_cycle import IRREGULAR_PROTOCOL
from .test099 import main as device_main
from .test112 import RestartYieldClient112


class DeviceClient113(RestartYieldClient112):
    trial_revision = 'native-device-failures-trial-v113'


def main(argv=None):
    return device_main(argv, test_number='113', protocol_spec=IRREGULAR_PROTOCOL,
                       client_class=DeviceClient113)


if __name__ == '__main__':
    raise SystemExit(main())
