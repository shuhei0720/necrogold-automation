"""TEST111 requires the image-and-price classifier before starting a run."""
from .native_cycle import IRREGULAR_PROTOCOL
from .test099 import main as device_main
from .trial_evidence099 import IrregularTrialClient110

IMAGE_PRICE_CAPABILITY = 'necrogold_native_image_price_v1'


class ImagePriceClient111(IrregularTrialClient110):
    required_capabilities = frozenset((IMAGE_PRICE_CAPABILITY,))
    trial_revision = 'native-image-price-trial-v1'


def main(argv=None):
    return device_main(argv, test_number='111', protocol_spec=IRREGULAR_PROTOCOL,
                       client_class=ImagePriceClient111)


if __name__ == '__main__':
    raise SystemExit(main())
