"""TEST087 local assessment publication; procedural data, no native C or game.

The native evaluator adapter explicitly reports unavailable. These assertions
cover integrity, immutable ZIP snapshots and display wiring, not recognition
accuracy or the native goods milestone.
"""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from necroprobe import native_walk as native
from necroprobe import target_assessment as target
from necroprobe import test069 as publication
from necroprobe import test086, test087
from necroprobe.validation import ProbeError
from tests.test_device_recording import procedural_recording, write_recording
from tools import evaluate_device_recording as audit


class UnavailableCore:
    def analyze(self, _rgba):
        raise ProbeError('target_test_native_unavailable')


def report_bytes(record):
    return json.dumps(record, sort_keys=True, separators=(',', ':')).encode()


def assessment(record, digest):
    return dict(schema=target.SCHEMA, classifier=target.CLASSIFIER,
                features_sha256=target.FEATURE_SHA256, run_id=record['run_id'],
                report_sha256=digest, outcome='unknown', reason='no_authority', inputs=[], sources=[])


def seed(base):
    record, pixels = procedural_recording()
    record['native_report']['ui_frozen'] = False
    folder = base/('native-'+record['run_id']); (folder/'images').mkdir(parents=True)
    for name, data in pixels.items(): (folder/'images'/name).write_bytes(data)
    native._save(base, record)
    record = native._load(base)
    assert native._read_only_terminal(record['native_state'], record['native_report'])
    native._save(base, record)
    return record


class TargetPublication087Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='target-publication087-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root/'local'/'test-087'
        self.destination = self.root/'mounted'; self.destination.mkdir()

    def evaluate(self, record, pixels, value=None, extra=()):
        path = self.root/'recording.zip'
        files = list(extra)
        if value is not None:
            files.append(('test-procedural/native-'+record['run_id']+'/'+target.SIDECAR,
                          json.dumps(value, sort_keys=True, separators=(',', ':')).encode()))
        write_recording(path, record, pixels, extra=files)
        return audit.evaluate_recording(path, core=UnavailableCore())

    def invoke(self, prepare, *, cancelled=lambda: False):
        return publication.run(self.destination, spool=self.base,
            session=Mock(side_effect=AssertionError('publication recovery must not start a game')),
            cancelled=cancelled, notice=lambda _message: None, test_number='087', prepare=prepare)

    def test_valid_closed_sidecar_is_accepted_and_original_zip_layout_stays_valid(self):
        record, pixels = procedural_recording()
        value = assessment(record, hashlib.sha256(report_bytes(record)).hexdigest())
        self.assertEqual(value, target.validate_assessment(value, record=record, report_sha=value['report_sha256']))
        result = self.evaluate(record, pixels, value)
        self.assertEqual('pass', result['integrity']['status'],
                         'the one validated local assessment must be accepted alongside the original closed journal')
        self.assertEqual('unavailable', result['c_partial_evaluation']['status'])
        self.assertEqual('fail', result['recorded_milestone']['status'],
                         'accepting a sidecar does not turn the procedural no-goods run into native success')
        self.assertEqual('pass', self.evaluate(record, pixels)['integrity']['status'])

    def test_foreign_changed_malformed_sidecar_and_every_unrelated_extra_are_rejected(self):
        record, pixels = procedural_recording()
        original = assessment(record, hashlib.sha256(report_bytes(record)).hexdigest())
        for key, replacement in (('extra', True), ('run_id', 'b'*32), ('report_sha256', '0'*64),
                                 ('features_sha256', '0'*64), ('classifier', 'untrusted'),
                                 ('outcome', 'none'), ('inputs', [dict(role='authority', capture_id=1, sha256='0'*64)])):
            with self.subTest(key=key):
                changed = deepcopy(original); changed[key] = replacement
                self.assertEqual('invalid', self.evaluate(record, pixels, changed)['integrity']['status'])
        sidecar = 'test-procedural/native-'+record['run_id']+'/'+target.SIDECAR
        for content in (b'{"schema":"x","schema":"y"}', b'{"x":NaN}', b'['*30+b'0'+b']'*30, b'x'*(target.MAX_SIDECAR+1)):
            self.assertEqual('invalid', self.evaluate(record, pixels, extra=[(sidecar, content)])['integrity']['status'])
        for name in ('test-procedural/target-assessment.json',
                     'test-procedural/native-'+record['run_id']+'/extra.json',
                     'test-procedural/native-'+('b'*32)+'/'+target.SIDECAR):
            self.assertEqual('invalid', self.evaluate(record, pixels, original, [(name, b'{}')])['integrity']['status'])

    def test_prepare_follows_certificate_and_its_sidecar_is_in_the_same_verified_zip(self):
        record = seed(self.base)
        original = (self.base/'active.json').read_bytes()
        order = []; certificate = publication._certificate
        def checked(*args, **kwargs):
            result = certificate(*args, **kwargs); order.append('certificate'); return result
        def prepare(base, current, digest, cancelled):
            self.assertEqual(['certificate'], order)
            self.assertFalse(list(self.base.parent.glob('.test-087-publication/*.zip')))
            self.assertEqual(hashlib.sha256(original).hexdigest(), digest)
            result = target.prepare_assessment(base, current, digest, cancelled)
            order.append('prepare'); return result
        with patch.object(publication, '_certificate', side_effect=checked):
            returned, archive = self.invoke(prepare)
        self.assertEqual(['certificate', 'prepare'], order)
        self.assertEqual(record, returned)
        folder = self.base/('native-'+record['run_id'])
        self.assertEqual(original, (self.base/'active.json').read_bytes())
        self.assertEqual(original, (folder/'report.json').read_bytes())
        sidecar = (folder/target.SIDECAR).read_bytes()
        value = target.validate_assessment(json.loads(sidecar), record=record,
                                           report_sha=hashlib.sha256(original).hexdigest())
        self.assertEqual(('unknown', 'no_authority'), (value['outcome'], value['reason']))
        with zipfile.ZipFile(archive) as result:
            self.assertIsNone(result.testzip())
            self.assertEqual(sidecar, result.read('test-087/'+folder.name+'/'+target.SIDECAR))
            self.assertEqual(original, result.read('test-087/active.json'))
            for item in record['images']:
                self.assertEqual(item['sha256'], hashlib.sha256(result.read('test-087/'+folder.name+'/images/'+item['name'])).hexdigest())

    def test_incomplete_or_changed_native_evidence_never_calls_prepare(self):
        for fault in ('cursor', 'prefix', 'missing', 'changed', 'unresolved_input'):
            with self.subTest(fault=fault):
                self.base = self.root/fault/'test-087'; record = seed(self.base)
                image = self.base/('native-'+record['run_id'])/'images'/record['images'][0]['name']
                if fault == 'cursor':
                    record['image_export']['offsets'][0] = 0
                    record['image_export']['prefix_sha256'][0] = hashlib.sha256(b'').hexdigest()
                elif fault == 'prefix': record['image_export']['prefix_sha256'][0] = '0'*64
                elif fault == 'missing': image.unlink()
                elif fault == 'changed': image.write_bytes(image.read_bytes()+b'changed')
                else: record['native_report']['input_state'] = 4
                native._save(self.base, record)
                prepare = Mock(side_effect=AssertionError('uncertified images cannot be classified'))
                with self.assertRaises((OSError, ValueError, ProbeError)) as rejected: self.invoke(prepare)
                if fault == 'missing': self.assertIsInstance(rejected.exception, FileNotFoundError)
                else:
                    self.assertEqual({'cursor': 'publication_cursor_incomplete', 'prefix': 'publication_cursor_incomplete',
                                      'changed': 'publication_image_changed', 'unresolved_input': 'publication_native_incomplete'}[fault],
                                     str(rejected.exception))
                prepare.assert_not_called()
                self.assertFalse(list(self.destination.rglob('*.zip')))

    def test_interrupted_publication_reuses_frozen_sidecar_archive_and_receipt_without_prepare(self):
        record = seed(self.base); calls = []
        def prepare(*args):
            calls.append('prepare'); return target.prepare_assessment(*args)
        atomic = native._atomic
        def interrupt(path, data):
            if path.name.endswith('.receipt.json'): raise OSError('interrupted receipt')
            return atomic(path, data)
        with patch.object(native, '_atomic', side_effect=interrupt):
            with self.assertRaisesRegex(OSError, 'interrupted receipt'): self.invoke(prepare)
        folder = self.base/('native-'+record['run_id'])
        sidecar = (folder/target.SIDECAR).read_bytes()
        final = self.destination/'runtime'/('test-087-'+record['run_id']+'.zip')
        original = final.read_bytes()
        returned, archive = self.invoke(Mock(side_effect=AssertionError('a frozen archive cannot be retrofitted')))
        self.assertEqual(record, returned)
        self.assertEqual(original, archive.read_bytes())
        self.assertEqual(sidecar, (folder/target.SIDECAR).read_bytes())
        self.assertEqual(['prepare'], calls)
        storage = self.base.parent/('.'+self.base.name+'-publication')
        with self.assertRaisesRegex(ValueError, 'cancel_requested'):
            self.invoke(lambda *args: target.prepare_assessment(*args), cancelled=lambda: True)
        self.assertTrue(publication._published(self.base, self.destination, record, storage, lambda: False, '087'))
        publication._publish(self.base, self.destination, record, storage, lambda: False, lambda _message: None,
                             '087', prepare=Mock(side_effect=AssertionError('published ZIP must remain unchanged')))
        self.assertEqual(original, final.read_bytes())

    def test_new_entry_connects_prepare_and_displays_only_target_candidate_or_unknown(self):
        with patch.object(test087, 'device_main', return_value=0) as main:
            self.assertEqual(0, test087.main(['--check']))
            self.assertEqual('087', main.call_args.kwargs['test_number'])
            prepare = main.call_args.kwargs['prepare']
        for outcome, expected in (('target', 'のろいのゆびわ'), ('candidate', '候補'),
                                  ('unknown', 'のろいのゆびわとの一致は未確認（対象なしとは未確定）')):
            output = io.StringIO()
            reason = {'target': 'icon_and_name', 'candidate': 'icon_only', 'unknown': 'no_target_evidence'}[outcome]
            # The display fixture represents an evaluated source, as an actual
            # sidecar does; outcome alone did not describe execution status.
            value = dict(outcome=outcome, reason=reason, sources=[dict(outcome=outcome, reason=reason)])
            with patch.object(test087, 'prepare_assessment', return_value=value) as assess:
                with patch('sys.stdout', output): result = prepare(self.base, {}, 'a'*64, lambda: False)
            self.assertEqual(outcome, result['outcome'])
            self.assertIn('実施済み', output.getvalue())
            self.assertIn(expected, output.getvalue())
            # Permit only the explicit statement that absence is unconfirmed;
            # any separate assertion of absence remains forbidden.
            self.assertNotIn('対象なし', output.getvalue().replace(expected, '', 1))
            assess.assert_called_once()
        with patch.object(test086, 'device_main', return_value=0) as old:
            self.assertEqual(0, test086.main(['--check']))
            self.assertEqual({'test_number': '086'}, old.call_args.kwargs,
                             'the old entry retains its default no-assessment publication path')
