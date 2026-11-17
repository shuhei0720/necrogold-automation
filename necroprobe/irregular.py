"""Closed, read-only validation of the explicitly selected irregular protocol.

These records describe native evidence; this module grants no game input and
does not turn an interrupted shop into a negative assessment.
"""
from .validation import ProbeError

KINDS = ('none', 'stalled', 'death')
STAGES = ('idle', 'quiesce', 'checkpoint', 'pause', 'death_continue', 'wait_menu',
          'restart_ready', 'wait_restart', 'outcome', 'held')
HELD = ('none', 'menu_unrecognized', 'deadline', 'storage', 'candidate',
        'unknown_input', 'invalid_ui', 'classification', 'baseline_unavailable',
        'limit', 'control_invalid')
STATUS_NUMBERS = ('abi_version', 'episodes', 'episode_id', 'trigger_capture_id',
    'before_capture_id', 'live_baseline_capture_id', 'prefix', 'trigger_ns',
    'parent_deadline_ns', 'proof_capture_id', 'continue_command_id',
    'continue_capture_id', 'pause_capture_id', 'restart_command_id',
    'next_floor_capture_id', 'durable_ns', 'continue_intent_ns',
    'continue_outcome_ns', 'restart_intent_ns', 'outcome_ns')
STATUS_KEYS = frozenset(STATUS_NUMBERS + ('enabled', 'kind', 'stage', 'held_reason'))
OBS_NUMBERS = ('abi_version', 'struct_size', 'kind', 'glyph_intersection',
    'glyph_union', 'hud_mask', 'empty_hearts', 'matches', 'left', 'top', 'width',
    'height', 'enemy_mask')
HEART_ARRAYS = ('heart_inter', 'heart_union', 'heart_red', 'heart_dark', 'heart_bright')
ENEMY_ARRAYS = ('enemy_matches', 'enemy_inter', 'enemy_union', 'enemy_left',
    'enemy_top', 'enemy_body_luma', 'enemy_body_saturation', 'enemy_red_outside',
    'enemy_heart_count', 'enemy_width', 'enemy_height')
OBS_KEYS = frozenset(OBS_NUMBERS + HEART_ARRAYS + ENEMY_ARRAYS)
ROLES = frozenset(('last_live_baseline', 'before', 'zero1', 'zero2', 'trigger',
    'ring_source', 'queued_source', 'fresh_death', 'continue_outcome', 'menu1',
    'menu2', 'live_pause_source', 'pause_ack', 'restart_source', 'new_floor', 'terminal'))
RECORD_KINDS = frozenset(('irregular_checkpoint', 'irregular_continue_intent',
    'irregular_continue_outcome', 'irregular_restart_intent', 'irregular_restart_outcome'))
COMMAND_KEYS = frozenset(('id', 'ordinal', 'target_ns', 'not_before_ns', 'deadline_ns',
    'source_capture_id', 'source_start_ns', 'phase_sample_ns', 'kind', 'direction', 'x', 'y'))


def require(value):
    if not value:
        raise ProbeError('invalid_irregular_response')


def ns(value):
    return type(value) is int and 0 <= value < 2**63


def closed(value, keys):
    require(type(value) is dict and set(value) == set(keys))
    return value


def digest(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_status(value):
    closed(value, STATUS_KEYS)
    require(type(value['enabled']) is bool and value['kind'] in KINDS
        and value['stage'] in STAGES and value['held_reason'] in HELD
        and all(ns(value[k]) for k in STATUS_NUMBERS)
        and value['abi_version'] == 1 and value['episodes'] < 2**31)
    if value['kind'] != 'none':
        require(value['enabled'] and value['episode_id'] > 0 and value['episodes'] > 0
            and value['trigger_capture_id'] > 0 and value['trigger_ns'] > 0
            and value['parent_deadline_ns'] >= value['trigger_ns'])
    if value['stage'] == 'held':
        require(value['held_reason'] != 'none')
    return value


def _box(left, top, width, height):
    return all(type(v) is int for v in (left, top, width, height)) and \
        0 <= left < 896 and 0 <= top < 414 and width > 0 and height > 0 and \
        left + width <= 896 and top + height <= 414


def validate_observation(value):
    closed(value, OBS_KEYS)
    require(all(ns(value[k]) and value[k] <= 896*414 for k in OBS_NUMBERS)
        and value['abi_version'] == 1 and value['struct_size'] == 288
        and value['kind'] in (0, 1, 2, 3) and value['hud_mask'] <= 15
        and value['enemy_mask'] <= 15 and value['empty_hearts'] <= 3
        and value['matches'] in (0, 1, 2))
    for keys, count in ((HEART_ARRAYS, 3), (ENEMY_ARRAYS, 4)):
        for key in keys:
            require(type(value[key]) is list and len(value[key]) == count
                and all(ns(n) and n <= 896*414 for n in value[key]))
    require(all(n <= 2 for n in value['enemy_matches']))
    require(value['glyph_intersection'] <= value['glyph_union'] <= 6480
        and 0 <= value['left'] <= 896 and 0 <= value['top'] <= 414
        and value['width'] <= 896-value['left'] and value['height'] <= 414-value['top'])
    for i in range(3):
        require(value['heart_inter'][i] <= 382
            and value['heart_inter'][i] <= value['heart_union'][i] <= 625
            and value['heart_red'][i] <= 306 and value['heart_dark'][i] <= 306
            and value['heart_bright'][i] <= 306)
    for i in range(4):
        require(value['enemy_inter'][i] <= value['enemy_union'][i] <= 5304
            and value['enemy_left'][i] <= 896 and value['enemy_top'][i] <= 414
            and value['enemy_width'][i] <= 896-value['enemy_left'][i]
            and value['enemy_height'][i] <= 414-value['enemy_top'][i]
            and value['enemy_body_luma'][i] <= 696 and value['enemy_body_saturation'][i] <= 696
            and value['enemy_red_outside'][i] <= 5304 and value['enemy_heart_count'][i] <= 3)
    if value['kind'] == 1:
        require(value['matches'] == 1 and value['hud_mask'] == 15
            and value['empty_hearts'] == 3
            and (value['left'], value['top'], value['width'], value['height']) == (312, 312, 270, 24)
            and value['glyph_intersection'] <= 522 <= value['glyph_union']
            and 100*value['glyph_intersection'] >= 64*value['glyph_union']
            and 100*value['glyph_intersection'] >= 90*522)
        for i in range(3):
            require(value['heart_union'][i] >= 382
                and 100*value['heart_inter'][i] >= 90*value['heart_union'][i]
                and 100*value['heart_inter'][i] >= 95*382
                and value['heart_red'][i] >= 225 and value['heart_red'][i] <= 306
                and value['heart_dark'][i] >= 192 and value['heart_dark'][i] <= 306
                and value['heart_bright'][i] <= 48)
    elif value['kind'] == 2:
        require(value['matches'] == 1 and value['enemy_mask'] == 0
            and _box(value['left'], value['top'], value['width'], value['height'])
            and (value['width'], value['height']) == (181, 28)
            and 160 <= value['left'] <= 555 and 60 <= value['top'] <= 332
            and value['glyph_intersection'] <= 223 <= value['glyph_union']
            and 212 <= value['glyph_union']-223+value['glyph_intersection'] <= 237
            and 100*value['glyph_intersection'] >= 94*value['glyph_union']
            and 100*value['glyph_intersection'] >= 95*223)
    elif value['kind'] == 3:
        require(value['enemy_mask'] != 0 and value['hud_mask'] == 15)
    for i in range(4):
        if not value['enemy_mask'] & (1 << i):
            continue
        n = value['enemy_heart_count'][i]
        require(value['enemy_matches'][i] == 1 and 1 <= n <= 3
            and value['enemy_inter'][i] <= 137*n
            and 100*value['enemy_inter'][i] >= 90*value['enemy_union'][i]
            and 100*value['enemy_inter'][i] >= 93*137*n
            and value['enemy_union'][i] >= 137*n
            and value['enemy_red_outside'][i] == value['enemy_union'][i]-137*n
            and value['enemy_red_outside'][i] <= 64
            and value['enemy_body_luma'][i] >= 48 and value['enemy_body_luma'][i] <= 696
            and value['enemy_body_saturation'][i] >= 96 and value['enemy_body_saturation'][i] <= 696
            and 15 + 17*(n-1) <= value['enemy_width'][i] <= 15 + 19*(n-1)
            and 13 <= value['enemy_height'][i] <= 14
            and _box(value['enemy_left'][i], value['enemy_top'][i],
                value['enemy_width'][i], value['enemy_height'][i]))
        cx, cy = ((412, 207), (484, 207), (448, 171), (448, 243))[i]
        require(abs(2*value['enemy_left'][i]+value['enemy_width'][i]-2*cx) <= 12
            and -64 <= 2*value['enemy_top'][i]+value['enemy_height'][i]-2*cy <= -24
            and value['enemy_left'][i] >= cx-68
            and value['enemy_left'][i]+value['enemy_width'][i] <= cx+68
            and value['enemy_top'][i] >= cy-43
            and value['enemy_top'][i]+value['enemy_height'][i] <= cy-4)
    return value


def validate_command(value, kinds=(3, 4, 5)):
    closed(value, COMMAND_KEYS)
    require(all(ns(value[k]) for k in COMMAND_KEYS-{'kind', 'direction', 'x', 'y'})
        and type(value['kind']) is int and value['kind'] in kinds
        and type(value['direction']) is int and value['direction'] in (0, 1, 2, 3, 4)
        and all(type(value[k]) is int and -(2**31) <= value[k] < 2**31 for k in ('x', 'y'))
        and value['id'] > 0 and value['source_capture_id'] > 0
        and value['not_before_ns'] <= value['deadline_ns'])
    require(value['direction'] in (1, 2, 3, 4) if value['kind'] == 4 else value['direction'] == 0)
    if value['kind'] == 5:
        require((value['x'], value['y']) == (90, 447))
    return value


def validate_record(kind, payload):
    require(kind in RECORD_KINDS)
    closed(payload, ('irregular', 'generation', 'resources', 'frames', 'observations',
                     'command', 'ack', 'proofs', 'assessment_hint'))
    state = validate_status(payload['irregular'])
    require(ns(payload['generation']) and state['kind'] in ('stalled', 'death'))
    resources = closed(payload['resources'], ('raw_slots', 'raw_bytes', 'pin_slots',
                        'episode_metadata_bytes', 'final_metadata_bytes'))
    require(all(ns(v) for v in resources.values()) and resources['raw_slots'] <= 44
        and resources['raw_bytes'] <= 64*1024*1024 and resources['pin_slots'] <= 24
        and resources['episode_metadata_bytes'] <= 224*1024
        and resources['final_metadata_bytes'] <= 1080*1024)
    require(type(payload['frames']) is list and len(payload['frames']) <= 16)
    frames = {}
    role_frames = {}
    roles = set()
    for frame in payload['frames']:
        closed(frame, ('role', 'capture_id', 'start_ns', 'end_ns', 'prefix', 'generation', 'rgba_sha256'))
        require(frame['role'] in ROLES and frame['role'] not in roles
            and all(ns(frame[k]) for k in ('capture_id', 'start_ns', 'end_ns', 'prefix', 'generation'))
            and frame['capture_id'] > 0 and frame['start_ns'] < frame['end_ns']
            and frame['generation'] == payload['generation'] and digest(frame['rgba_sha256']))
        # Several logical roles may bind the same immutable capture.
        if frame['capture_id'] in frames:
            require({k:v for k,v in frame.items() if k != 'role'} ==
                {k:v for k,v in frames[frame['capture_id']].items() if k != 'role'})
        roles.add(frame['role']); frames[frame['capture_id']] = frame
        role_frames[frame['role']] = frame
    require(type(payload['observations']) is list and len(payload['observations']) <= 5)
    observations = {}
    for observation in payload['observations']:
        closed(observation, ('capture_id', 'value'))
        require(ns(observation['capture_id']) and observation['capture_id'] in frames
            and observation['capture_id'] not in observations)
        observations[observation['capture_id']] = validate_observation(observation['value'])
    command = payload['command']
    if command is not None:
        validate_command(command)
        require(command['source_capture_id'] in frames
            and command['source_start_ns'] == frames[command['source_capture_id']]['start_ns'])
    ack = payload['ack']
    if ack is not None:
        closed(ack, ('command_id', 'kind', 'started_ns', 'completed_ns', 'outcome'))
        require(all(ns(ack[k]) for k in ('command_id', 'started_ns', 'completed_ns'))
            and type(ack['kind']) is int and ack['kind'] in (3, 4, 5)
            and ack['outcome'] in ('acked', 'unknown')
            and 0 < ack['started_ns'] <= ack['completed_ns']
            and command is not None and ack['command_id'] == command['id']
            and ack['kind'] == command['kind'])
    require(type(payload['proofs']) is list and len(payload['proofs']) <= 2)
    for proof in payload['proofs']:
        closed(proof, ('capture_id', 'start_ns', 'end_ns', 'normal_motion', 'dx', 'dy', 'enemy'))
        require(ns(proof['capture_id']) and proof['capture_id'] in frames and proof['normal_motion'] == 'blocked'
            and ns(proof['start_ns']) and ns(proof['end_ns'])
            and type(proof['dx']) is int and type(proof['dy']) is int
            and proof['dx'] == proof['dy'] == 0
            and proof['start_ns'] == frames[proof['capture_id']]['start_ns']
            and proof['end_ns'] == frames[proof['capture_id']]['end_ns'])
        validate_observation(proof['enemy'])
        require(proof['enemy']['kind'] == 3 and command is not None and command['kind'] == 4
            and proof['enemy']['enemy_mask'] & (1 << (command['direction']-1)))
    hint = payload['assessment_hint']
    if hint is not None:
        closed(hint, ('job_id', 'capture_id', 'prefix', 'status', 'outcome'))
        require(all(ns(hint[k]) for k in ('job_id', 'capture_id', 'prefix'))
            and hint['job_id'] > 0 and hint['capture_id'] in frames
            and frames[hint['capture_id']]['prefix'] == hint['prefix']
            and hint['status'] in ('ok', 'cancelled', 'deadline', 'invalid', 'allocation', 'kernel')
            and hint['outcome'] in ('unknown', 'candidate', 'target', 'negative'))
    if kind == 'irregular_checkpoint':
        require('trigger' in roles and role_frames['trigger']['capture_id'] == state['trigger_capture_id']
            and 'last_live_baseline' in roles
            and role_frames['last_live_baseline']['capture_id'] == state['live_baseline_capture_id'])
        if state['kind'] == 'death':
            require(state['trigger_capture_id'] in observations
                and observations[state['trigger_capture_id']]['kind'] == 1
                and state['proof_capture_id'] == 0)
        else:
            require(command is not None and command['kind'] == 4 and len(payload['proofs']) == 2
                and ack is not None and ack['kind'] == 4 and ack['outcome'] == 'acked'
                and command['id'] == ack['command_id'] == state['prefix']
                and command['source_capture_id'] == state['before_capture_id']
                and 'before' in roles and role_frames['before']['capture_id'] == state['before_capture_id']
                and 'zero1' in roles and role_frames['zero1']['capture_id'] == state['proof_capture_id']
                and 'zero2' in roles and role_frames['zero2']['capture_id'] == state['trigger_capture_id']
                and payload['proofs'][0]['capture_id'] == state['proof_capture_id']
                and payload['proofs'][1]['capture_id'] == state['trigger_capture_id']
                and payload['proofs'][0]['capture_id'] < payload['proofs'][1]['capture_id'])
            for proof in payload['proofs']:
                require(observations.get(proof['capture_id']) == proof['enemy']
                    and frames[proof['capture_id']]['prefix'] == command['id']
                    and ack['completed_ns'] <= proof['start_ns'])
    elif kind.endswith('_intent'):
        require(command is not None and command['kind'] == (5 if 'continue' in kind else 3))
        command_key = 'continue_command_id' if command['kind'] == 5 else 'restart_command_id'
        require(state[command_key] == command['id'])
        if command['kind'] == 5:
            require(command['source_capture_id'] in observations
                and observations[command['source_capture_id']]['kind'] == 1
                and 'fresh_death' in roles
                and role_frames['fresh_death']['capture_id'] == command['source_capture_id'])
        elif 'menu1' in roles or 'menu2' in roles:
            require('menu1' in roles and 'menu2' in roles)
            first, second = role_frames['menu1'], role_frames['menu2']
            require(first['capture_id'] != second['capture_id'] and first['end_ns'] <= second['start_ns']
                and first['prefix'] == second['prefix'] == state['prefix']
                and first['capture_id'] in observations and second['capture_id'] in observations)
            one, two = observations[first['capture_id']], observations[second['capture_id']]
            require(one['kind'] == two['kind'] == 2 and abs(one['left']-two['left']) <= 2
                and abs(one['top']-two['top']) <= 2)
    else:
        require(command is not None and ack is not None
            and command['kind'] == (5 if 'continue' in kind else 3))
        required_role = 'continue_outcome' if command['kind'] == 5 else 'new_floor'
        require(required_role in roles)
        command_key = 'continue_command_id' if command['kind'] == 5 else 'restart_command_id'
        capture_key = 'continue_capture_id' if command['kind'] == 5 else 'next_floor_capture_id'
        require(state[command_key] == command['id'] == ack['command_id']
            and state[capture_key] == role_frames[required_role]['capture_id'])
    return payload


def validate_controller(value, *, allow_irregular):
    """Keep action identity truthful without reinterpreting pixel/phase proof."""
    if value is None:
        return
    require(type(value) is dict)
    events = value.get('events', [])
    require(type(events) is list and len(events) <= 64)
    acknowledgements = set()
    previous = 0
    moves = []
    for event in events:
        require(type(event) is dict and type(event.get('kind')) is int
            and event['kind'] in ((1, 2, 3, 4, 5) if allow_irregular else (1, 2, 3, 4)))
        if event['kind'] == 5:
            require(event.get('direction') == 0 and type(event.get('direction')) is int
                and event.get('motion', 0) == 0 and type(event.get('motion', 0)) is int
                and event.get('dx', 0) == event.get('dy', 0) == 0
                and type(event.get('dx', 0)) is int and type(event.get('dy', 0)) is int)
        if event.get('outcome') == 2:
            require(ns(event.get('id')) and event['id'] > previous
                and event['id'] not in acknowledgements)
            acknowledgements.add(event['id']); previous = event['id']
            if event['kind'] == 4:
                moves.append(event['id'])
    references = value.get('motion_references')
    if references is not None:
        require(type(references) is list and len(references) <= 16
            and [row.get('command_id') for row in references if type(row) is dict] == moves)


def sequence_summary(records, frame_metadata):
    """Validate durable ordering; an unfinished intent stays explicitly pending.

    Period, motion signature and frontmost UI permission are native C proof,
    not reconstructed from a fixed Python clock or from read-only metadata.
    """
    episodes = {}
    for kind, payload in records:
        validate_record(kind, payload)
        state = payload['irregular']
        key = (payload['generation'], state['episode_id'])
        if kind == 'irregular_checkpoint':
            require(key not in episodes)
            episodes[key] = dict(identity=tuple(state[k] for k in
                ('trigger_capture_id', 'before_capture_id', 'live_baseline_capture_id',
                 'proof_capture_id', 'trigger_ns', 'parent_deadline_ns')),
                kind=state['kind'], seen=set(), continue_intent=None, restart_intent=None, frozen=False)
        require(key in episodes)
        episode = episodes[key]
        require(kind not in episode['seen'] and episode['identity'] == tuple(state[k] for k in
            ('trigger_capture_id', 'before_capture_id', 'live_baseline_capture_id',
             'proof_capture_id', 'trigger_ns', 'parent_deadline_ns')))
        if state['kind'] != episode['kind']:
            # The only upgrade keeps the already durable stalled checkpoint,
            # epoch, original proof and deadline. Its new input has its own
            # fresh positive death source and its own intent.
            require(episode['kind'] == 'stalled' and state['kind'] == 'death'
                and kind == 'irregular_continue_intent' and state['stage'] == 'death_continue'
                and state['durable_ns'] > 0 and state['pause_capture_id'] == 0
                and episode['continue_intent'] is None and episode['restart_intent'] is None)
            episode['kind'] = 'death'
        for frame in payload['frames']:
            raw = frame_metadata.get(frame['capture_id'])
            require(type(raw) is dict and raw.get('raw_sha256') == frame['rgba_sha256'])
            metadata = raw.get('metadata')
            require(type(metadata) is dict and metadata.get('capture_start_ns') == frame['start_ns']
                and metadata.get('capture_end_ns') == frame['end_ns']
                and metadata.get('completed_prefix_start') == metadata.get('completed_prefix_end') == frame['prefix']
                and metadata.get('generation') == frame['generation']
                and metadata.get('stable_prefix') is True
                and metadata.get('inflight_start') is False and metadata.get('inflight_end') is False)
        if kind.endswith('_intent'):
            require(not episode['frozen'])
            name = 'continue_intent' if 'continue' in kind else 'restart_intent'
            require(episode[name] is None)
            if name == 'restart_intent' and state['kind'] == 'death':
                require('irregular_continue_outcome' in episode['seen'])
            command = payload['command']
            source = next(frame for frame in payload['frames'] if frame['capture_id'] == command['source_capture_id'])
            require(source['prefix'] == state['prefix'])
            episode[name] = dict(command)
        elif kind.endswith('_outcome'):
            name = 'continue_intent' if 'continue' in kind else 'restart_intent'
            command = payload['command']; ack = payload['ack']
            require(episode[name] == command)
            if ack['outcome'] == 'unknown':
                episode['frozen'] = True
            else:
                role = 'continue_outcome' if 'continue' in kind else 'new_floor'
                frame = next(frame for frame in payload['frames'] if frame['role'] == role)
                require(frame['prefix'] == state['prefix'] == command['id']
                    and ack['completed_ns'] <= frame['start_ns'])
        episode['seen'].add(kind)
    # A checkpoint or completed death continuation is still an interrupted
    # episode. Only its own durable restart outcome closes that episode.
    pending = any(ep['frozen'] or 'irregular_restart_outcome' not in ep['seen']
        for ep in episodes.values())
    return dict(episodes=len(episodes), pending=pending,
        unknown_ack=any(ep['frozen'] for ep in episodes.values()))
