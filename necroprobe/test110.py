"""TEST110 explicitly selects the bounded irregular-retry protocol."""
from .test099 import main as device_main
from .native_cycle import IRREGULAR_PROTOCOL


def main(argv=None):
    return device_main(argv, test_number='110', protocol_spec=IRREGULAR_PROTOCOL)


if __name__ == '__main__':
    raise SystemExit(main())
