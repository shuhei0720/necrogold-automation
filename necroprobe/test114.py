"""TEST114 on-device goods and continuous trial entry.

The inherited capabilities and restart/publication contracts stay unchanged.
"""
from .native_cycle import IRREGULAR_PROTOCOL
from .campaign_diagnostics114 import admit_readonly114
from .test099 import main as device_main
from .test113 import DeviceClient113


class DeviceClient114(DeviceClient113):
    trial_revision = 'native-device-failures-trial-v114'
    diagnostics114 = True

    def _validate(self, method, params):
        if admit_readonly114(method, params):
            return
        return super()._validate(method, params)


def main(argv=None):
    return device_main(argv, test_number='114', protocol_spec=IRREGULAR_PROTOCOL,
                       client_class=DeviceClient114)


if __name__ == '__main__':
    raise SystemExit(main())
