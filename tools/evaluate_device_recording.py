"""Evaluate one native recording ZIP locally, independently of live acceptance.

Archive contents are never executed. Only repository production C is compiled;
original PNG pixels, HUD, timestamps and prefixes are preserved.
"""
import argparse
import ctypes as C
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from necroprobe import native_walk
from necroprobe.validation import ProbeError, json_object

MAX_ZIP = 16 * 1024 * 1024
MAX_ENTRIES = 128
MAX_UNCOMPRESSED = 12 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
CAPTURE_FRESH_NS = 3_000_000_000  # Existing native source freshness bound.
CAPTURE_KEYS = ('id', 'start_ns', 'end_ns', 'decode_end_ns', 'analysis_start_ns',
                'analysis_end_ns', 'observe_start_ns', 'observe_end_ns',
                'completed_prefix_start', 'completed_prefix_end', 'inflight_start',
                'inflight_end', 'stable')
EVENT_KEYS = ('id', 'kind', 'outcome', 'direction', 'source_capture_id', 'source_start_ns',
              'observed_capture_id', 'begin_ns', 'end_ns', 'target_ns', 'not_before_ns',
              'deadline_ns', 'phase_sample_ns', 'ordinal', 'x', 'y', 'motion', 'dx', 'dy', 'reason')
IMAGE_JOIN = (('capture_start_ns', 'start_ns'), ('capture_end_ns', 'end_ns'),
              ('decode_end_ns', 'decode_end_ns'), ('completed_prefix_start', 'completed_prefix_start'),
              ('completed_prefix_end', 'completed_prefix_end'), ('stable_prefix', 'stable'),
              ('inflight_start', 'inflight_start'), ('inflight_end', 'inflight_end'))


def require(condition, code):
    if not condition:
        raise ProbeError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _png(raw):
    """Verify all chunk CRCs (including ancillary chunks) and exact IEND end."""
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'invalid_png_signature')
    offset, first = 8, True
    while offset + 12 <= len(raw):
        length = struct.unpack_from('>I', raw, offset)[0]
        kind = raw[offset+4:offset+8]
        end = offset + length + 12
        require(end <= len(raw), 'invalid_png_length')
        require(not first or (kind == b'IHDR' and length == 13), 'invalid_png_header')
        require(zlib.crc32(raw[offset+4:end-4]) & 0xffffffff
                == struct.unpack_from('>I', raw, end-4)[0], 'invalid_png_crc')
        first, offset = False, end
        if kind == b'IEND':
            require(length == 0 and offset == len(raw), 'invalid_png_end')
            return
    raise ProbeError('invalid_png_end')


def _archive(path):
    require(path.stat().st_size <= MAX_ZIP, 'zip_size_limit')
    with path.open('rb') as handle:
        raw = handle.read(MAX_ZIP + 1)
    require(len(raw) <= MAX_ZIP, 'zip_size_limit')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        require(0 < len(entries) <= MAX_ENTRIES, 'zip_entry_limit')
        require(sum(entry.file_size for entry in entries) <= MAX_UNCOMPRESSED,
                'zip_uncompressed_limit')
        names, files, directories = set(), {}, set()
        for entry in entries:
            name = entry.orig_filename
            parts = PurePosixPath(name).parts
            require(name and '\\' not in name and '\x00' not in name
                    and not name.startswith('/') and ':' not in name
                    and all(part not in ('.', '..') for part in parts)
                    and '/'.join(parts) == name.rstrip('/'), 'unsafe_zip_path')
            require(name.casefold() not in names, 'duplicate_zip_entry')
            names.add(name.casefold())
            mode = stat.S_IFMT(entry.external_attr >> 16)
            require(mode in (0, stat.S_IFREG, stat.S_IFDIR)
                    and (mode != stat.S_IFDIR or entry.is_dir())
                    and (mode != stat.S_IFREG or not entry.is_dir()), 'nonregular_zip_entry')
            require(not entry.flag_bits & 1 and entry.compress_type in
                    (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'unsupported_zip_encoding')
            if entry.is_dir():
                require(entry.file_size == 0 and entry.CRC == 0, 'invalid_zip_directory')
                directories.add(name)
            else:
                require(entry.file_size <= MAX_JSON, 'zip_member_limit')
                files[name] = entry
        active = [name for name in files if name.endswith('/active.json')]
        require(len(active) == 1 and len(PurePosixPath(active[0]).parts) == 2,
                'one_native_run_required')
        base = active[0].rsplit('/', 1)[0]
        active_raw = archive.read(files[active[0]])
        document = json_object(active_raw, MAX_JSON)
        run_id = document.get('run_id')
        require(native_walk._uuid(run_id), 'invalid_run_id')
        folder = base + '/native-' + run_id
        report_name = folder + '/report.json'
        require(report_name in files, 'native_report_missing')
        report_raw = archive.read(files[report_name])
        require(active_raw == report_raw, 'active_report_mismatch')
        require(isinstance(document.get('result_metadata'), dict), 'invalid_result_metadata')
        with tempfile.TemporaryDirectory(prefix='ngg2-recording-journal-') as temporary:
            location = Path(temporary)
            (location/'active.json').write_bytes(active_raw)
            record = native_walk._load(location)
        require(record['native_report'] is not None, 'native_report_missing')
        allowed = {active[0], report_name} | {folder+'/images/'+item['name'] for item in record['images']}
        require(set(files) == allowed, 'unsupported_or_multiple_run_layout')
        require(directories <= {base+'/', folder+'/', folder+'/images/', folder+'/images/.parts/'},
                'unsupported_or_multiple_run_layout')
        images = {}
        from necroprobe.capture import inspect_bytes
        for item in record['images']:
            data = archive.read(files[folder+'/images/'+item['name']])
            require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'image_digest_mismatch')
            _png(data)
            inspected, rgb = inspect_bytes(data, include_rgb=True)
            try:
                require(inspected['format'] == 'PNG' and inspected['exif_orientation'] == 1
                        and rgb.size == (896, 414), 'image_geometry_mismatch')
                images[item['capture_id']] = rgb.convert('RGBA').tobytes()
            finally:
                rgb.close()
        checkpoint = record.get('image_export')
        if checkpoint:
            require(checkpoint['images'] == record['images'], 'incomplete_image_export')
            require(checkpoint['offsets'] == [item['bytes'] for item in record['images']]
                    and checkpoint['prefix_sha256'] == [item['sha256'] for item in record['images']],
                    'incomplete_image_export')
    return record, images, sha(raw), sha(report_raw)


def _lineage(record, images):
    native = record['native_report']
    captures, events = native.get('captures', []), native.get('events', [])
    require(all(set(CAPTURE_KEYS) <= set(row) for row in captures), 'capture_fields_missing')
    require(all(set(EVENT_KEYS) <= set(row) for row in events), 'event_fields_missing')
    for rows in (captures, events):
        ids = [row['id'] for row in rows]
        require(ids == sorted(set(ids)) and all(value > 0 for value in ids), 'invalid_row_ids')
    by_id, commands = {row['id']:row for row in captures}, {row['id']:row for row in events}
    acknowledged = {0} | {row['id'] for row in events if row['outcome'] == 2 and row['begin_ns'] > 0}
    start, now = native.get('started_ns'), native['device_now_ns']
    require(type(start) is int and 0 < start <= now, 'run_time_missing')
    previous_start = previous_end = start - 1
    previous_prefix = 0
    for row in captures:
        require(start <= row['start_ns'] < row['end_ns'] <= row['observe_end_ns'] <= now
                and row['start_ns'] > previous_start and row['end_ns'] > previous_end, 'capture_time_lineage')
        before, after = row['completed_prefix_start'], row['completed_prefix_end']
        require(before in acknowledged and after in acknowledged and previous_prefix <= before <= after,
                'capture_prefix_lineage')
        require(row['stable'] == (before == after and not row['inflight_start'] and not row['inflight_end']),
                'capture_stability_mismatch')
        # Runtime publishes prefix just before recording event.end_ns. Do not
        # reconstruct that tiny publication interval from the later timestamp.
        require(all(prefix == 0 or commands[prefix]['begin_ns'] <= row[edge+'_ns']
                    for prefix, edge in ((before, 'start'), (after, 'end'))), 'future_capture_prefix')
        previous_start, previous_end, previous_prefix = row['start_ns'], row['end_ns'], after
    for row in events:
        require(row['kind'] in range(1, 5) and row['outcome'] in range(5)
                and row['motion'] in range(8) and row['direction'] in range(5), 'invalid_event_values')
        require(row['begin_ns'] == 0 or start <= row['begin_ns'] <= row['end_ns'] <= now,
                'event_time_lineage')
        require(row['outcome'] != 2 or row['begin_ns'] > 0, 'ack_without_begin')
        source = by_id.get(row['source_capture_id'])
        require(source is not None and source['start_ns'] == row['source_start_ns'], 'event_source_lineage')
        require(not row['begin_ns'] or source['observe_end_ns'] <= row['begin_ns'], 'future_event_source')
        if row['observed_capture_id']:
            require(row['observed_capture_id'] in by_id, 'event_observation_missing')
    ids = [item['capture_id'] for item in record['images']]
    require(len(set(ids)) == len(ids) == len(images), 'duplicate_image_capture')
    for item in record['images']:
        row = by_id.get(item['capture_id'])
        require(row is not None and all(item.get(left) == row[right] for left, right in IMAGE_JOIN)
                and item.get('completed_prefix') == row['completed_prefix_end'], 'image_capture_mismatch')
    for key in ('referenced_capture_ids', 'missing_capture_ids'):
        values = native.get(key, [])
        require(len(values) == len(set(values)) and all(value in by_id for value in values), 'invalid_reference_ids')
    for key in ('capture_count', 'analyzed_capture_count'):
        require(key not in native or native[key] >= len(captures), 'capture_count_mismatch')
    require('retained_image_count' not in native or native['retained_image_count'] >= len(images), 'image_count_mismatch')
    for change in native.get('scene_changes', []):
        require(change['command_id'] in commands and change['source_capture_id'] in by_id
                and change['observed_capture_id'] in by_id, 'scene_change_lineage')
    if native.get('last_capture_id') in by_id:
        last = by_id[native['last_capture_id']]
        require(native.get('last_capture_start_ns') == last['start_ns']
                and native.get('last_capture_end_ns') == last['end_ns'], 'last_capture_mismatch')
    return by_id, commands


class Scene(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32),
                *[(name, C.c_int32) for name in ('state', 'restart_label', 'gold_state', 'gold_peak', 'goods')],
                ('tiles', C.c_uint8 * 230), ('protected_cells', C.c_uint8 * 230),
                ('signature', C.c_uint8 * 23296), ('fingerprint', C.c_uint8 * 48),
                ('beat_valid', C.c_int32), ('beat_remaining', C.c_double),
                ('beat_spacing', C.c_double), ('beat_center', C.c_double)]


class Entrance(C.Structure):
    _fields_ = [(key, C.c_int32) for key in ('valid', 'x', 'y', 'direction')]


class Decision(C.Structure):
    _fields_ = [(key, C.c_int32) for key in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


class Motion(C.Structure):
    _fields_ = [(key, C.c_int32) for key in ('kind', 'dx', 'dy')]


def fields(value):
    return {key:getattr(value, key) for key, _ in value._fields_}


class NativeCore:
    """Production ABI adapter; archive code and compiler flags are ignored."""
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='ngg2-recording-core-')
        core = ROOT/'patches/loopctrl/ngg2'
        output = Path(self.directory.name)/'recording.so'
        try:
            self.sources = {name:sha((core/name).read_bytes()) for name in
                            ('NG2Core.h', 'NG2Perception.c', 'NG2Navigation.c', 'NG2Templates.h')}
            subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
                            '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                            str(core/'NG2Perception.c'), str(core/'NG2Navigation.c'),
                            '-lm', '-o', str(output)], check=True, capture_output=True, timeout=60)
            self.lib = C.CDLL(str(output))
        except (OSError, subprocess.SubprocessError):
            self.close()
            raise ProbeError('trusted_c_unavailable') from None
        self.lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(Scene)]
        self.lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32, C.POINTER(Motion)]
        self.lib.ng2_choose.argtypes = [C.POINTER(Scene), C.c_int32, C.c_int32,
                                      C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
        self.lib.ng2_entered_gate.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                            C.c_int32, C.c_int32, C.c_int32, C.POINTER(Entrance)]

    def close(self):
        self.directory.cleanup()

    def analyze(self, rgba):
        scene = Scene()
        require(self.lib.ng2_analyze_rgba(rgba, len(rgba), 3584, C.byref(scene)) == 0
                and scene.abi_version == 1 and scene.struct_size == C.sizeof(Scene), 'trusted_c_analysis_failed')
        return scene

    def motion(self, before, after, direction):
        result = Motion()
        require(self.lib.ng2_motion(C.byref(before), C.byref(after), direction, C.byref(result)) == 1,
                'trusted_c_motion_failed')
        return fields(result)

    def choose(self, scene, position, visits, entrance):
        result = Decision()
        status = self.lib.ng2_choose(C.byref(scene), *position, visits, len(visits), C.byref(entrance), C.byref(result))
        return dict(fields(result), return_value=status)

    def entered_gate(self, before, after, direction, position, motion):
        result = Entrance()
        self.lib.ng2_entered_gate(C.byref(before), C.byref(after), direction, *position, motion, C.byref(result))
        return result


def _stable(row, prefix=None):
    return row['stable'] and (prefix is None or row['completed_prefix_end'] == prefix)


def _partial(record, captures, commands, scenes, core):
    native = record['native_report']
    motions, navigation, branches = [], [], []
    position, entrance, previous_ack = [0, 0], Entrance(), 0
    visits = (C.c_uint16 * 1089)()
    visits[16*33+16] = 1
    reconstructable = (list(commands) == list(range(1, len(commands)+1)) and native.get('restarts') == 0)
    # Origin/visits are the Controller create contract. Any unverified actual
    # move disables subsequent Nav evaluation rather than guessing its state.
    for event in commands.values():
        before_id, after_id = event['source_capture_id'], event['observed_capture_id']
        source = captures[before_id]
        state_known = reconstructable and before_id in scenes and _stable(source, previous_ack)
        if event['kind'] == 4 and state_known:
            state = dict(position=list(position), visits={f'{i%33-16},{i//33-16}':v for i,v in enumerate(visits) if v},
                         entrance=fields(entrance))
            navigation.append(dict(command_id=event['id'], capture_id=before_id, **state,
                                   decision=core.choose(scenes[before_id], position, visits, entrance)))
            for change in native.get('scene_changes', []):
                latest_id = change['observed_capture_id']
                if (change['command_id'] != event['id'] or latest_id not in scenes
                        or change['source_capture_id'] != before_id or not _stable(captures[latest_id], previous_ack)):
                    continue
                choice = core.choose(scenes[latest_id], position, visits, entrance)
                motion = core.motion(scenes[before_id], scenes[latest_id], event['direction'])
                motions.append(dict(command_id=event['id'], before=before_id, after=latest_id,
                                    direction=event['direction'], context='pre_send_same_prefix', **motion))
                navigation.append(dict(command_id=event['id'], capture_id=latest_id, **state, decision=choice))
                if choice['direction'] and choice['direction'] != event['direction']:
                    branches.append(dict(capture_id=latest_id, recorded_direction=event['direction'],
                        candidate_direction=choice['direction'], continuation='not_recorded', future_frame_used=False))
        if event['kind'] == 4 and event['outcome'] == 2:
            candidates = []
            if before_id in scenes and _stable(source, previous_ack):
                for capture_id, row in captures.items():
                    if (capture_id not in scenes or not before_id < capture_id <= after_id
                            or not _stable(row, event['id'])
                            or row['start_ns'] < max(event['end_ns'], event['target_ns']+80_000_000)):
                        continue
                    motion = core.motion(scenes[before_id], scenes[capture_id], event['direction'])
                    motions.append(dict(command_id=event['id'], before=before_id, after=capture_id,
                        direction=event['direction'], context='ack_lower_bound_only', **motion))
                    if capture_id == after_id:
                        candidates.append(motion)
            expected = dict(kind=event['motion'], dx=event['dx'], dy=event['dy'])
            if not state_known or candidates != [expected] or event['motion'] not in (1, 2, 3, 4):
                reconstructable = False
            elif event['motion'] == 1:
                new = [position[0]+event['dx'], position[1]+event['dy']]
                if any(abs(value) > 16 for value in new):
                    reconstructable = False
                else:
                    entered = core.entered_gate(scenes[before_id], scenes[after_id], event['direction'], position, 1)
                    if entered.valid:
                        entrance = entered
                    position = new
                    visits[(position[1]+16)*33+position[0]+16] += 1
        elif event['kind'] == 4 and event['outcome'] not in (2, 3):
            reconstructable = False
        if event['outcome'] == 2:
            previous_ack = event['id']
    return dict(status='evaluated', scope='original_png_production_c_partial_regression',
        scenes=[dict(capture_id=item['capture_id'], state=scenes[item['capture_id']].state,
                     goods=scenes[item['capture_id']].goods, png_sha256=item['sha256']) for item in record['images']],
        motions=motions, navigation=navigation, counterfactual_branches=branches,
        source_sha256=core.sources, raster_transform='none; original HUD preserved',
        temporal_limit='ACK lower bound only; original frozen motion horizons/model history are not serialized',
        reconstructed_final_position=position if reconstructable else None, controller_replayed=False)


def _milestone(record, captures, commands, scenes):
    native = record['native_report']
    ack_ids = [event['id'] for event in commands.values() if event['outcome'] == 2]
    final_ack = ack_ids[-1] if ack_ids else 0
    history_complete = (list(commands) == list(range(1, len(commands)+1))
        and native.get('inputs') == sum(event['kind'] == 4 and event['outcome'] in (2,4)
                                       for event in commands.values())
        and native.get('last_completed_id') == native.get('live_completed_prefix') == final_ack)
    safe = (record['resolved'] and record['state'] in native_walk.TERMINAL
            and record['native_state'] in native_walk.TERMINAL and native.get('terminal') == 1
            and native.get('workers_drained') is True and native.get('input_state') == 0
            and native.get('native_inflight') is False and native.get('capture_outstanding') is False
            and native.get('main_ticket_outstanding') is False and native.get('daemon_requests_outstanding') == 0
            and all(event['outcome'] in (2, 3) for event in commands.values()) and history_complete
            and native.get('started_ns', 0) <= native.get('ended_ns', 0) <= native['device_now_ns']
            and max([event['end_ns'] for event in commands.values()]+[0]) <= native.get('ended_ns', 0))
    result = dict(goal='goods_visible_and_paused', status='unknown', safe_terminal=safe,
                  goods_capture_ids=[], pause_capture_ids=[],
                  scope='recorded milestone only; item/ring identification and whole-game acceptance are not evaluated')
    if not safe:
        result['reason'] = 'unfinished_or_unknown_input'
    elif native.get('goods') == 0:
        if any(scene.state == 2 and scene.goods == 2 for scene in scenes.values()):
            result['reason'] = 'recorded_goods_flag_and_c_pixels_disagree'
        else:
            result.update(status='fail', reason='recorded_terminal_without_goods')
    else:
        pauses = [event for event in commands.values() if event['kind'] == 2 and event['outcome'] == 2]
        pause = pauses[-1] if pauses else None
        if pause:
            last_other_begin = max([event['begin_ns'] for event in commands.values()
                                   if event['kind'] != 2] + [0])
            result['goods_capture_ids'] = [capture_id for capture_id, scene in scenes.items()
                if scene.state == 2 and scene.goods == 2
                and captures[capture_id]['observe_end_ns'] - captures[capture_id]['start_ns'] <= CAPTURE_FRESH_NS
                and last_other_begin <= captures[capture_id]['observe_end_ns'] <= pause['begin_ns']]
            # Goods latch permits inflight captures. Final PAUSE needs the
            # stronger stable post-ACK, matching-prefix evidence.
            result['pause_capture_ids'] = [capture_id for capture_id, scene in scenes.items()
                if scene.state == 1 and capture_id == pause['observed_capture_id']
                and pause['id'] == final_ack and native.get('last_capture_id') == capture_id
                and _stable(captures[capture_id], pause['id'])
                and pause['end_ns'] <= captures[capture_id]['start_ns']
                and captures[capture_id]['end_ns'] <= native.get('ended_ns', 0)]
        if native.get('goods') == 1 and native.get('paused') == 1 and result['goods_capture_ids'] and result['pause_capture_ids']:
            result.update(status='pass', reason='visible_goods_and_final_pause_verified')
        else:
            result['reason'] = 'retained_goods_or_final_pause_evidence_insufficient'
    return result


def evaluate_recording(path, *, core=None):
    result = dict(schema='necrogold-recording-evaluation-v1', integrity=dict(status='invalid'),
        recorded_milestone=dict(goal='goods_visible_and_paused', status='unknown'),
        c_partial_evaluation=dict(status='not_evaluated'), coverage=dict(full_controller_replay=False, live_game_e2e=False))
    owned = None
    try:
        record, images, digest, report_digest = _archive(Path(path))
        result.update(source_zip_sha256=digest, source_report_sha256=report_digest,
                      run_id=record['run_id'], client_revision=record['revision'])
        captures, commands = _lineage(record, images)
        native = record['native_report']
        result['integrity'] = dict(status='pass', checks='bounded ZIP/strict journal/PNG CRC+SHA/capture lineage/export bytes')
        unavailable = sorted(set(captures) - set(images))
        result['coverage'].update(capture_rows=len(captures), retained_pngs=len(images),
            unretained_capture_count=len(unavailable), unretained_capture_ids=unavailable,
            reported_missing_reference_ids=native.get('missing_capture_ids', []),
            missing_for_full_controller=['unretained original captures' if unavailable else 'no unretained rows',
                'full eight-sample fit/tracking history', 'initial epoch/model and frozen command motion horizons'],
            limitation='Changed candidate action continuation is not recorded. Pause images are never movement continuation.')
        scenes = {}
        try:
            if core is None:
                core = owned = NativeCore()
            scenes = {capture_id:core.analyze(rgba) for capture_id, rgba in images.items()}
            result['c_partial_evaluation'] = _partial(record, captures, commands, scenes, core)
        except ProbeError as error:
            result['c_partial_evaluation'] = dict(status='unavailable', reason=error.code)
        result['recorded_milestone'] = _milestone(record, captures, commands, scenes)
    except (ProbeError, OSError, ValueError, zipfile.BadZipFile, RuntimeError,
            EOFError, zlib.error, struct.error) as error:
        result['integrity'] = dict(status='invalid', reason=error.code if isinstance(error, ProbeError) else 'unreadable_recording')
    except ImportError:
        result['integrity'] = dict(status='unknown', reason='image_dependency_unavailable')
    finally:
        if owned:
            owned.close()
    return result


def exit_code(result):
    if result['integrity']['status'] != 'pass':
        return 2
    return {'pass':0, 'fail':1}.get(result['recorded_milestone']['status'], 2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('--goal', choices=['goods_visible_and_paused'], default='goods_visible_and_paused')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = evaluate_recording(args.recording)
    raw = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if args.output:
        args.output.write_text(raw)
    else:
        print(raw, end='')
    return exit_code(result)


if __name__ == '__main__':
    raise SystemExit(main())
