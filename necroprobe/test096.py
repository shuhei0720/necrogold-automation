"""TEST096: use the native cycle client and publish a separately labelled ZIP."""
from .test094 import main as device_main


def main(argv=None):
    return device_main(argv, test_number='096')


if __name__ == '__main__':
    raise SystemExit(main())
