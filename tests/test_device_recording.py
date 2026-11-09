"""Recording evaluator contracts. Public fixtures are procedural, not game E2E."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image
from necroprobe import gold_scan
from tools import evaluate_device_recording as audit


def procedural_png(paused=False, goods=False):
    image = Image.new('RGB', (896, 414))
    names = ('continue',) if paused else ('icon', 'footer', 'zone_one', 'floor_one')
    for name in names:
        box, _, _, mask = gold_scan._TEMPLATES[name]
        image.paste(Image.new('RGB', mask.size, (180, 180, 180)), box[:2], mask)
    if goods:
        image.paste((200,190,10), (190,90,211,111))
        for x in (196,232,268):
            image.paste((56,)*3, (x-12,136,x+12,137))
            image.paste((180,)*3, (x-11,165,x+7,166))
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def procedural_recording():
    captures, images, pixels = [], [], {}
    for number, paused, prefix in ((1, False, 0), (2, True, 1)):
        start = number * 1000
        row = dict(id=number, start_ns=start, end_ns=start+100, decode_end_ns=start+200,
            analysis_start_ns=start+210, analysis_end_ns=start+300,
            observe_start_ns=start+310, observe_end_ns=start+320,
            completed_prefix_start=prefix, completed_prefix_end=prefix,
            inflight_start=False, inflight_end=False, stable=True)
        raw = procedural_png(paused)
        name = f'capture-{number:06d}.png'
        pixels[name] = raw
        captures.append(row)
        images.append(dict(name=name, format='png', pixel_width=896, pixel_height=414,
            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), capture_id=number,
            capture_start_ns=start, capture_end_ns=start+100, decode_end_ns=start+200,
            completed_prefix=prefix, completed_prefix_start=prefix, completed_prefix_end=prefix,
            stable_prefix=True, inflight_start=False, inflight_end=False))
    pause = dict(id=1, kind=2, outcome=2, direction=0, source_capture_id=1,
        source_start_ns=1000, observed_capture_id=2, begin_ns=1800, end_ns=1900,
        target_ns=0, not_before_ns=1700, deadline_ns=2700, phase_sample_ns=0,
        ordinal=0, x=390, y=448, motion=0, dx=0, dy=0, reason=0)
    native = dict(schema='ngg2-native-v1', clock_id='b'*32, device_now_ns=2400,
        input_state=0, phase=7, reason=17, reason_name='screen', terminal=1, goods=0,
        paused=1, workers_drained=True, native_inflight=False, capture_outstanding=False,
        main_ticket_outstanding=False, daemon_requests_outstanding=0,
        events=[pause], captures=captures, motion_references=[], inputs=0, moves=0,
        x=0, y=0, restarts=0, door_changes=0, terrain_changes=0, lead_confirmed=0,
        started_ns=100, accepted_started_ns=90, walk_started_ns=500, ended_ns=2100,
        first_move_ns=0, last_capture_id=2, last_capture_start_ns=2000,
        last_capture_end_ns=2100, last_completed_id=1, live_completed_prefix=1,
        current_command_id=0, capture_count=2, analyzed_capture_count=2,
        accepted_frames=2, discarded_frames=0, retained_image_count=2,
        evicted_capture_count=0, referenced_capture_ids=[1, 2], missing_capture_ids=[],
        capture_failure=None, dispatch_failure=None, beat_period_ns=520000000,
        input_time_semantics='synth_call_interval_not_game_receipt_timestamp')
    record = dict(schema='ngg2-host-v1', revision='native-walk-v12', run_id='a'*32,
        profile='normal-1-1-v1', state='stopped', resolved=True, start_attempted=True,
        cancel_attempted=False, cancel_attempts=0, cancel_confirmed=False,
        stop_reason=None, native_state='stopped', native_report=native,
        images=images, result_metadata=dict(retained_images=2, omitted_image_count=0,
            exported_capture_ids=[1, 2], exported_images=2, api_version='1.98.14-ngg2'),
        host_clock_domain='python.monotonic_ns', native_clock_domain='device.monotonic_ns',
        events=[], events_dropped=0,
        image_export=dict(export_id='c'*32, images=deepcopy(images),
            total_bytes=sum(x['bytes'] for x in images), chunk_bytes=65536,
            offsets=[x['bytes'] for x in images], prefix_sha256=[x['sha256'] for x in images]))
    return record, pixels


def write_recording(path, record, pixels, *, extra=(), active=None):
    root = 'test-procedural'
    folder = f'{root}/native-{record["run_id"]}'
    raw = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(root+'/active.json', raw if active is None else active)
        archive.writestr(folder+'/report.json', raw)
        for name, data in pixels.items():
            archive.writestr(folder+'/images/'+name, data)
        for name, data in extra:
            archive.writestr(name, data)


def replace_png(record, pixels, capture_id, raw):
    item = next(row for row in record['images'] if row['capture_id'] == capture_id)
    pixels[item['name']] = raw
    item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    checkpoint = record['image_export']
    checkpoint.update(images=deepcopy(record['images']),
        total_bytes=sum(row['bytes'] for row in record['images']),
        offsets=[row['bytes'] for row in record['images']],
        prefix_sha256=[row['sha256'] for row in record['images']])


def goods_recording():
    record, pixels = procedural_recording()
    replace_png(record, pixels, 1, procedural_png(goods=True))
    record['native_report']['goods'] = 1
    return record, pixels


def inflight_goods_recording():
    """Explicit procedural lifecycle: goods during RESUME, then stable cleanup."""
    record, _ = procedural_recording()
    native = record['native_report']
    capture_template, image_template = native['captures'][0], record['images'][0]
    captures, images, pixels = [], [], {}
    for number, start, prefix, inflight in ((1,400,0,False), (2,1000,0,True),
                                           (3,2000,1,False), (4,3000,2,False)):
        capture = {key:(value+start-1000 if key.endswith('_ns') else value)
                   for key,value in capture_template.items()}
        capture.update(id=number, completed_prefix_start=prefix, completed_prefix_end=prefix,
                       inflight_start=inflight, inflight_end=inflight, stable=not inflight)
        item = deepcopy(image_template)
        item.update(name=f'capture-{number:06d}.png', capture_id=number,
                    capture_start_ns=capture['start_ns'], capture_end_ns=capture['end_ns'],
                    decode_end_ns=capture['decode_end_ns'], completed_prefix=prefix,
                    completed_prefix_start=prefix, completed_prefix_end=prefix,
                    inflight_start=inflight, inflight_end=inflight, stable_prefix=not inflight)
        raw = procedural_png(paused=number==4, goods=number==2)
        item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        captures.append(capture); images.append(item); pixels[item['name']] = raw
    pause = deepcopy(native['events'][0])
    resume = dict(pause, id=1, kind=1, source_capture_id=1, source_start_ns=400,
                  observed_capture_id=3, begin_ns=800, end_ns=1600, not_before_ns=750,
                  deadline_ns=1750)
    pause.update(id=2, source_capture_id=3, source_start_ns=2000, observed_capture_id=4,
                 begin_ns=2800, end_ns=2900, not_before_ns=2700, deadline_ns=3700)
    native.update(goods=1, events=[resume,pause], captures=captures, ended_ns=3100,
        device_now_ns=4000, last_capture_id=4, last_capture_start_ns=3000, last_capture_end_ns=3100,
        last_completed_id=2, live_completed_prefix=2, capture_count=4, analyzed_capture_count=4,
        accepted_frames=3, discarded_frames=1, retained_image_count=4, referenced_capture_ids=[1,2,3,4])
    record['images'] = images
    record['result_metadata'].update(retained_images=4, exported_images=4, exported_capture_ids=[1,2,3,4])
    replace_png(record, pixels, 1, pixels[images[0]['name']])
    return record, pixels


class DeviceRecordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = audit.NativeCore()
        cls.addClassCleanup(cls.core.close)

    def evaluate(self, record=None, pixels=None, **kwargs):
        if record is None:
            record, pixels = procedural_recording()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'procedural.zip'
            write_recording(path, record, pixels, **kwargs)
            return audit.evaluate_recording(path, core=self.core)

    def test_report_only_numeric_type_coercion_is_invalid(self):
        original, pixels = goods_recording()
        active = json.dumps(original, sort_keys=True, separators=(',', ':')).encode()
        for forged in (True, 1.0):
            with self.subTest(forged=repr(forged)):
                report = deepcopy(original)
                report['native_report']['goods'] = forged
                result = self.evaluate(report, pixels, active=active)
                self.assertEqual('invalid', result['integrity']['status'])
                self.assertEqual(2, audit.exit_code(result))

    def test_non_object_result_metadata_is_invalid_without_traceback(self):
        for malformed in ([], None):
            with self.subTest(metadata=repr(malformed)):
                record, pixels = procedural_recording()
                record['result_metadata'] = malformed
                result, caught = None, None
                try:
                    result = self.evaluate(record, pixels)
                except Exception as error:
                    caught = type(error).__name__ + ': ' + str(error)
                self.assertIsNone(caught, 'invalid input must return an evaluation result')
                self.assertEqual('invalid', result['integrity']['status'])
                self.assertEqual(2, audit.exit_code(result))
                with tempfile.TemporaryDirectory() as folder:
                    path = Path(folder)/'invalid.zip'
                    write_recording(path, record, pixels)
                    command = subprocess.run([sys.executable, str(audit.__file__), str(path)],
                                             capture_output=True, text=True)
                    self.assertEqual(2, command.returncode)
                    self.assertNotIn('Traceback', command.stderr)
                    self.assertEqual('invalid', json.loads(command.stdout)['integrity']['status'])

    def test_completed_recording_without_goods_is_failed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'procedural.zip'
            write_recording(path, *procedural_recording())
            result = audit.evaluate_recording(path)
            self.assertEqual('fail', result['recorded_milestone']['status'])
            self.assertEqual(1, audit.exit_code(result))

    def test_procedural_visible_goods_and_confirmed_pause_pass_bounded_milestone(self):
        result = self.evaluate(*goods_recording())
        self.assertEqual('pass', result['integrity']['status'])
        self.assertEqual('pass', result['recorded_milestone']['status'])
        self.assertEqual([1], result['recorded_milestone']['goods_capture_ids'])
        self.assertEqual([2], result['recorded_milestone']['pause_capture_ids'])
        self.assertEqual(0, audit.exit_code(result))
        self.assertFalse(result['coverage']['full_controller_replay'])
        self.assertFalse(result['coverage']['live_game_e2e'])

    def test_inflight_goods_latches_but_does_not_authorize_navigation_or_motion(self):
        result = self.evaluate(*inflight_goods_recording())
        self.assertEqual('pass', result['recorded_milestone']['status'])
        self.assertEqual([2], result['recorded_milestone']['goods_capture_ids'])
        self.assertEqual([], result['c_partial_evaluation']['motions'])
        self.assertEqual([], result['c_partial_evaluation']['navigation'])

    def test_goods_flag_without_retained_visible_goods_is_unknown(self):
        record, pixels = procedural_recording()
        record['native_report']['goods'] = 1
        result = self.evaluate(record, pixels)
        self.assertEqual('pass', result['integrity']['status'])
        self.assertEqual('unknown', result['recorded_milestone']['status'])
        self.assertEqual(2, audit.exit_code(result))

    def test_contradictory_goods_and_incomplete_final_input_history_are_unknown(self):
        for mutation in ('goods','inputs','last_ack','live_prefix','ended'):
            with self.subTest(mutation=mutation):
                record,pixels = goods_recording()
                key,value = {'goods':('goods',0), 'inputs':('inputs',1),
                    'last_ack':('last_completed_id',0), 'live_prefix':('live_completed_prefix',0),
                    'ended':('ended_ns',1800)}[mutation]
                record['native_report'][key] = value
                result = self.evaluate(record,pixels)
                self.assertEqual('unknown',result['recorded_milestone']['status'])
                self.assertEqual(2,audit.exit_code(result))

    def test_stale_or_unobserved_goods_png_does_not_prove_latched_goods(self):
        record,pixels = goods_recording()
        native = record['native_report']
        native['captures'][0].update(observe_start_ns=3_000_001_000, observe_end_ns=3_000_001_100)
        native['events'][0].update(begin_ns=4_000_000_000, end_ns=4_000_000_100)
        delta = 5_000_000_000 - 2000
        for key in native['captures'][1]:
            if key.endswith('_ns'): native['captures'][1][key] += delta
        for key in ('capture_start_ns','capture_end_ns','decode_end_ns'):
            record['images'][1][key] += delta
        native.update(device_now_ns=6_000_000_000, ended_ns=5_000_000_100,
                      last_capture_start_ns=5_000_000_000, last_capture_end_ns=5_000_000_100)
        record['image_export']['images'] = deepcopy(record['images'])
        result = self.evaluate(record,pixels)
        self.assertEqual('pass',result['integrity']['status'])
        self.assertEqual('unknown',result['recorded_milestone']['status'])
        self.assertEqual([],result['recorded_milestone']['goods_capture_ids'])
        self.assertEqual(2,audit.exit_code(result))
        del native['captures'][0]['observe_start_ns']
        self.assertEqual(2,audit.exit_code(self.evaluate(record,pixels)))

    def test_proven_not_sent_after_begin_does_not_create_unknown_input(self):
        record,pixels = procedural_recording()
        event = deepcopy(record['native_report']['events'][0])
        event.update(id=2,kind=4,outcome=3,source_capture_id=2,source_start_ns=2000,
                     observed_capture_id=0,begin_ns=2330,end_ns=2340,direction=1)
        record['native_report']['events'].append(event)
        record['native_report']['ended_ns'] = 2340
        result = self.evaluate(record,pixels)
        self.assertEqual('pass',result['integrity']['status'])
        self.assertEqual('fail',result['recorded_milestone']['status'])

    def test_resolved_is_not_completed_or_known_input(self):
        for field, value in (('terminal',0), ('workers_drained',False), ('input_state',4),
                             ('native_inflight',True), ('capture_outstanding',True),
                             ('main_ticket_outstanding',True), ('daemon_requests_outstanding',1)):
            with self.subTest(field=field):
                record, pixels = goods_recording()
                record['native_report'][field] = value
                result = self.evaluate(record, pixels)
                self.assertEqual('unknown', result['recorded_milestone']['status'])
                self.assertEqual(2, audit.exit_code(result))

    def test_final_pause_requires_post_ack_stable_matching_prefix_png(self):
        for mutation in ('early','inflight','prefix','not_pause'):
            with self.subTest(mutation=mutation):
                record, pixels = goods_recording()
                native = record['native_report']
                capture, image = native['captures'][1], record['images'][1]
                if mutation == 'early':
                    native['events'][0]['end_ns'] = 2050
                elif mutation == 'inflight':
                    capture.update(stable=False, inflight_start=True, inflight_end=True)
                    image.update(stable_prefix=False, inflight_start=True, inflight_end=True)
                elif mutation == 'prefix':
                    capture.update(completed_prefix_start=0, completed_prefix_end=0)
                    image.update(completed_prefix=0, completed_prefix_start=0, completed_prefix_end=0)
                else:
                    replace_png(record, pixels, 2, procedural_png())
                record['image_export']['images'] = deepcopy(record['images'])
                result = self.evaluate(record, pixels)
                self.assertEqual('unknown', result['recorded_milestone']['status'])
                self.assertEqual(2, audit.exit_code(result))

    def test_valid_unretained_images_are_coverage_gaps(self):
        record, pixels = goods_recording()
        removed = record['images'].pop(0)
        pixels.pop(removed['name'])
        replace_png(record, pixels, 2, pixels[record['images'][0]['name']])
        result = self.evaluate(record, pixels)
        self.assertEqual('pass', result['integrity']['status'])
        self.assertEqual('unknown', result['recorded_milestone']['status'])
        self.assertEqual([1], result['coverage']['unretained_capture_ids'])

    def test_native_v13_and_literal_v12_journals_are_supported(self):
        for revision in ('native-walk-v12','native-walk-v13'):
            with self.subTest(revision=revision):
                record, pixels = procedural_recording()
                record['revision'] = revision
                self.assertEqual('pass', self.evaluate(record,pixels)['integrity']['status'])

    def test_zip_paths_duplicates_symlinks_extra_and_multiple_runs_are_invalid(self):
        symlink = zipfile.ZipInfo('test-procedural/link')
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        extras = ('../escape', '/absolute', 'C:/drive', 'test-procedural/../escape',
                  'test-procedural\\escape', 'test-procedural/./escape',
                  'test-procedural/active.json', 'test-procedural/native-'+('d'*32)+'/report.json',
                  'second/active.json', 'test-procedural/execute.py', symlink)
        for name in extras:
            with self.subTest(name=str(name)):
                result = self.evaluate(extra=[(name,b'not executed')])
                self.assertEqual('invalid', result['integrity']['status'])
                self.assertEqual(2, audit.exit_code(result))

    def test_zip_and_json_resource_limits_are_checked(self):
        for name, value in (('MAX_ZIP',1), ('MAX_ENTRIES',1), ('MAX_UNCOMPRESSED',1), ('MAX_JSON',1)):
            with self.subTest(limit=name), patch.object(audit,name,value):
                self.assertEqual(2, audit.exit_code(self.evaluate()))

    def test_strict_json_rejects_duplicates_nonfinite_depth_and_mismatch(self):
        record, pixels = procedural_recording()
        for active in (b'{"run_id":"'+b'a'*32+b'","run_id":"'+b'a'*32+b'"}',
                       b'{"x":NaN}', b'{"x":'+b'['*20+b'0'+b']'*20+b'}',
                       json.dumps(dict(record,run_id='d'*32)).encode()):
            with self.subTest(active=active[:40]):
                self.assertEqual(2, audit.exit_code(self.evaluate(record,pixels,active=active)))

    def test_png_digest_crc_iend_and_geometry_are_verified(self):
        for mutation in ('digest','crc','iend','geometry'):
            with self.subTest(mutation=mutation):
                record,pixels = procedural_recording()
                raw = pixels[record['images'][0]['name']]
                if mutation == 'digest':
                    pixels[record['images'][0]['name']] = raw+b'x'
                elif mutation == 'crc':
                    raw = raw[:29]+bytes([raw[29]^1])+raw[30:]
                    replace_png(record,pixels,1,raw)
                elif mutation == 'iend':
                    replace_png(record,pixels,1,raw+b'after IEND')
                else:
                    image = Image.new('RGB',(414,896))
                    stream = io.BytesIO(); image.save(stream,format='PNG')
                    replace_png(record,pixels,1,stream.getvalue())
                self.assertEqual(2,audit.exit_code(self.evaluate(record,pixels)))

    def test_capture_event_image_and_export_crosslinks_are_strict(self):
        for mutation in ('capture_time','capture_prefix','stable','image_join','duplicate_capture',
                         'duplicate_image','source','export_offset','export_digest'):
            with self.subTest(mutation=mutation):
                record,pixels = procedural_recording()
                native = record['native_report']
                if mutation == 'capture_time': native['captures'][0]['analysis_end_ns'] = 999
                elif mutation == 'capture_prefix': native['captures'][0]['completed_prefix_end'] = 77
                elif mutation == 'stable': native['captures'][0]['stable'] = False
                elif mutation == 'image_join': record['images'][0]['capture_start_ns'] += 1
                elif mutation == 'duplicate_capture': native['captures'][1]['id'] = 1
                elif mutation == 'duplicate_image': record['images'][1]['capture_id'] = 1
                elif mutation == 'source': native['events'][0]['source_start_ns'] += 1
                elif mutation == 'export_offset': record['image_export']['offsets'][0] = 0
                elif mutation == 'export_digest': record['image_export']['prefix_sha256'][0] = '0'*64
                if mutation in ('image_join','duplicate_image'):
                    record['image_export']['images'] = deepcopy(record['images'])
                self.assertEqual(2,audit.exit_code(self.evaluate(record,pixels)))

    def test_original_png_and_hud_reach_c_without_transformation(self):
        record,pixels = goods_recording()
        observed = []
        real = self.core.analyze
        def inspect(rgba):
            observed.append(rgba)
            return real(rgba)
        with patch.object(self.core,'analyze',side_effect=inspect):
            result = self.evaluate(record,pixels)
        self.assertEqual('pass',result['recorded_milestone']['status'])
        for index,item in enumerate(record['images']):
            with Image.open(io.BytesIO(pixels[item['name']])) as image:
                self.assertEqual(image.convert('RGBA').tobytes(),observed[index])

    def test_missing_compiler_keeps_goods_success_unknown_and_uses_no_network(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'procedural.zip'
            write_recording(path,*goods_recording())
            with patch.object(audit.subprocess,'run',side_effect=FileNotFoundError), \
                    patch('socket.socket',side_effect=AssertionError('network forbidden')):
                result = audit.evaluate_recording(path)
            self.assertEqual('pass',result['integrity']['status'])
            self.assertEqual('unavailable',result['c_partial_evaluation']['status'])
            self.assertEqual('unknown',result['recorded_milestone']['status'])
            self.assertEqual(2,audit.exit_code(result))

    def test_cli_reports_json_with_exit_zero_one_two(self):
        for fixture,code in ((goods_recording,0),(procedural_recording,1)):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'procedural.zip'
                write_recording(path,*fixture())
                run = subprocess.run([sys.executable,str(audit.ROOT/'tools/evaluate_device_recording.py'),str(path)],
                                     capture_output=True,text=True)
                self.assertEqual(code,run.returncode,run.stderr)
                self.assertEqual('pass',json.loads(run.stdout)['integrity']['status'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bad.zip'; path.write_bytes(b'bad archive')
            output = Path(folder)/'out.json'
            self.assertEqual(2,audit.main([str(path),'--output',str(output)]))
            self.assertEqual('invalid',json.loads(output.read_text())['integrity']['status'])

    def test_required_test054_recorded_failure_is_not_game_success(self):
        """Private known recording regression; never an unseen/live game E2E."""
        path = Path(os.environ.get('NECRO_TEST055_RECORDING_ZIP',
            '/tmp/codex-remote-attachments/01a1b13e-8e5b-732b-955c-6407d4e00082/'
            '6EDB1D81-6153-4D99-A61C-9FCA64B8EA83/1-test-054.zip'))
        self.assertTrue(path.is_file(),'required private TEST054 recording missing')
        self.assertEqual('15ae61c465bdabb99a34dabb2979abd43debfe586c323ecbf5337c7d48778a15',
                         hashlib.sha256(path.read_bytes()).hexdigest())
        result = audit.evaluate_recording(path,core=self.core)
        self.assertEqual('pass',result['integrity']['status'])
        self.assertEqual('fail',result['recorded_milestone']['status'])
        self.assertTrue(result['recorded_milestone']['safe_terminal'])
        self.assertEqual(1,audit.exit_code(result))
        self.assertEqual((65,11,54),tuple(result['coverage'][key] for key in
            ('capture_rows','retained_pngs','unretained_capture_count')))
        self.assertFalse(result['coverage']['full_controller_replay'])
        partial = result['c_partial_evaluation']
        self.assertEqual('evaluated',partial['status'])
        pairs = {(row['before'],row['after']):(row['kind'],row['dx'],row['dy']) for row in partial['motions']}
        self.assertEqual((0,0,0),pairs[60,68])
        self.assertEqual((1,0,1),pairs[60,69])
        self.assertEqual((2,0,0),pairs[69,70])
        decisions = {row['capture_id']:row for row in partial['navigation']}
        # TEST057 corrects reviewed floor pixels; this is the current analyzer's
        # decision, while the original report/motion and failed goal stay fixed.
        for capture_id,expected in ((69,(1,8,-4,0,1)),(70,(1,7,-4,0,1))):
            row = decisions[capture_id]
            self.assertEqual(expected,tuple(row['decision'][key] for key in
                ('direction','reason','target_x','target_y','obstacle')))
            self.assertEqual([0,1],row['position'])
            self.assertEqual({'0,0':1,'0,1':1},row['visits'])
            self.assertEqual(0,row['entrance']['valid'])
        self.assertEqual([dict(capture_id=capture,recorded_direction=direction,candidate_direction=1,
                               continuation='not_recorded',future_frame_used=False)
                          for capture,direction in ((60,4),(70,3))],partial['counterfactual_branches'])
        self.assertTrue(all(row['after'] not in (77,78,79) for row in partial['motions']))


if __name__ == '__main__':
    unittest.main()
