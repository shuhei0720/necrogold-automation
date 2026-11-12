"""Public procedural boundaries for local target semantics, not device accuracy."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from necroprobe import target_assessment as target

FEATURES = json.loads((Path(__file__).resolve().parents[1]/'necroprobe/target_ring_features.json').read_text())
WIDTH, HEIGHT = 896, 414


def shop(*, left=470, sign_y=120, icon=True, name=True, word_slot=1, dark=False, hud=False, extra_icon_slots=()):
    pixels = bytearray(bytes((12, 8, 7, 255))*(WIDTH*HEIGHT))
    def put(x, y, colour):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            pixels[4*(y*WIDTH+x):4*(y*WIDTH+x)+4] = bytes((*colour, 255))
    for cx in (left, left+72):
        for y in range(sign_y-14, sign_y+15):
            for x in range(cx-15, cx+15): put(x, y, (220, 210, 10))
    for slot in range(3):
        cx = left+36*slot
        for y in range(sign_y+31, sign_y+55):
            for x in range(cx-9, cx+9): put(x, y, (10, 170, 165))
        for y in range(sign_y+75, sign_y+84):
            for x in range(cx-4, cx+4): put(x, y, (245, 245, 245))
    sprite = FEATURES['icons'][1]
    for slot in ((1,) if icon else ())+tuple(extra_icon_slots):
        sx, sy = left+36*slot-18, sign_y+34
        for x, y, r, g, b in sprite['bright']: put(sx+x, sy+y, (r, g, b))
        for x, y in sprite['dark']: put(sx+x, sy+y, (0, 0, 0))
    if name:
        start = left+36*word_slot-42
        for y, row in enumerate(FEATURES['word']['rows_hex']):
            bits = int(row, 16)
            for x in range(84):
                if bits >> x & 1: put(start+x, sign_y+11+y, (245, 245, 245))
    if dark:
        for i in range(0, len(pixels), 4): pixels[i:i+3] = b'\x01\x01\x01'
    if hud:
        # A whole shop-like patch inside the actual lower-right HUD is excluded.
        shifted = bytearray(bytes((12, 8, 7, 255))*(WIDTH*HEIGHT))
        for y in range(90):
            for x in range(160):
                old = 4*((sign_y-15+y)*WIDTH+left-20+x)
                new = 4*((315+y)*WIDTH+720+x)
                shifted[new:new+4] = pixels[old:old+4]
        pixels = shifted
    return bytes(pixels)


def chunk(kind, body):
    return struct.pack('>I', len(body))+kind+body+struct.pack('>I', zlib.crc32(kind+body)&0xffffffff)


def png(pixels, filter_kind=0, *, width=WIDTH, height=HEIGHT, colour=6, interlace=0, raw_extra=b''):
    rows = []; prior = bytes(width*4)
    for y in range(height):
        row = pixels[y*width*4:(y+1)*width*4]
        filtered = bytearray(row)
        for i, value in enumerate(row):
            a = row[i-4] if i >= 4 else 0; b = prior[i]; c = prior[i-4] if i >= 4 else 0
            if filter_kind == 1: estimate = a
            elif filter_kind == 2: estimate = b
            elif filter_kind == 3: estimate = (a+b)//2
            elif filter_kind == 4:
                p = a+b-c; da, db, dc = abs(p-a), abs(p-b), abs(p-c)
                estimate = a if da <= db and da <= dc else b if db <= dc else c
            else: estimate = 0
            filtered[i] = (value-estimate)&255
        rows.append(bytes((filter_kind,))+filtered); prior = row
    header = struct.pack('>IIBBBBB', width, height, 8, colour, 0, 0, interlace)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', header)+chunk(b'IDAT', zlib.compress(b''.join(rows)+raw_extra))+chunk(b'IEND', b'')


def seed(base, data):
    run = 'a'*32; folder = base/('native-'+run); (folder/'images').mkdir(parents=True)
    item = dict(name='capture-000007.png', capture_id=7, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                capture_start_ns=100, capture_end_ns=200, completed_prefix=7, completed_prefix_start=7,
                completed_prefix_end=7, stable_prefix=True, inflight_start=False, inflight_end=False,
                format='png', pixel_width=896, pixel_height=414)
    record = dict(run_id=run, images=[item], native_report=dict(goods=1, paused=1, terminal=1, workers_drained=True,
                  events=[dict(id=7, kind=4, outcome=2, begin_ns=30, end_ns=80, source_capture_id=6, source_start_ns=10),
                          dict(id=8, kind=2, outcome=2, begin_ns=900, end_ns=1000, source_capture_id=7, source_start_ns=100)]))
    raw = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    (base/'active.json').write_bytes(raw); (folder/'report.json').write_bytes(raw)
    (folder/'images'/item['name']).write_bytes(data)
    return record, hashlib.sha256(raw).hexdigest(), folder


class TargetAssessment087Tests(unittest.TestCase):
    def test_same_slot_icon_and_name_on_complete_observed_shop_is_target(self):
        data = png(shop())
        self.assertEqual((896, 414), struct.unpack('>II', data[16:24]))
        self.assertEqual(239, sum(bin(int(row, 16)).count('1') for row in FEATURES['word']['rows_hex']))
        try:
            result = target.classify_png(data)
        except AttributeError as error:
            self.fail('Supported iSH Python must classify the complete shop without an unsupported integer API: '+str(error))
        self.assertEqual('target', result['outcome'], 'the two independently located same-slot witnesses must identify the target')
        self.assertGreaterEqual(result['slots'][1]['icon_score'], .88)
        self.assertGreaterEqual(result['word']['iou'], .82)
        self.assertEqual(1, result['word']['slot'])

    def test_icon_only_wrong_slot_name_only_dark_and_hud_preserve_uncertainty(self):
        for options in ({'name': False}, {'word_slot': 0}):
            with self.subTest(options=options):
                self.assertEqual('candidate', target.classify_png(png(shop(**options)))['outcome'])
        for options in ({'icon': False}, {'icon': False, 'name': False}, {'dark': True}, {'hud': True}):
            with self.subTest(options=options):
                self.assertEqual('unknown', target.classify_png(png(shop(**options)))['outcome'])
        self.assertEqual('target', target.classify_png(png(shop(left=250, sign_y=200)))['outcome'],
                         'run-specific shop coordinates are not product conditions')
        self.assertEqual('target', target.classify_png(png(shop(extra_icon_slots=(0,))))['outcome'],
                         'an ambiguous first icon must not hide a second slot with both strong witnesses')

    def test_all_png_filters_reconstruct_exact_original_opaque_rgba(self):
        pixels = shop(name=False)
        for kind in range(5):
            with self.subTest(filter=kind):
                self.assertEqual(pixels, target.decode_png(png(pixels, kind)))

    def test_png_crc_geometry_alpha_inflate_filters_trailing_and_cancellation_fail_closed(self):
        pixels = shop(); data = png(pixels)
        broken = bytearray(data); broken[-5] ^= 1
        alpha = bytearray(pixels); alpha[3] = 254
        split_idat = data[:33]+chunk(b'IDAT', b'')+chunk(b'tEXt', b'x')+data[33:]
        bad_type = data[:33]+chunk(b'te0t', b'')+data[33:]
        for invalid in (bytes(broken), data[:-1], data+b'x', png(pixels, 5), png(pixels, raw_extra=b'x'),
                        png(bytes(alpha)), b'x'*(512*1024+1), split_idat, bad_type):
            with self.subTest(length=len(invalid)):
                with self.assertRaises(target.AssessmentError): target.decode_png(invalid)
        for options in ({'width': 895}, {'colour': 2}, {'interlace': 1}):
            with self.subTest(options=options):
                with self.assertRaises(target.AssessmentError): target.decode_png(png(pixels, **options))
        with self.assertRaises(target.AssessmentError): target.classify_png(data, cancelled=lambda: True)
        calls = [0]
        def cancel_during_rows():
            calls[0] += 1
            return calls[0] > 4
        with self.assertRaises(target.AssessmentError): target.decode_png(data, cancelled=cancel_during_rows)

    def test_prepare_is_deterministic_atomic_and_keeps_closed_original_reports_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); record, report_sha, folder = seed(base, png(shop()))
            original = (base/'active.json').read_bytes()
            first = target.prepare_assessment(base, record, report_sha)
            sidecar = folder/'target-assessment.json'; before = sidecar.read_bytes()
            self.assertEqual('target', first['outcome'])
            self.assertEqual(first, target.prepare_assessment(base, record, report_sha))
            self.assertEqual(before, sidecar.read_bytes())
            self.assertEqual(original, (base/'active.json').read_bytes())
            self.assertEqual(original, (folder/'report.json').read_bytes())
            self.assertEqual(first, target.validate_assessment(first, record=record, report_sha=report_sha))
            self.assertEqual([7], [item['capture_id'] for item in first['sources']])
            self.assertFalse(list(folder.glob('*.part')))
            recovery = base/'link-recovery'
            recovering, recovering_sha, recovering_folder = seed(recovery, png(shop()))
            original_unlink = Path.unlink
            def fail_after_link(path, *args, **kwargs):
                if path.name == '.target-assessment.json.part': raise OSError('simulated unlink interruption')
                return original_unlink(path, *args, **kwargs)
            with patch.object(Path, 'unlink', fail_after_link):
                with self.assertRaises(OSError): target.prepare_assessment(recovery, recovering, recovering_sha)
            saved = recovering_folder/'target-assessment.json'
            partial = recovering_folder/'.target-assessment.json.part'
            before_recovery = saved.read_bytes(); self.assertEqual(before_recovery, partial.read_bytes())
            with patch.object(target, 'classify_png', side_effect=AssertionError('already saved evidence must not be classified again')):
                target.prepare_assessment(recovery, recovering, recovering_sha)
            self.assertEqual(before_recovery, saved.read_bytes())
            self.assertFalse(partial.exists(), 'a post-link interruption must not publish an extra .part file')
            for field, replacement in (('stable_prefix', False), ('inflight_start', True), ('inflight_end', True)):
                other = base/field
                unsafe, _, unsafe_folder = seed(other, png(shop()))
                unsafe['images'][0][field] = replacement
                raw = json.dumps(unsafe, sort_keys=True, separators=(',', ':')).encode()
                (other/'active.json').write_bytes(raw); (unsafe_folder/'report.json').write_bytes(raw)
                result = target.prepare_assessment(other, unsafe, hashlib.sha256(raw).hexdigest())
                self.assertEqual(('unknown', 'no_authority', []), (result['outcome'], result['reason'], result['sources']),
                                 'inflight/non-stable captures never become certified target evidence')
            for change in ('missing_prefix', 'boolean_prefix', 'fractional_prefix', 'missing_source_start',
                           'wrong_source_start', 'wrong_ack_prefix', 'ack_after_source', 'missing_ack'):
                other = base/change
                unsafe, _, unsafe_folder = seed(other, png(shop()))
                metadata = unsafe['images'][0]; events = unsafe['native_report']['events']
                if change == 'missing_prefix':
                    for key in ('completed_prefix', 'completed_prefix_start', 'completed_prefix_end'): metadata.pop(key)
                elif change in ('boolean_prefix', 'fractional_prefix'):
                    for key in ('completed_prefix', 'completed_prefix_start', 'completed_prefix_end'):
                        metadata[key] = True if change == 'boolean_prefix' else 7.0
                elif change == 'missing_source_start': events[-1].pop('source_start_ns')
                elif change == 'wrong_source_start': events[-1]['source_start_ns'] = 101
                elif change == 'wrong_ack_prefix': events[0]['id'] = 6
                elif change == 'ack_after_source': events[0]['end_ns'] = 101
                else: unsafe['native_report']['events'] = events[-1:]
                raw = json.dumps(unsafe, sort_keys=True, separators=(',', ':')).encode()
                (other/'active.json').write_bytes(raw); (unsafe_folder/'report.json').write_bytes(raw)
                result = target.prepare_assessment(other, unsafe, hashlib.sha256(raw).hexdigest())
                with self.subTest(change=change):
                    self.assertEqual(('unknown', 'no_authority', []), (result['outcome'], result['reason'], result['sources']),
                                     'target evidence requires explicit source time and prior ACK prefix, not missing-value equality')

    def test_sidecar_unknown_fields_foreign_identity_source_changes_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); record, report_sha, folder = seed(base, png(shop(name=False)))
            value = target.prepare_assessment(base, record, report_sha)
            for field, replacement in (('extra', 1), ('run_id', 'b'*32), ('report_sha256', '0'*64),
                                        ('features_sha256', '0'*64), ('outcome', 'none')):
                changed = deepcopy(value); changed[field] = replacement
                with self.subTest(field=field):
                    with self.assertRaises(target.AssessmentError): target.validate_assessment(changed, record=record, report_sha=report_sha)
            bad = deepcopy(value); bad['sources'][0]['sha256'] = '0'*64
            with self.assertRaises(target.AssessmentError): target.validate_assessment(bad, record=record, report_sha=report_sha)
            for change in ('icon_box', 'boolean_slot', 'fractional_capture', 'pending_proof'):
                bad = deepcopy(value); expected_record = deepcopy(record); expected_sha = report_sha
                if change == 'icon_box': bad['sources'][0]['slots'][0]['icon_box'] = [0, 0, 32, 28]
                elif change == 'boolean_slot': bad['sources'][0]['slots'][0]['slot'] = False
                elif change == 'fractional_capture':
                    bad['inputs'][0]['capture_id'] = 7.0; bad['sources'][0]['capture_id'] = 7.0
                else:
                    proof = dict(record['images'][0], name='capture-000006.png', capture_id=6,
                                 capture_start_ns=85, capture_end_ns=95)
                    expected_record['images'].append(proof)
                    expected_sha = hashlib.sha256(json.dumps(expected_record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                    bad['report_sha256'] = expected_sha
                    bad['inputs'] = [dict(role='authority', capture_id=7, sha256=record['images'][0]['sha256']),
                                     dict(role='proof', capture_id=6, sha256=proof['sha256'])]
                with self.subTest(change=change):
                    with self.assertRaises(target.AssessmentError): target.validate_assessment(bad, record=expected_record, report_sha=expected_sha)
            sidecar = folder/'target-assessment.json'; raw = sidecar.read_bytes(); sidecar.unlink()
            target_file = base/'operator-file'; target_file.write_bytes(raw); sidecar.symlink_to(target_file)
            with self.assertRaises(target.AssessmentError): target.prepare_assessment(base, record, report_sha)
            sidecar.unlink(); sidecar.write_bytes(raw)
            image = folder/'images'/'capture-000007.png'; image.write_bytes(png(shop()))
            with self.assertRaises(target.AssessmentError): target.prepare_assessment(base, record, report_sha)
