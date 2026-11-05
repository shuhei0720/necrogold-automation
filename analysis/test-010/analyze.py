"""TEST-010の受領ZIPを変更せず検算し、公開可能な派生結果を出力する。

使い方:
  python3 analyze.py test-010.zip test-007.zip IMG_8534.png results.json
画像本文、接続先、ペアリング情報は出力しない。目視判定は別の試験記録に残す。
"""
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import sys
import zipfile

from PIL import Image

SPANS = {
    'request_prepare': ('request_start_ns', 'http_start_ns'),
    'http_roundtrip': ('http_start_ns', 'http_end_ns'),
    'envelope_auth': ('http_end_ns', 'decrypt_start_ns'),
    'decrypt': ('decrypt_start_ns', 'decrypt_end_ns'),
    'response_json': ('decrypt_end_ns', 'response_end_ns'),
    'image_base64': ('base64_start_ns', 'base64_end_ns'),
    'image_decode': ('decode_start_ns', 'decode_end_ns'),
    'image_inspect': ('decode_end_ns', 'inspect_end_ns'),
    'capture_to_inspected': ('request_start_ns', 'inspect_end_ns'),
    'raw_save': ('save_start_ns', 'save_end_ns'),
    'trial_total': ('trial_start_ns', 'trial_end_ns'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_report(path):
    with zipfile.ZipFile(path) as archive:
        files = archive.infolist()
        assert len(files) <= 50
        assert sum(f.file_size for f in files) <= 16 * 1024 * 1024
        assert len({f.filename for f in files}) == len(files)
        for f in files:
            name = PurePosixPath(f.filename)
            assert not name.is_absolute() and '..' not in name.parts
            assert f.file_size <= 4 * 1024 * 1024
        names = [f.filename for f in files if f.filename.endswith('/report.json')]
        assert len(names) == 1
        raw = archive.read(names[0])
        report = json.loads(raw)
        images = []
        for row in report['rows']:
            if 'raw_file' not in row:
                continue
            file_name = row['raw_file']
            assert PurePosixPath(file_name).name == file_name
            data = archive.read(str(PurePosixPath(names[0]).parent / file_name))
            meta = row['image']
            assert len(data) == meta['raw_bytes'] and sha(data) == meta['sha256']
            with Image.open(io.BytesIO(data)) as image:
                assert image.width * image.height <= 8_000_000
                image.load()
                size = [image.width, image.height]
                orientation = image.getexif().get(274, 1)
                assert size == [meta['pixel_width'], meta['pixel_height']]
                assert orientation == meta['exif_orientation']
                images.append({'file': file_name, 'trial': row['trial'], 'dimensions': size,
                               'format': image.format, 'exif_orientation': orientation,
                               'bytes': len(data), 'sha256': sha(data)})
    return report, {'file': Path(path).name, 'bytes': Path(path).stat().st_size,
                    'sha256': sha(Path(path).read_bytes()), 'report_path': names[0],
                    'report_sha256': sha(raw)}, images


def stats(values):
    values = sorted(values)
    return {'n': len(values), 'median_ms': round(statistics.median(values), 3),
            'p95_ms': round(values[math.ceil(len(values) * .95) - 1], 3)}


def groups(report):
    result = {}
    for name in dict.fromkeys(row['variant'] for row in report['rows']):
        rows = [r for r in report['rows'] if r['variant'] == name]
        complete = [r for r in rows if r['status'] == 'complete']
        durations = {}
        for key, (start, end) in SPANS.items():
            values = [(r['timings'][end] - r['timings'][start]) / 1e6 for r in complete
                      if start in r['timings'] and end in r['timings']]
            if values:
                durations[key] = stats(values)
        # 独立計算を元reportの集計と照合する。元report自体を書き換えない。
        assert durations == report['summary']['groups'][name]['success_only_timings']
        hashes = {}
        for row in complete:
            hashes.setdefault(row['image']['sha256'], []).append(row['trial'])
        result[name] = {'planned': len(rows), 'complete': len(complete),
                        'durations_ms': durations, 'hash_trials': hashes,
                        'dimensions': sorted({(r['image']['pixel_width'], r['image']['pixel_height']) for r in complete})}
    return result


def main():
    current, source, images = read_report(sys.argv[1])
    previous, old_source, _ = read_report(sys.argv[2])
    actual = groups(current)
    old = groups(previous)
    elapsed = (current['end_ns'] - current['start_ns']) / 1e6
    assert elapsed == current['summary']['elapsed_ms']
    assert len(current['rows']) == 12
    assert all(r['status'] == 'complete' for r in current['rows'])
    assert all(r['image']['metadata_issues'] == [] for r in current['rows'])
    assert all(r['image']['geometry_applied'] == 'none' for r in current['rows'])
    assert all(r['image']['reported_geometry']['geometry'] == 'image_size_v1' for r in current['rows'])
    assert all(r['image']['reported_geometry']['input_geometry_verified'] is False for r in current['rows'])
    comparison = {}
    for name, group in actual.items():
        before = old[name]['durations_ms']['capture_to_inspected']['median_ms']
        after = group['durations_ms']['capture_to_inspected']['median_ms']
        comparison[name] = {'test007_median_ms': before, 'test010_median_ms': after,
                            'median_change_percent': round((after / before - 1) * 100, 3)}
    screenshot = Path(sys.argv[3])
    result = {
        'test_id': 'TEST-010', 'source_archive': source,
        'terminal_image': {'file': screenshot.name, 'bytes': screenshot.stat().st_size,
                           'sha256': sha(screenshot.read_bytes())},
        'run': PurePosixPath(source['report_path']).parent.name,
        'start_time_jst': '2026-11-05T21:27:52+09:00',
        'start_time_source': 'directory timestamp; device clock accuracy unverified',
        'version': current['version'], 'crypto_engine': current['crypto_engine'],
        'delivered_client_commit': 'b07e0682e86140e623b436fa5747ba5d964f7e4f',
        'delivered_source_commit': 'ae91483e51f5c97d93f2da1eac7a6f99759c74aa',
        'device_source_hashes_received': False,
        'status': current['status'], 'worker': current['worker'],
        'counts': {k: current['summary'][k] for k in ('planned', 'started', 'complete', 'errors', 'interrupted', 'not_started')},
        'elapsed_ms': elapsed,
        'startup_before_first_event_ms': (current['events'][0]['start_ns'] - current['start_ns']) / 1e6,
        'groups': actual, 'saved_images_verified': images,
        'all_12_metadata_issues_empty': True, 'all_12_client_geometry_applied': 'none',
        'reported_geometry_first_row': current['rows'][0]['image']['reported_geometry'],
        'foreground_first': current['events'][0]['observation']['foreground'],
        'foreground_last': current['events'][-1]['observation']['foreground'],
        'input_authorized': current['input_authorized'],
        'gate': current['gate'], 'timer': current['timer'],
        'location_reader_start_reported': True, 'location_reader_stop_requested': True,
        'location_reader_stop_completed_verified': False,
        'comparison': {'source_archive': old_source, 'test007_elapsed_ms': previous['summary']['elapsed_ms'],
                       'elapsed_change_percent': round((elapsed / previous['summary']['elapsed_ms'] - 1) * 100, 3),
                       'capture_to_inspected': comparison},
        'limitations': [
            'Four completed trials per format; nearest-rank p95 is the maximum; no warmup excluded.',
            'Only three original images were saved; other nine raster metadata/hashes cannot replace visual inspection.',
            'Source-generated compressed images and sizes differ from TEST-007; separate runs do not isolate regression causality.',
            'capture_to_inspected ends before new metadata validation; trial_total includes that validation and selected raw saves.',
            'Trial/report checkpoints and startup overhead are included in elapsed; throughput is not fresh game frame rate.',
            'same_bytes_as_previous compares adjacent mixed formats, not same-format history; later same-format hashes repeat.',
            'Input geometry, capture timestamps, frame age, input cancellation, gameplay and human-faster performance remain unverified.'
        ],
    }
    Path(sys.argv[4]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'result': sys.argv[4], 'elapsed_ms': elapsed, 'comparison': comparison,
                      'verified_saved_images': len(images)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
