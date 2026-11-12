"""TEST091 device entry; reuse verified publication and TEST087 assessment."""
from .test069 import main as device_main
from .test087 import _prepare
from .ring_early import EarlyAssessment


def main(argv=None):
    observer = EarlyAssessment()
    def prepare(base, record, report_sha, cancelled):
        return _prepare(base, record, report_sha, cancelled,
                        classify=observer.classify, before=observer.before_prepare)
    return device_main(argv, test_number='091', prepare=prepare, image_observer=observer)


if __name__ == '__main__':
    raise SystemExit(main())
