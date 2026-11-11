"""TEST074 device entry; reuse verified local result publication."""
from .test069 import main as device_main


def main(argv=None):
    return device_main(argv, test_number='074')


if __name__ == '__main__':
    raise SystemExit(main())
