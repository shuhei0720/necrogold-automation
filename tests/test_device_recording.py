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

    def test_required_test057_partial_checkpoint_is_not_complete_export(self):
        """Received partial journal snapshot cannot certify arrival or recovery."""
        path=Path(os.environ.get('NECRO_TEST058_RECORDING_ZIP',
            '/tmp/codex-remote-attachments/01a1b13e-8e5b-732b-955c-6407d4e00082/'
            '719314C6-9D81-496A-ABA7-97F2CB2F31E3/1-test-057.zip'))
        self.assertTrue(path.is_file(),'required private TEST057 recording missing')
        self.assertEqual('f49e35e4ae1a3491c1af7e0fe4e0e0acbbc990b60ff0e3cc262cd904f3f197c1',
                         hashlib.sha256(path.read_bytes()).hexdigest())
        result=audit.evaluate_recording(path,core=self.core)
        self.assertEqual({'status':'invalid','reason':'active_report_mismatch'},result['integrity'])
        self.assertEqual('unknown',result['recorded_milestone']['status'])
        self.assertEqual('not_evaluated',result['c_partial_evaluation']['status'])
        self.assertFalse(result['coverage']['full_controller_replay'])
        self.assertFalse(result['coverage']['live_game_e2e'])
        self.assertEqual(2,audit.exit_code(result))

    def test_required_test058_complete_recording_is_not_goods_acceptance(self):
        """Private complete export proves a recorded failure, not game acceptance."""
        path = Path(os.environ.get('NECRO_TEST059_RECORDING_ZIP',
            '/tmp/codex-remote-attachments/01a1b13e-8e5b-732b-955c-6407d4e00082/'
            '52CCAA26-94AD-4EC8-8DAD-2654B6686716/1-test-058.zip'))
        run_id = 'ff55bc0398a64132a4efde046fd8dffe'
        digest = '5a10c1c76237e15133843d13231206157b43f1e66cc42873b2de9cbf8c70c369'
        self.assertTrue(path.is_file(), 'required private TEST058 recording missing')
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        result = audit.evaluate_recording(path, core=self.core)
        self.assertEqual(digest, result['source_zip_sha256'])
        self.assertEqual(run_id, result['run_id'])
        self.assertEqual('pass', result['integrity']['status'])
        self.assertEqual('fail', result['recorded_milestone']['status'])
        self.assertEqual('recorded_terminal_without_goods', result['recorded_milestone']['reason'])
        self.assertTrue(result['recorded_milestone']['safe_terminal'])
        self.assertEqual([], result['recorded_milestone']['goods_capture_ids'])
        self.assertEqual(1, audit.exit_code(result))
        self.assertEqual((48, 12, 36), tuple(result['coverage'][key] for key in
            ('capture_rows', 'retained_pngs', 'unretained_capture_count')))
        self.assertFalse(result['coverage']['full_controller_replay'])
        self.assertFalse(result['coverage']['live_game_e2e'])
        with zipfile.ZipFile(path) as archive:
            record = json.loads(archive.read(f'test-058/native-{run_id}/report.json'))
        native = record['native_report']
        self.assertTrue(record['resolved'])
        self.assertTrue(native['workers_drained'])
        self.assertEqual((2, 2, -2, 0, 0, 1, 9, 'late', 0, 0, 1, 0), tuple(native[key] for key in
            ('inputs', 'moves', 'x', 'y', 'goods', 'paused', 'reason', 'reason_name',
             'door_changes', 'terrain_changes', 'terminal', 'input_state')))
        acknowledged = [event for event in native['events'] if event['kind'] == 4 and event['outcome'] == 2]
        self.assertEqual([(3, 1, 1, -1, 0, 47), (4, 1, 1, -1, 0, 54)],
            [tuple(event[key] for key in ('id', 'direction', 'motion', 'dx', 'dy', 'observed_capture_id'))
             for event in acknowledged])
        partial = result['c_partial_evaluation']
        self.assertEqual('evaluated', partial['status'])
        self.assertFalse(partial['controller_replayed'])
        self.assertEqual([-2, 0], partial['reconstructed_final_position'])
        self.assertEqual([(3, 40, 47, 1, -1, 0), (4, 47, 54, 1, -1, 0)],
            [tuple(row[key] for key in ('command_id', 'before', 'after', 'direction', 'dx', 'dy'))
             for row in partial['motions'] if row['kind'] == 1])
        scenes = {row['capture_id']: row for row in partial['scenes']}
        self.assertEqual(12, len(scenes))
        self.assertTrue(all(row['goods'] == 0 for row in scenes.values()))
        self.assertEqual(1, scenes[61]['state'])


    def test_required_test059_incomplete_two_run_recording_is_unknown(self):
        """Original two-run/part archive is invalid, never repaired into a pass."""
        manifest = json.loads((audit.ROOT / 'tests/test060-fixtures.json').read_text())
        path = Path(os.environ.get('NECRO_TEST060_RECORDING_ZIP',
            '/tmp/codex-remote-attachments/01a1b13e-8e5b-732b-955c-6407d4e00082/'
            '99E1F628-13C9-45E6-9023-1567BACCC5E1/1-test-059.zip'))
        digest = '900b06ffcaecb973a3c97a9b794702ac031cdc5f40437558ee19844e434dce0b'
        self.assertTrue(path.is_file(), 'required private TEST059 recording missing')
        self.assertEqual((3723124, digest), (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()))
        self.assertEqual((digest, 3723124, 25), tuple(manifest[key] for key in
                         ('source_zip_sha256', 'source_zip_bytes', 'source_zip_entry_count')))
        expected = {'integrity': {'status': 'invalid', 'reason': 'unsupported_or_multiple_run_layout'},
                    'milestone_status': 'unknown', 'exit_code': 2,
                    'full_controller_replay': False, 'live_game_e2e': False}
        self.assertEqual(expected, manifest['strict_recording_expectation'])
        result = audit.evaluate_recording(path, core=self.core)
        self.assertEqual(expected['integrity'], result['integrity'])
        self.assertEqual('unknown', result['recorded_milestone']['status'])
        self.assertEqual('not_evaluated', result['c_partial_evaluation']['status'])
        self.assertFalse(result['coverage']['full_controller_replay'])
        self.assertFalse(result['coverage']['live_game_e2e'])
        self.assertEqual(2, audit.exit_code(result))
        cli = subprocess.run([sys.executable, str(audit.ROOT / 'tools/evaluate_device_recording.py'), str(path)],
                             text=True, capture_output=True, check=False)
        self.assertEqual(2, cli.returncode, cli.stderr)
        self.assertEqual(result, json.loads(cli.stdout))
        run_id = 'd411b59e938c40719be2c40ab4c77939'
        folder = f'test-059/native-{run_id}'
        scope = manifest['collection_scope']
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(25, len(archive.infolist()))
            self.assertIsNone(archive.testzip())
            reports = {name: archive.read(name) for name in archive.namelist() if name.endswith('/report.json')}
            self.assertEqual({f'test-059/native-{row["run_id"]}/report.json': row['sha256']
                              for row in manifest['source_reports']},
                             {name: hashlib.sha256(raw).hexdigest() for name, raw in reports.items()})
            current_raw = reports[folder + '/report.json']
            self.assertEqual(current_raw, archive.read('test-059/active.json'))
            self.assertEqual(manifest['active_report_sha256'], hashlib.sha256(current_raw).hexdigest())
            record = json.loads(current_raw)
            other = json.loads(reports['test-059/native-897534256fce4a81942f3f8b46a6a9f3/report.json'])
            self.assertEqual((20, 0, 0), tuple(other['native_report'][key] for key in ('reason', 'inputs', 'moves')))
            native = record['native_report']
            self.assertFalse(record['resolved'])
            self.assertEqual('host_deadline', record['stop_reason'])
            self.assertEqual((3, 3, 0, -3, 0, 1, 17, 'screen', 0, 0, 1, 0), tuple(native[key] for key in
                ('inputs', 'moves', 'x', 'y', 'goods', 'paused', 'reason', 'reason_name',
                 'door_changes', 'terrain_changes', 'terminal', 'input_state')))
            self.assertIsNone(native['dispatch_failure'])
            metadata = {row['capture_id']: row for row in record['images']}
            checkpoint = record['image_export']
            self.assertEqual((14, 16, 16), (len(metadata), len(checkpoint['images']),
                                           record['result_metadata']['exported_images']))
            self.assertEqual(scope['reported_exported_capture_ids'], record['result_metadata']['exported_capture_ids'])
            complete_files = [name for name in archive.namelist()
                              if name.startswith(folder+'/images/') and name.endswith('.png')]
            ids = sorted(int(Path(name).stem.split('-')[-1]) for name in complete_files)
            self.assertEqual(scope['complete_png_capture_ids'], ids)
            self.assertEqual(sorted(metadata), ids)
            self.assertEqual(scope['referenced_capture_ids'], native['referenced_capture_ids'])
            self.assertEqual([], native['missing_capture_ids'])
            self.assertEqual(scope['unavailable_original_capture_ids_for_full_replay'],
                             sorted({row['id'] for row in native['captures']}-set(ids)))
            captures = {row['id']: row for row in native['captures']}
            for entry in manifest['images']:
                cid = entry['capture_id']; row = metadata[cid]
                raw = archive.read(folder+'/images/'+row['name'])
                self.assertEqual((entry['bytes'], entry['sha256']),
                                 (len(raw), hashlib.sha256(raw).hexdigest()))
                self.assertEqual((entry['stable'], entry['completed_prefix']),
                                 (row['stable_prefix'], row['completed_prefix']))
                # Source times/prefixes are checked directly in the immutable
                # raw journal, never moved to make a partial recording valid.
                for image_key, capture_key in audit.IMAGE_JOIN:
                    self.assertEqual(row[image_key], captures[cid][capture_key])
            by_export = {row['capture_id']: (row, offset, prefix) for row, offset, prefix in
                         zip(checkpoint['images'], checkpoint['offsets'], checkpoint['prefix_sha256'])}
            self.assertEqual((0, hashlib.sha256(b'').hexdigest()), by_export[59][1:])
            self.assertNotIn(folder+'/images/capture-000059.png', archive.namelist())
            self.assertNotIn(folder+'/images/capture-000060.png', archive.namelist())
            part = scope['part_files'][0]
            part_raw = archive.read(folder+'/images/.parts/capture-000060.png.part')
            self.assertEqual((60, 67986, 'c85303904d94e2226782cac5a8fbd75c80774714e5f67d369f154048bd87529b', True),
                             (part['capture_id'], part['bytes'], part['sha256'], part['fully_downloaded_but_unfinalized']))
            self.assertEqual((part['bytes'], part['sha256']), (len(part_raw), hashlib.sha256(part_raw).hexdigest()))
            self.assertEqual((part['bytes'], part['sha256']), by_export[60][1:])
            acknowledged = [event for event in native['events'] if event['kind'] == 4 and event['outcome'] == 2]
            self.assertEqual([(3, 32, 40), (4, 40, 47), (6, 48, 54)],
                             [(row['id'], row['source_capture_id'], row['observed_capture_id']) for row in acknowledged])
            self.assertTrue(all((row['direction'], row['motion'], row['dx'], row['dy']) == (3, 1, 0, -1)
                                for row in acknowledged))
            reference = next(row for row in native['motion_references'] if row['command_id'] == 6)
            self.assertEqual((48, 47, 54, True, 0, True, 1, 47, 1), tuple(reference[key] for key in
                ('authority_capture_id', 'reference_capture_id', 'observed_capture_id',
                 'reference_eligible', 'primary_motion', 'fallback_attempted', 'fallback_motion',
                 'selected_capture_id', 'selected_motion')))
            unsent = next(row for row in native['events'] if row['id'] == 7)
            self.assertEqual((54, 3, 0, 17), tuple(unsent[key] for key in
                             ('source_capture_id', 'direction', 'begin_ns', 'reason')))
            change = next(row for row in native['scene_change_details'] if row['command_id'] == 7)
            self.assertEqual((54, 55, 11), tuple(change[key] for key in
                             ('source_capture_id', 'observed_capture_id', 'validation')))
            self.assertEqual(manifest['latest_scene_change']['changed_tiles'],
                             [[cell[key] for key in ('x', 'y', 'tile_before', 'tile_after')]
                              for cell in change['cells']])
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest(), 'raw ZIP must remain unchanged')


if __name__ == '__main__':
    unittest.main()
