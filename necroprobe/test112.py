"""TEST112 explicitly yields after a durable normal restart before a fresh run."""
from .native_cycle import IRREGULAR_PROTOCOL
from .test099 import main as device_main
from .test111 import ImagePriceClient111, IMAGE_PRICE_CAPABILITY

RESTART_YIELD_CAPABILITY = 'necrogold_native_restart_yield_v1'


class RestartYieldClient112(ImagePriceClient111):
    required_capabilities = frozenset((IMAGE_PRICE_CAPABILITY, RESTART_YIELD_CAPABILITY))
    yield_after_restart = True
    allow_restarted_budget = True
    trial_revision = 'native-restart-yield-trial-v1'


def main(argv=None):
    return device_main(argv, test_number='112', protocol_spec=IRREGULAR_PROTOCOL,
                       client_class=RestartYieldClient112)


if __name__ == '__main__':
    raise SystemExit(main())
