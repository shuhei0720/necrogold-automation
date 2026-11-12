"""Bounded local target semantics after the native run has stopped.

This module sends no RPC or input. Visibility, individual target identity and
device acceptance are distinct. A missing match is always unknown.
"""
from collections import deque
import errno
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import struct
import zlib

WIDTH, HEIGHT = 896, 414
FEATURE_SHA256 = '202322326d86f600b300713ca8572b592f3beb59ceff6e6f6e58ef9cb3b728b4'
CLASSIFIER = 'ring-icon-word-v1'
SCHEMA = 'ngg2-target-assessment-v1'
SIDECAR = 'target-assessment.json'
MAX_SIDECAR = 64*1024
HUD = ((0, 0, 143, 140), (663, 0, 896, 80), (717, 315, 896, 414),
       (405, 321, 485, 414), (0, 380, 896, 414), (429, 0, 465, 45), (866, 45, 896, 290))


class AssessmentError(OSError):
    """A fixed local integrity/cancellation reason; preserve the unpublished run."""


def _require(condition, code='target_invalid'):
    if not condition:
        raise AssessmentError(code)


def _check(cancelled):
    _require(not cancelled(), 'target_cancelled')


def decode_png(data, cancelled=lambda: False):
    """Strict original-size opaque RGBA8 PNG; bounded inflate and filters 0..4."""
    _check(cancelled)
    _require(type(data) is bytes and 8 <= len(data) <= 512*1024, 'target_png_limit')
    _require(data[:8] == b'\x89PNG\r\n\x1a\n', 'target_png_format')
    position = 8; compressed = bytearray(); seen = []; ended = False
    while position < len(data):
        _check(cancelled)
        _require(len(seen) < 64 and position+12 <= len(data), 'target_png_chunks')
        length = struct.unpack_from('>I', data, position)[0]
        kind = data[position+4:position+8]; end = position+12+length
        _require(end <= len(data), 'target_png_length')
        _require(all(65 <= c <= 90 or 97 <= c <= 122 for c in kind) and not kind[2]&32, 'target_png_chunk_name')
        body = data[position+8:end-4]
        _require(zlib.crc32(kind+body)&0xffffffff == struct.unpack_from('>I', data, end-4)[0], 'target_png_crc')
        if not seen:
            _require(kind == b'IHDR' and length == 13, 'target_png_header')
            _require(struct.unpack('>IIBBBBB', body) == (WIDTH, HEIGHT, 8, 6, 0, 0, 0), 'target_png_geometry')
        elif kind == b'IHDR':
            raise AssessmentError('target_png_header')
        if kind == b'IDAT':
            _require(not ended and (b'IDAT' not in seen or seen[-1] == b'IDAT'), 'target_png_order')
            compressed.extend(body)
        elif kind == b'IEND':
            _require(length == 0 and compressed and end == len(data), 'target_png_end')
            ended = True
        elif kind != b'IHDR':
            _require(kind[0]&32, 'target_png_critical')
        seen.append(kind); position = end
    _require(ended, 'target_png_end')
    expected = HEIGHT*(WIDTH*4+1)
    try:
        inflater = zlib.decompressobj()
        raw = inflater.decompress(compressed, expected+1)
    except zlib.error as exc:
        raise AssessmentError('target_png_deflate') from exc
    _require(len(raw) == expected and inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail,
             'target_png_inflate')
    result = bytearray(); prior = bytes(WIDTH*4); stride = WIDTH*4
    for y in range(HEIGHT):
        if not y % 8: _check(cancelled)
        offset = y*(stride+1); method = raw[offset]
        _require(method <= 4, 'target_png_filter')
        row = bytearray(raw[offset+1:offset+1+stride])
        if method == 1:
            for i in range(4, stride): row[i] = (row[i]+row[i-4])&255
        elif method == 2:
            row = bytearray((a+b)&255 for a, b in zip(row, prior))
        elif method in (3, 4):
            for i in range(stride):
                a = row[i-4] if i >= 4 else 0; b = prior[i]
                if method == 3: estimate = (a+b)//2
                else:
                    c = prior[i-4] if i >= 4 else 0; p = a+b-c
                    da, db, dc = abs(p-a), abs(p-b), abs(p-c)
                    estimate = a if da <= db and da <= dc else b if db <= dc else c
                row[i] = (row[i]+estimate)&255
        _require(row[3::4] == b'\xff'*WIDTH, 'target_png_alpha')
        result.extend(row); prior = row
    _check(cancelled)
    return bytes(result)


@lru_cache(maxsize=1)
def _feature_values(raw):
    _require(hashlib.sha256(raw).hexdigest() == FEATURE_SHA256, 'target_features_changed')
    value = json.loads(raw)
    _require(value['schema'] == 'ngg2-ring-features-v1' and value['word']['ink'] == 239, 'target_features_invalid')
    icons = []
    for sprite in value['icons']:
        bright = tuple(tuple(point) for point in sprite['bright']); dark = tuple(tuple(point) for point in sprite['dark'])
        intensities = tuple(sum(point[2:]) for point in bright)
        total = sum(intensities)
        icons.append((sprite['width'], sprite['height'], bright, dark, intensities,
                      sum(sum(c*c for c in point[2:]) for point in bright), total,
                      sum(v*v for v in intensities)-total*total/len(bright)))
    return tuple(icons), tuple(int(row, 16) for row in value['word']['rows_hex'])


def _features():
    raw = Path(__file__).with_name('target_ring_features.json').read_bytes()
    _require(len(raw) <= 64*1024, 'target_features_limit')
    return _feature_values(raw)


def _hud(x0, y0, x1, y1):
    return any(x0 < right and left < x1 and y0 < bottom and top < y1 for left, top, right, bottom in HUD)


def _observations(rgba, cancelled):
    white = []; signs = bytearray(WIDTH*HEIGHT)
    for y in range(HEIGHT):
        if not y % 8: _check(cancelled)
        bits = 0
        for x in range(WIDTH):
            at = 4*(y*WIDTH+x); r, g, b = rgba[at], rgba[at+1], rgba[at+2]
            if r > 140 and g > 140 and b > 140 and max(r, g, b)-min(r, g, b) < 40: bits |= 1 << x
            if r > 57 and g > r*865//1000 and g < min(255, (r*1050+999)//1000) and b < (g*240+999)//1000:
                if not _hud(x, y, x+1, y+1): signs[y*WIDTH+x] = 1
        white.append(bits)
    components = []
    for at in range(WIDTH*HEIGHT):
        if not signs[at]: continue
        _check(cancelled)
        signs[at] = 0; queue = deque((at,)); count = 0; x0 = WIDTH; y0 = HEIGHT; x1 = y1 = 0
        while queue:
            position = queue.popleft(); x, y = position % WIDTH, position // WIDTH; count += 1
            x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
            for other in (position-1 if x else -1, position+1 if x+1 < WIDTH else -1,
                          position-WIDTH if y else -1, position+WIDTH if y+1 < HEIGHT else -1):
                if other >= 0 and signs[other]: signs[other] = 0; queue.append(other)
            if not count % 1024: _check(cancelled)
        if count >= 150 and 18 <= x1-x0+1 <= 48 and 16 <= y1-y0+1 <= 40:
            components.append((count, (x0+x1+1)//2, (y0+y1+1)//2))
    rows = {}
    for count, cx, sy in sorted(components, reverse=True)[:12]:
        for left in (cx, cx-72):
            _check(cancelled)
            start = sy+69
            if left < 18 or left+72 >= 878 or start < 0 or start+20 >= HEIGHT or _hud(left-18, sy+24, left+90, start+20): continue
            counts = [[sum(bin((white[y] >> (left+36*slot-11))&((1 << 23)-1)).count('1')
                           for y in range(start+k, start+k+9)) for k in range(12)] for slot in range(3)]
            price = max(min(counts[slot][k] for slot in range(3)) for k in range(12))
            if price < 18: continue
            bright = []
            for slot in range(3):
                value = 0
                for y in range(sy+24, sy+66):
                    for x in range(left+36*slot-17, left+36*slot+18):
                        at = 4*(y*WIDTH+x)
                        value += (19595*rgba[at]+38470*rgba[at+1]+7471*rgba[at+2]+32768) >> 16 > 55
                bright.append(value)
            if min(bright) >= 24: rows[(left, sy)] = (price, count)
    return white, sorted(rows, key=lambda row: (-rows[row][0], -rows[row][1], row[1], row[0]))[:4]


def _icon(rgba, cx, sy, sprites, cancelled):
    best = 0.; box = [cx-16, sy+24, 33, 28]
    for width, height, bright, dark, reference, energy, target_sum, target_var in sprites:
        count = len(bright)
        for y in range(max(0, sy+24), min(HEIGHT-height, sy+57)+1):
            _check(cancelled)
            for x in range(max(0, cx-width//2-8), min(WIDTH-width, cx-width//2+8)+1):
                observed = []; dot = total = square = cross = 0
                for point, intensity in zip(bright, reference):
                    dx, dy, r, g, b = point; at = 4*((y+dy)*WIDTH+x+dx)
                    a, c, d = rgba[at], rgba[at+1], rgba[at+2]; v = a+c+d
                    observed.append((a, c, d)); dot += a*r+c*g+d*b
                    total += v; square += v*v; cross += v*intensity
                gain = min(1.30, max(.37, dot/energy))
                matches = sum(sum(abs(a-gain*b) for a, b in zip(pixel, point[2:])) < 3*(13+15*gain)
                              for pixel, point in zip(observed, bright))
                outline = 0
                for dx, dy in dark:
                    at = 4*((y+dy)*WIDTH+x+dx)
                    outline += rgba[at]+rgba[at+1]+rgba[at+2] < 144
                norm = math.sqrt(max(0, (square-total*total/count)*target_var))
                shape = max(0, (cross-total*target_sum/count)/max(norm, 9))
                score = (.55*matches/count+.45*shape)*(.80+.20*outline/len(dark))
                if score > best: best, box = score, [x, y, width, height]
    return round(min(1., best), 9), box


def _word(white, cx, sy, reference, slot, cancelled):
    mask = (1 << 84)-1; best = None
    for y in range(max(0, sy-20), min(HEIGHT-11, sy+35)+1):
        _check(cancelled)
        for x in range(max(0, cx-42-18), min(WIDTH-84, cx-42+18)+1):
            observed = [(white[y+dy] >> x)&mask for dy in range(11)]
            intersection = sum(bin(a&b).count('1') for a, b in zip(reference, observed))
            union = sum(bin(a|b).count('1') for a, b in zip(reference, observed))
            iou = intersection/max(union, 1); coverage = intersection/239
            if best is None or (iou, coverage) > (best['iou'], best['coverage']):
                best = dict(slot=slot, iou=iou, coverage=coverage, box=[x, y, 84, 11])
    best['iou'] = round(best['iou'], 9); best['coverage'] = round(best['coverage'], 9)
    return best


def _outcome(slots, word):
    maximum = max((item['icon_score'] for item in slots), default=0)
    if word and slots[word['slot']]['icon_score'] >= .88 and word['iou'] >= .82 and word['coverage'] >= .90:
        return 'target', 'icon_and_name'
    return ('candidate', 'icon_only') if maximum >= .80 else ('unknown', 'no_target_evidence')


def classify_png(data, cancelled=lambda: False):
    """Find three observed merchandise slots, then join icon/name in one slot."""
    rgba = decode_png(data, cancelled); sprites, reference = _features()
    white, rows = _observations(rgba, cancelled)
    best = dict(outcome='unknown', reason='no_complete_row', row=None, slots=[], word=None)
    for left, sy in rows:
        _check(cancelled); slots = []
        for slot in range(3):
            score, box = _icon(rgba, left+36*slot, sy, sprites, cancelled)
            slots.append(dict(slot=slot, icon_score=score, icon_box=box))
        words = [_word(white, left+36*slot, sy, reference, slot, cancelled)
                 for slot in range(3) if slots[slot]['icon_score'] >= .80]
        word = max(words, key=lambda item: (slots[item['slot']]['icon_score'] >= .88
                   and item['iou'] >= .82 and item['coverage'] >= .90,
                   item['iou'], item['coverage'], slots[item['slot']]['icon_score']), default=None)
        outcome, reason = _outcome(slots, word)
        value = dict(outcome=outcome, reason=reason, row=[left, sy], slots=slots, word=word)
        if (outcome == 'target' or best['row'] is None or
                max(item['icon_score'] for item in slots) > max(item['icon_score'] for item in best['slots'])): best = value
        if outcome == 'target': break
    _check(cancelled)
    return best


def _selected(record):
    report = record.get('native_report') or {}
    if not (report.get('goods') == 1 and report.get('paused') == 1 and report.get('terminal') == 1 and report.get('workers_drained') is True): return []
    def acknowledged(event):
        return (event.get('outcome') == 2 and type(event.get('id')) is int and event['id'] > 0
                and type(event.get('begin_ns')) is int and event['begin_ns'] > 0
                and type(event.get('end_ns')) is int and event['end_ns'] >= event['begin_ns'])
    events = report.get('events', [])
    pauses = [event for event in events if event.get('kind') == 2 and acknowledged(event)]
    if not pauses: return []
    pause = max(pauses, key=lambda event: event['id'])
    prior = [event for event in events if acknowledged(event) and event['id'] < pause['id']]
    if not prior or type(pause.get('source_start_ns')) is not int or pause['source_start_ns'] <= 0: return []
    previous = max(prior, key=lambda event: event['id'])
    def eligible(item):
        prefixes = [item.get(key) for key in ('completed_prefix', 'completed_prefix_start', 'completed_prefix_end')]
        start, end = item.get('capture_start_ns'), item.get('capture_end_ns')
        return (all(type(value) is int and value >= 0 and value == previous['id'] for value in prefixes)
                and item.get('stable_prefix') is True and item.get('inflight_start') is False and item.get('inflight_end') is False
                and type(start) is int and type(end) is int and previous['end_ns'] <= start < end <= pause['begin_ns'])
    images = [item for item in record['images'] if eligible(item)]
    authority = next((item for item in images if item['capture_id'] == pause.get('source_capture_id')), None)
    if authority is None or authority['capture_start_ns'] != pause['source_start_ns']: return []
    values = [('authority', authority)]
    proof = [item for item in images if item['capture_id'] < authority['capture_id']
             and item['completed_prefix'] == authority['completed_prefix'] and item['capture_end_ns'] <= authority['capture_start_ns']]
    if proof: values.append(('proof', max(proof, key=lambda item: item['capture_id'])))
    return [dict(role=role, capture_id=item['capture_id'], sha256=item['sha256']) for role, item in values]


def _keys(value, expected):
    _require(type(value) is dict and set(value) == set(expected), 'target_schema')


def validate_assessment(value, *, record, report_sha):
    """Validate the one allowed sidecar, its fixed feature identity and sources."""
    _keys(value, ('schema', 'classifier', 'features_sha256', 'run_id', 'report_sha256', 'outcome', 'reason', 'inputs', 'sources'))
    _require(value['schema'] == SCHEMA and value['classifier'] == CLASSIFIER and value['features_sha256'] == FEATURE_SHA256
             and value['run_id'] == record['run_id'] and value['report_sha256'] == report_sha, 'target_identity')
    selected = _selected(record)
    _require(type(value['inputs']) is list and value['inputs'] == selected
             and type(value['sources']) is list and len(value['sources']) <= len(selected), 'target_sources')
    for source in value['inputs']:
        _keys(source, ('capture_id', 'sha256', 'role'))
        _require(type(source['capture_id']) is int and source['capture_id'] > 0, 'target_sources')
    expected = ('outcome', 'reason', 'row', 'slots', 'word', 'capture_id', 'sha256', 'role')
    for index, source in enumerate(value['sources']):
        _keys(source, expected)
        _require(type(source['capture_id']) is int
                 and all(source[key] == selected[index][key] for key in ('capture_id', 'sha256', 'role')), 'target_sources')
        _require(type(source['slots']) is list and len(source['slots']) in (0, 3), 'target_slots')
        row = source['row']
        if row is None: _require(not source['slots'] and source['word'] is None and source['outcome'] == 'unknown' and source['reason'] == 'no_complete_row', 'target_result')
        else:
            _require(type(row) is list and len(row) == 2 and all(type(v) is int for v in row)
                     and 18 <= row[0] < 806 and 0 <= row[1] < HEIGHT-89 and len(source['slots']) == 3, 'target_row')
        for slot, item in enumerate(source['slots']):
            _keys(item, ('slot', 'icon_score', 'icon_box'))
            _require(type(item['slot']) is int and item['slot'] == slot and _score(item['icon_score']) and _box(item['icon_box']), 'target_icon')
            x, y, width, height = item['icon_box']; cx = row[0]+36*slot
            _require((width, height) in ((32, 28), (33, 28), (34, 29))
                     and cx-width//2-8 <= x <= cx-width//2+8 and row[1]+24 <= y <= row[1]+57, 'target_icon')
        word = source['word']
        if word is not None:
            _keys(word, ('slot', 'iou', 'coverage', 'box'))
            _require(type(word['slot']) is int and 0 <= word['slot'] < 3 and _score(word['iou']) and _score(word['coverage'])
                     and _box(word['box']) and word['box'][2:] == [84, 11]
                     and abs(word['box'][0]+42-row[0]-36*word['slot']) <= 18
                     and row[1]-20 <= word['box'][1] <= row[1]+35, 'target_word')
        if row is not None: _require((source['outcome'], source['reason']) == _outcome(source['slots'], word), 'target_result')
    if selected:
        _require(value['sources'], 'target_sources')
        count = 1 if value['sources'][0]['outcome'] == 'target' else len(selected)
        _require(len(value['sources']) == count, 'target_sources_incomplete')
    outcomes = [source['outcome'] for source in value['sources']]
    aggregate = 'target' if 'target' in outcomes else 'candidate' if 'candidate' in outcomes else 'unknown'
    reason = 'icon_and_name' if aggregate == 'target' else 'icon_only' if aggregate == 'candidate' else 'no_target_evidence' if selected else 'no_authority'
    _require((value['outcome'], value['reason']) == (aggregate, reason), 'target_result')
    _require(len(json.dumps(value, allow_nan=False).encode()) <= MAX_SIDECAR, 'target_sidecar_limit')
    return value


def _score(value):
    return type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1


def _box(value):
    return (type(value) is list and len(value) == 4 and all(type(v) is int for v in value)
            and value[0] >= 0 and value[1] >= 0 and value[2] > 0 and value[3] > 0
            and value[0]+value[2] <= WIDTH and value[1]+value[3] <= HEIGHT)


def _read(path, base, limit):
    _require(base in path.parents, 'target_path')
    for parent in (path, *path.parents):
        _require(not parent.is_symlink(), 'target_symlink')
        if parent == base: break
    info = path.stat()
    _require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'target_file_limit')
    handle = os.open(path, os.O_RDONLY|getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(handle, 'rb') as opened:
        current = os.fstat(opened.fileno())
        _require((current.st_dev, current.st_ino) == (info.st_dev, info.st_ino), 'target_file_changed')
        data = opened.read(limit+1)
    _require(len(data) <= limit, 'target_file_limit')
    return data


def prepare_assessment(base, record, report_sha, cancelled=lambda: False):
    """After the publication certificate, freeze a deterministic same-run sidecar."""
    _check(cancelled); base = Path(base); folder = base/('native-'+record['run_id'])
    active = _read(base/'active.json', base, 2*1024*1024)
    _require(hashlib.sha256(active).hexdigest() == report_sha and json.loads(active) == record
             and _read(folder/'report.json', base, 2*1024*1024) == active, 'target_report_changed')
    selected = _selected(record); images = {}
    for source in selected:
        _check(cancelled)
        name = 'capture-'+format(source['capture_id'], '06d')+'.png'
        item = next(item for item in record['images'] if item['capture_id'] == source['capture_id'])
        _require(item['name'] == name, 'target_image_name')
        data = _read(folder/'images'/name, base, 512*1024)
        _require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == source['sha256'], 'target_image_changed')
        images[source['capture_id']] = data
    path = folder/SIDECAR
    if path.exists() or path.is_symlink():
        raw = _read(path, base, MAX_SIDECAR)
        _require(len(raw) <= MAX_SIDECAR, 'target_sidecar_limit')
        value = json.loads(raw)
        validate_assessment(value, record=record, report_sha=report_sha)
        _require(raw == _encoded(value), 'target_sidecar_changed')
        partial = folder/('.'+SIDECAR+'.part')
        if partial.exists() or partial.is_symlink():
            _require(_read(partial, base, MAX_SIDECAR) == raw, 'target_partial_changed')
            _check(cancelled); partial.unlink(); _sync_folder(folder)
        return value
    sources = []
    for source in selected:
        _check(cancelled)
        sources.append(dict(source, **classify_png(images[source['capture_id']], cancelled)))
        if sources[-1]['outcome'] == 'target': break
    outcomes = [source['outcome'] for source in sources]
    outcome = 'target' if 'target' in outcomes else 'candidate' if 'candidate' in outcomes else 'unknown'
    reason = 'icon_and_name' if outcome == 'target' else 'icon_only' if outcome == 'candidate' else 'no_target_evidence' if selected else 'no_authority'
    value = dict(schema=SCHEMA, classifier=CLASSIFIER, features_sha256=FEATURE_SHA256, run_id=record['run_id'],
                 report_sha256=report_sha, outcome=outcome, reason=reason, inputs=selected, sources=sources)
    validate_assessment(value, record=record, report_sha=report_sha)
    raw = _encoded(value); part = folder/('.'+SIDECAR+'.part')
    _check(cancelled)
    if part.exists() or part.is_symlink():
        _read(part, base, MAX_SIDECAR); part.unlink()
    handle = os.open(part, os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(handle, 'wb') as opened:
        opened.write(raw); opened.flush(); os.fsync(opened.fileno())
    _check(cancelled)
    os.link(part, path); part.unlink()
    _sync_folder(folder)
    return value


def _sync_folder(folder):
    directory = os.open(folder, os.O_RDONLY)
    try:
        try: os.fsync(directory)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP, errno.ENOSYS): raise
    finally: os.close(directory)


def _encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
