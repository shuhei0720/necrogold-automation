"""Prioritize the proven goods frame; keep assessment provisional until export.

The observer owns no game/RPC authority and writes no sidecar. Its in-memory
cache can only be reused after normal publication verifies the complete run.
"""
import hashlib
import json
from pathlib import Path
import time

from . import native_walk as native, ring_native, target_assessment as target
from .ring_status import assessment_label


def _notice(message):
    print(message, flush=True)


class EarlyAssessment:
    def __init__(self, notice=_notice):
        self._notice = notice
        self._binding = None
        self._selected = []
        self._cache = {}
        self._failure = None
        self._began = None

    @staticmethod
    def _identity(record, selected):
        return (record['run_id'], record['image_export']['export_id'], target.CLASSIFIER,
                target.FEATURE_SHA256, ring_native._PROTOCOL,
                tuple((source['role'], source['capture_id'], source['sha256']) for source in selected))

    def failed(self):
        if self._failure is None:
            self._failure = 'ring_early_failed'

    def _plan(self, record, images):
        report = record.get('native_report') or {}
        if (not native._read_only_terminal(record.get('native_state'), report)
                or report.get('cancel_requested') is True):
            return []
        selected = target._selected(dict(record, images=list(images)))
        if self._binding is None:
            if not selected:
                return []
            self._binding = self._identity(record, selected)
            self._selected = selected
            self._began = time.monotonic()
        target._require(self._binding == self._identity(record, selected), 'ring_early_changed')
        return selected

    def priority(self, record, images):
        try:
            if self._failure is not None:
                return []
            selected = self._plan(record, images)
            for source in selected:
                key = (source['role'], source['capture_id'], source['sha256'])
                if key not in self._cache:
                    return [source['capture_id']]
                if json.loads(self._cache[key])['outcome'] == 'target':
                    return []
            return []
        except target.AssessmentError as error:
            self._failure = str(error)
        except Exception:
            self.failed()
        return []

    def saved(self, base, record, item, cancelled):
        try:
            if self._failure is not None:
                return
            selected = self._plan(record, record['image_export']['images'])
            source = next((source for source in selected if source['capture_id'] == item['capture_id']), None)
            if source is None:
                return
            # A conclusive authority result never needs another frame's pixels.
            if any(json.loads(value)['outcome'] == 'target' for value in self._cache.values()):
                return
            key = (source['role'], source['capture_id'], source['sha256'])
            if key in self._cache:
                return
            target._check(cancelled)
            index = record['image_export']['images'].index(item)
            target._require(item in record['images'] and item['sha256'] == source['sha256']
                and record['image_export']['offsets'][index] == item['bytes']
                and record['image_export']['prefix_sha256'][index] == source['sha256'], 'ring_early_changed')
            name = 'capture-'+format(source['capture_id'], '06d')+'.png'
            target._require(item['name'] == name, 'ring_early_changed')
            base = Path(base)
            data = target._read(base/('native-'+record['run_id'])/'images'/name, base, 512*1024)
            target._require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == source['sha256'],
                            'ring_early_changed')
            result = target.classify_png(data, cancelled)
            # Canonical bytes are immutable and keep Python float types on load.
            self._cache[key] = target._encoded(result)
            outcomes = [json.loads(value)['outcome'] for value in self._cache.values()]
            outcome = 'target' if 'target' in outcomes else 'candidate' if 'candidate' in outcomes else 'unknown'
            label = assessment_label(outcome, has_sources=bool(self._cache))
            elapsed = time.monotonic()-self._began
            try:
                self._notice('対象の暫定先行確認: '+label+'（全画像の保存・照合は継続中。結果回収開始から'
                             +format(elapsed, '.3f')+'秒）')
            except Exception:
                # Display cannot invalidate an already verified local result.
                pass
        except target.AssessmentError as error:
            self._failure = str(error)
        except Exception:
            self.failed()

    def before_prepare(self, record):
        """Check even a final no-source result; call after the full certificate."""
        if self._failure is not None:
            raise target.AssessmentError(self._failure)
        try:
            if self._binding is not None:
                target._require(self._binding == self._identity(record, target._selected(record)),
                                'ring_early_changed')
        except target.AssessmentError:
            raise
        except Exception:
            raise target.AssessmentError('ring_early_changed') from None

    def classify(self, record, source, data, cancelled):
        """Use only from prepare_assessment after its complete certificate."""
        target._check(cancelled)
        self.before_prepare(record)
        selected = target._selected(record)
        target._require(source in selected and hashlib.sha256(data).hexdigest() == source['sha256'],
                        'ring_early_changed')
        if self._binding is not None:
            target._require(self._binding == self._identity(record, selected), 'ring_early_changed')
        key = (source['role'], source['capture_id'], source['sha256'])
        if key in self._cache:
            try:
                return json.loads(self._cache[key])
            except (TypeError, ValueError):
                raise target.AssessmentError('ring_early_changed') from None
        # A recovery invocation may have no early image observation. It uses
        # the same bounded compiled classifier after the normal certificate.
        return target.classify_png(data, cancelled)
