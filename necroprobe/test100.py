"""TEST100 uses the finite campaign with its own entry and durable labels."""
from .test099 import main as device_main


def main(argv=None):
    return device_main(argv,test_number='100')


if __name__=='__main__':raise SystemExit(main())
