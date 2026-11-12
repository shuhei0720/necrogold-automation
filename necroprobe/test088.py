"""TEST088 device entry; reuse verified publication and TEST087 assessment."""
from .test069 import main as device_main
from .test087 import _prepare


def main(argv=None):
    return device_main(argv, test_number='088', prepare=_prepare)


if __name__ == '__main__':
    raise SystemExit(main())
