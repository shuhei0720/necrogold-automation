"""Public-earned transfer of an existing unissued FULL observation.

Composition reuses the old halo lifecycle and its read-only 14-field query.
No private Controller state is injected. Procedural pixels, Scene inputs and
component clocks do not reconstruct an unavailable iPhone job or its flags.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import random
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_full_halo_data122 as halo
from tests import test_native_full_framing101 as full
from tests import test_native_single_offer108 as single
from tests import test_native_offer_coverage104 as offer


CORE = Path(os.environ.get('NECRO124_TRANSFER_CORE', str(native.CORE)))

READ_ONLY_B_SUFFIX = r'''
/* Public lifecycle earned every field; query and qualification are const. */
int ng2_transfer124_B_earned(const NG2Controller*p,const NG2RingResult*r,uint64_t*out,size_t count){
 NG2Decision choice={0};int direction=0;
 if(!p||!r||!out||count<29)return 0;
 unsigned char *copy=malloc(sizeof(*p));if(!copy)return 0;memcpy(copy,p,sizeof(*p));
 out[0]=(uint64_t)cycle_full_admit(p,r,&choice);out[1]=(uint64_t)choice.direction;
 out[2]=(uint64_t)choice.reason;out[3]=(uint64_t)cycle_result_positive_hint(r);out[4]=(uint64_t)entry_result_safe(r);
 out[5]=(uint64_t)cycle_current_data_pair(&p->cycle_anchor,&p->scene);
 out[6]=(uint64_t)p->cycle_retry_only;out[7]=(uint64_t)p->cycle_full_data_active;out[8]=(uint64_t)p->cycle.pending;
 out[9]=(uint64_t)p->cycle_full_spent;out[10]=(uint64_t)p->cycle_full_framing;out[11]=(uint64_t)p->cycle_current_used;
 out[12]=(uint64_t)p->cycle_current_active;out[13]=(uint64_t)p->cycle_retry_used;out[14]=(uint64_t)p->cycle_retry_blocked;
 out[15]=(uint64_t)p->s.input_state;out[16]=p->s.current_command_id;out[17]=(uint64_t)p->cycle_pause_attempted;
 out[18]=p->s.last_capture_id;out[19]=p->cycle.capture_id;out[20]=p->cycle.capture_start_ns;out[21]=p->cycle.prefix;
 out[22]=p->s.last_completed_id;out[23]=p->last_observed_prefix;out[24]=(uint64_t)p->cycle.state;
 out[25]=p->cycle.continuation_deadline_ns;out[26]=(uint64_t)!memcmp(copy,p,sizeof(*p));
 out[27]=(uint64_t)cycle_full_history(p,&direction);out[28]=(uint64_t)direction;
 free(copy);return 29;
}
'''
B_FIELDS = ('full_admit direction reason positive_hint entry_safe current_data_pair '
    'retry_only full_data_active pending full_spent full_framing current_used '
    'current_active retry_used retry_blocked input_state current_command_id '
    'pause_attempted current_capture old_capture old_start prefix last_completed '
    'last_observed cycle_state parent context_unchanged full_history '
    'full_history_direction').split()


def values(value):
    return {name: getattr(value, name) for name, *_ in value._fields_}


def full_normal(f, source):
    status, result = offer.normal_assess(f.ring,
        single.shop_pixels(missing_wall=True), f.h.scene(2, 2, source, beat=True))
    f.assertEqual((0, 0, 1), (status, result.outcome, result.coverage))
    return result


def complete_normal(f, source, case):
    items = [point for point, kind in source.tiles.items() if kind == 'item']
    left, sy = 448+36*min(x for x, _ in items), 159+36*items[0][1]
    producer = halo.single.shop_pixels if case == 'A' else single.shop_pixels
    status, result = offer.normal_assess(f.ring, producer(left=left, sy=sy),
        f.h.scene(2, 2, source, beat=True))
    f.assertEqual((0, 3, 2), (status, result.outcome, result.coverage),
        'the genuinely moved new source needs its own normal complete result')
    return result


def unarmed_current_data(f, *, prepared=False, query=None):
    """Earn B or ordinary prepared-PAUSE DATA; never set Controller fields."""
    f.h, terrain, old, _ = f.p.armed(direction=1)
    f.q = cycle.NativeCycle094Tests(methodName='runTest')
    f.q.lib, f.q.h = f.lib, f.h
    moves = f.h.status().moves
    f.h.ack(old)
    source = full.NativeFullFraming101Tests.full_source()
    source.tiles[(-1, -2)] = 'floor'
    source.tiles[(6, 4)] = 'floor'
    f.h.now = max(f.h.now+2, old.target_ns+100_000_000)
    f.assertEqual(1, f.h.observe_actual(f.h.scene(2, 2, source, beat=True)))
    latest_ack = f.h.events()[-1]
    f.assertEqual((old.id, 2, 0, 0, 0), (latest_ack.command.id,
        latest_ack.outcome, latest_ack.motion, latest_ack.dx, latest_ack.dy))
    f.assertEqual(moves, f.h.status().moves, 'known ACK UNKNOWN is not displacement credit')
    f.source, f.opening, f.root = source, old, f.q.cycle()
    f.saved_counts = f.counts()
    old_result = full_normal(f, source)
    f.start_worker()
    pause = None
    if prepared:
        ready, pause = f.h.tick()
        f.assertEqual((1, 2, 1), (ready, pause.kind, f.h.status().input_state))
        f.assertEqual((0, 0), (f.h.events()[-1].begin_ns, f.h.events()[-1].outcome))
    latest = deepcopy(source)
    latest.tiles[(6, 4)] = 'dirt'
    rng = random.Random(124187)
    latest.signature = bytes(rng.randrange(20, 240) for _ in range(23296))
    f.assertEqual((0, 0, 0), f.h.motion(source, latest, 1),
        'declared component texture earns a hard old-comparison rejection')
    f.assertEqual((2, 0, 0), f.h.motion(latest, latest, 1),
        'the new immutable source still supports its own later direct zeros')
    f.assertEqual(1, f.observe(latest))
    qualification = query(f, old_result) if query else None
    f.assertEqual((0, 0, 0, 0), (f.earned()[1], f.earned()[7],
        f.earned()[8], f.earned()[10]))
    f.commit(old_result)
    job = f.q.cycle()
    f.assertEqual((f.root.job_id+1, f.root.prefix, 1),
        (job.job_id, job.prefix, job.pending))
    f.assertEqual((1, 1, 2, 1), f.earned()[7:11])
    f.assertEqual((f.root.hold_started_ns, f.root.continuation_deadline_ns),
        (job.hold_started_ns, job.continuation_deadline_ns))
    f.assertEqual(f.saved_counts, f.counts())
    return latest, job, {'qualification': qualification, 'prepared_pause_id':
        pause.id if pause else 0, 'earned_after_bind': list(f.earned()),
        'old_result': {name: getattr(old_result, name) for name in
            ('status', 'outcome', 'coverage', 'row_count', 'partial_count')},
        'old_ACK_id': old.id, 'old_ACK_motion': latest_ack.motion,
        'old_to_current_motion': [0, 0, 0], 'new_current_self_motion': [2, 0, 0]}


class NativeTransferredView124Tests(unittest.TestCase):
    observations = []

    @classmethod
    def setUpClass(cls):
        cls.observations = []
        previous = os.environ.get('NECRO122_FULL_HALO_CORE')
        previous_suffix = halo.READ_ONLY_SUFFIX
        try:
            os.environ['NECRO122_FULL_HALO_CORE'] = str(CORE)
            halo.READ_ONLY_SUFFIX = previous_suffix + READ_ONLY_B_SUFFIX
            halo.NativeFullHaloData122Tests.setUpClass()
        finally:
            halo.READ_ONLY_SUFFIX = previous_suffix
            if previous is None:
                os.environ.pop('NECRO122_FULL_HALO_CORE', None)
            else:
                os.environ['NECRO122_FULL_HALO_CORE'] = previous
        lib = halo.NativeFullHaloData122Tests.lib
        lib.ng2_transfer124_B_earned.argtypes = [C.c_void_p, C.POINTER(cycle.Result),
            C.POINTER(C.c_uint64), C.c_size_t]
        ring = halo.NativeFullHaloData122Tests.ring
        ring.ng2_ring_negative_certificate.argtypes = [C.POINTER(cycle.Result)]
        ring.ng2_ring_negative_certificate.restype = C.c_int
        cls.addClassCleanup(halo.NativeFullHaloData122Tests.doClassCleanups)

    @classmethod
    def tearDownClass(cls):
        halo.NativeFullHaloData122Tests.tearDownClass()

    def setUp(self):
        self.f = halo.NativeFullHaloData122Tests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def qualification(self, f, result):
        out = (C.c_uint64*29)()
        self.assertEqual(29, f.lib.ng2_transfer124_B_earned(f.h.engine,
            C.byref(result), out, 29))
        return dict(zip(B_FIELDS, out))

    def current_unknown(self, case):
        f = self.f
        if case == 'A':
            latest, job = f.queued()
            result = f.normal(latest, unknown=True)
        else:
            latest, job, _ = unarmed_current_data(f, query=self.qualification)
            result = full_normal(f, latest)
        f.commit(result)
        self.assertEqual((0, 0, 3), (f.q.cycle().outcome,
            f.q.cycle().status, f.q.cycle().state))
        self.assertEqual(0, f.h.status().beat_period_ns,
            'adopted DATA must retire the old model before new-current proofs')
        self.assertEqual(0, f.h.tick()[0], 'classification alone has no MOVE permission')
        return latest, job

    def no_observation_or_restart(self):
        ready, command = self.f.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))
        self.assertEqual(self.f.saved_counts, self.f.counts())

    def observation_ticket(self, latest, job):
        f = self.f
        before = [bytes(event) for event in f.h.events()]
        self.assertEqual((2, 0, 0), f.h.motion(latest, latest, 1))
        self.assertEqual(1, f.observe(latest))
        first_id = f.h.number
        self.assertEqual(0, f.h.tick()[0], 'one direct-current zero cannot mint a ticket')
        self.assertEqual(0, f.h.status().input_state)
        self.assertEqual(1, f.observe(latest))
        second_id = f.h.number
        self.assertGreater(second_id, first_id)
        self.assertEqual(before, [bytes(event) for event in f.h.events()])
        command = f.h.next_move(latest)
        self.assertEqual((4, 1), (command.kind, command.direction))
        self.assertGreater(command.id, job.prefix)
        self.assertGreater(command.ordinal, max(event.command.ordinal for event in
            f.h.events() if event.command.id <= job.prefix))
        self.assertGreaterEqual(command.source_capture_id, second_id)
        self.assertGreater(f.h.status().beat_period_ns, 0)
        self.assertLessEqual(command.target_ns+80_000_000,
            job.continuation_deadline_ns)
        self.assertEqual(f.saved_counts, f.counts())
        self.assertEqual(before, [bytes(event) for event in f.h.events()[:len(before)]])
        return command

    def test_earned_unissued_arm_keeps_same_oneview_after_current_data_unknown(self):
        f = self.f
        latest, job = f.queued()
        old = f.root
        before = f.earned()
        events_before = [bytes(event) for event in f.h.events()]
        self.assertEqual(14, len(before))
        self.assertEqual((0, 1, 0), before[:3],
            'only framing/source flags retire; the publicly earned oneview remains spent')
        self.assertEqual((1, 1, 2, 1, 0), before[7:12],
            'one current mode2 job consumes one shared DATA without an entered token')
        self.assertEqual((old.job_id+1, old.prefix, old.hold_started_ns,
            old.continuation_deadline_ns), (job.job_id, job.prefix,
            job.hold_started_ns, job.continuation_deadline_ns))
        self.assertNotEqual(old.capture_id, job.capture_id)
        self.assertEqual((0, 0), (f.h.status().input_state,
            f.h.status().current_command_id))

        result = f.normal(latest, unknown=True)
        self.assertEqual((0, 0, 1), (result.status, result.outcome, result.coverage))
        normal_summary = {name: getattr(result, name) for name in
            ('status', 'outcome', 'coverage', 'row_count', 'partial_count',
             'partial_safe_no_positive', 'checks')}
        normal_summary['packet_sha256_before_time_binding'] = hashlib.sha256(bytes(result)).hexdigest()
        f.commit(result)
        after, state = f.earned(), f.q.cycle()
        snapshot = {
            'old_cycle': values(old), 'new_data_cycle': values(job),
            'committed_cycle': values(state), 'earned_before': list(before),
            'earned_after': list(after), 'normal_result': normal_summary,
            'input_counts_before': list(f.saved_counts),
            'input_counts_after': list(f.counts()),
            'old_event_bytes_unchanged': events_before == [bytes(event) for event in f.h.events()],
            'input_state': f.h.status().input_state,
            'current_command_id': f.h.status().current_command_id,
            'component_clock_ns': f.h.now,
        }
        self.observations.append(snapshot)
        self.assertEqual((1, 1, 1), (after[1], after[7], after[10]),
            'spent/current-used/shared-DATA counters cannot be reset by UNKNOWN')
        self.assertEqual((job.job_id, job.capture_id, job.prefix,
            old.continuation_deadline_ns), (state.job_id, state.capture_id,
            state.prefix, state.continuation_deadline_ns))
        self.assertEqual(f.saved_counts, f.counts())
        self.assertEqual(events_before, [bytes(event) for event in f.h.events()],
            'DATA classification cannot resend or rewrite an earlier input')
        self.assertEqual((0, 0), (f.h.status().input_state,
            f.h.status().current_command_id))
        self.assertEqual((0, 0, 3), (state.outcome, state.status, state.state),
            'the same earned unissued oneview must await new direct-current proofs, not be lost as generic DATA-only UNKNOWN')

    def test_unarmed_old_normal_qualified_view_transfers_before_current_data_bind(self):
        f = self.f
        latest, job, snapshot = unarmed_current_data(f, query=self.qualification)
        qualification = snapshot['qualification']
        self.assertEqual((1, 1, 5, 0, 1, 1, 1, 1), tuple(qualification[k] for k in
            ('full_admit', 'direction', 'reason', 'positive_hint', 'entry_safe',
             'current_data_pair', 'full_history', 'full_history_direction')))
        self.assertEqual(1, qualification['retry_blocked'] & 1)
        self.assertEqual((0,)*9, tuple(qualification[k] for k in
            ('full_spent', 'full_framing', 'current_used', 'current_active',
             'retry_only', 'full_data_active', 'input_state',
             'current_command_id', 'pause_attempted')))
        self.assertEqual(1, qualification['context_unchanged'])
        self.assertEqual((qualification['prefix'],)*3, tuple(qualification[k]
            for k in ('prefix', 'last_completed', 'last_observed')))
        events = [bytes(event) for event in f.h.events()]
        result = full_normal(f, latest)
        f.commit(result)
        state, after = f.q.cycle(), f.earned()
        snapshot.update({'case': 'B_unarmed_qualified', 'new_data': values(job),
            'committed_cycle': values(state), 'earned_after_unknown': list(after),
            'input_counts_before': list(f.saved_counts),
            'input_counts_after': list(f.counts()),
            'old_event_bytes_unchanged': events == [bytes(event) for event in f.h.events()]})
        self.observations.append(snapshot)
        self.assertEqual(f.saved_counts, f.counts())
        self.assertEqual(events, [bytes(event) for event in f.h.events()])
        self.assertEqual((job.job_id, job.capture_id, job.prefix,
            f.root.continuation_deadline_ns), (state.job_id, state.capture_id,
            state.prefix, state.continuation_deadline_ns))
        self.assertEqual((0, 0, 3), (state.outcome, state.status, state.state),
            'the old normal-qualified unused oneview must transfer before its source is retired')
        self.assertEqual((1, 1, 1), (after[1], after[7], after[10]),
            'B first consumes its existing allowance; it never resets or remints it')

    def test_a_and_b_two_new_zeros_new_fit_unit_and_normal_negative_restart(self):
        for index, case in enumerate(('A', 'B')):
            if index:
                self.setUp()
            with self.subTest(case=case):
                f = self.f
                latest, job = self.current_unknown(case)
                old_events = [bytes(event) for event in f.h.events()]
                command = self.observation_ticket(latest, job)
                ready, duplicate = f.h.tick()
                self.assertFalse(ready and duplicate.kind == 4,
                    'one successful reservation consumes this transferred observation')
                f.h.ack(command)
                self.assertEqual((f.saved_counts[0]+1, f.saved_counts[1]),
                    (f.h.status().inputs, f.h.status().moves))
                moved = native.translated(latest, 1)
                self.assertEqual((1, -1, 0), f.h.motion(latest, moved, 1))
                f.h.observed_result(command, moved)
                state = f.q.cycle()
                self.assertEqual((f.saved_counts[0]+1, f.saved_counts[1]+1),
                    (f.h.status().inputs, f.h.status().moves))
                self.assertEqual((job.job_id+1, 1), (state.job_id, state.pending))
                self.assertEqual(old_events, [bytes(event) for event in
                    f.h.events()[:len(old_events)]], 'the old UNKNOWN ACK is never rescued')
                negative = complete_normal(f, moved, case)
                self.assertEqual(1, f.ring.ng2_ring_negative_certificate(C.byref(negative)))
                f.commit(negative)
                self.assertEqual((3, 0, 2), (f.q.cycle().outcome,
                    f.q.cycle().status, f.q.cycle().coverage),
                    'the Controller must independently accept its own new source certificate')
                self.assertEqual(0, f.q.durable())
                f.q.pause_observed()
                self.assertEqual(0, f.h.tick()[0])
                self.assertEqual(1, f.q.durable())
                ready, restart = f.h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(0, f.lib.ng2_controller_begin(f.h.engine,
                    restart.id, f.h.now, 1, 0, 1))
                self.assertEqual(1, f.q.intent(restart))
                f.q.next_floor(restart)
                final = f.q.cycle()
                self.assertEqual(1, f.lib.ng2_controller_cycle_outcome_commit(f.h.engine,
                    final.job_id, final.next_floor_capture_id, f.h.prefix, f.h.now))
                self.assertEqual(job.level_id+1, f.q.cycle().level_id)
                self.observations.append({'case': case+'_normal_restart',
                    'observation_id': command.id, 'old_prefix': job.prefix,
                    'negative_policy': negative.certificate.policy_version,
                    'restart_id': restart.id, 'next_level': f.q.cycle().level_id})

    def test_prepared_pause_current_data_has_no_unissued_transfer_provenance(self):
        f = self.f
        latest, job, snapshot = unarmed_current_data(f, prepared=True,
            query=self.qualification)
        q = snapshot['qualification']
        self.assertEqual((0, 1, snapshot['prepared_pause_id'], 1),
            (q['full_admit'], q['input_state'], q['current_command_id'],
             q['pause_attempted']),
            'an actual prepared PAUSE cannot be copied away to qualify B')
        self.assertEqual(0, f.earned()[1])
        f.commit(full_normal(f, latest))
        self.assertEqual((0, 0, 7), (f.q.cycle().outcome,
            f.q.cycle().status, f.q.cycle().state))
        second = deepcopy(latest)
        second.tiles[(-4, -1)] = 'dirt'
        f.observe(second)
        self.assertEqual((job.job_id, 1), (f.q.cycle().job_id, f.earned()[10]))
        self.no_observation_or_restart()
        self.observations.append({'case': 'ordinary_prepared_DATA_HELD',
            'qualification': q, 'prepared_pause_id': snapshot['prepared_pause_id']})

    def test_candidate_and_word_veto_win_before_transferred_observation(self):
        for index, (case, fault) in enumerate((('A', 'candidate'), ('A', 'word'),
                ('B', 'candidate'), ('B', 'word'))):
            if index:
                self.setUp()
            with self.subTest(case=case, fault=fault):
                f = self.f
                if case == 'A':
                    latest, job = f.queued()
                    result = f.normal(latest, unknown=True, target=fault == 'candidate')
                else:
                    latest, job, _ = unarmed_current_data(f, query=self.qualification)
                    if fault == 'candidate':
                        status, result = offer.normal_assess(f.ring,
                            single.shop_pixels(target=True, target_name=False),
                            f.h.scene(2, 2, latest, beat=True))
                        self.assertEqual(0, status)
                    else:
                        result = full_normal(f, latest)
                if fault == 'candidate':
                    self.assertIn(result.outcome, (1, 2))
                else:
                    self.assertGreater(result.partial_count, 0)
                    result.partial[0].word_present = 1
                    result.partial[0].word_iou = result.partial[0].word_coverage = 1
                f.commit(result)
                self.assertEqual(7, f.q.cycle().state)
                if fault == 'candidate':
                    self.assertEqual(1, f.q.cycle().candidate_latched)
                self.assertEqual(1, f.observe(latest))
                self.assertEqual(1, f.observe(latest))
                self.assertEqual(job.job_id, f.q.cycle().job_id)
                self.no_observation_or_restart()

    def test_two_later_mutual_zeros_cannot_replace_direct_new_source_zeros(self):
        latest, _ = self.current_unknown('B')
        wrong = deepcopy(latest)
        rng = random.Random(124222)
        wrong.signature = bytes(rng.randrange(20, 240) for _ in range(23296))
        self.assertEqual((0, 0, 0), self.f.h.motion(latest, wrong, 1))
        self.assertEqual((2, 0, 0), self.f.h.motion(wrong, wrong, 1))
        self.assertEqual(1, self.f.observe(wrong))
        self.assertEqual(1, self.f.observe(wrong))
        self.assertEqual(1, self.f.observe(latest))
        self.no_observation_or_restart()

    def test_item_halo_and_local_floor_changes_reject_the_current_proof(self):
        for index, fault in enumerate(('item', 'halo', 'local')):
            if index:
                self.setUp()
            with self.subTest(fault=fault):
                latest, job = self.current_unknown('B')
                changed = deepcopy(latest)
                if fault == 'item':
                    changed.tiles[(7, 3)] = 'item'
                    changed.protected.add((7, 3))
                elif fault == 'halo':
                    changed.protected.add((8, 4))
                else:
                    changed.tiles[(-1, 0)] = 'stone'
                self.assertEqual(1, self.f.observe(changed))
                self.assertEqual(1, self.f.observe(latest))
                self.assertEqual(job.job_id, self.f.q.cycle().job_id)
                self.no_observation_or_restart()

    def test_original_parent_and_cancel_do_not_reopen_the_transferred_view(self):
        for index, fault in enumerate(('parent', 'cancel')):
            if index:
                self.setUp()
            with self.subTest(fault=fault):
                latest, job = self.current_unknown('A')
                if fault == 'parent':
                    self.f.h.now = job.continuation_deadline_ns+1
                else:
                    self.f.h.now += 1
                    self.f.lib.ng2_controller_cancel(self.f.h.engine, self.f.h.now, 2)
                self.f.observe(latest, advance=1)
                self.no_observation_or_restart()

    def test_consumed_reservation_and_changed_begin_never_issue_a_second_view(self):
        for index, fault in enumerate(('consumed', 'changed_begin')):
            if index:
                self.setUp()
            with self.subTest(fault=fault):
                latest, job = self.current_unknown('B')
                command = self.observation_ticket(latest, job)
                if fault == 'consumed':
                    ready, duplicate = self.f.h.tick()
                    self.assertFalse(ready and duplicate.kind == 4)
                    self.assertEqual(command.id, self.f.h.status().current_command_id)
                else:
                    changed = deepcopy(latest)
                    changed.tiles[(-1, 0)] = 'stone'
                    self.assertEqual(1, self.f.observe(changed))
                    self.f.h.now = max(self.f.h.now, command.not_before_ns)
                    self.assertEqual(0, self.f.lib.ng2_controller_begin(self.f.h.engine,
                        command.id, self.f.h.now, 1, 0, 1))
                    self.f.observe(latest, advance=1)
                    self.no_observation_or_restart()
                self.assertEqual((job.job_id, 1, 1), (self.f.q.cycle().job_id,
                    self.f.earned()[1], self.f.earned()[10]))
                self.assertEqual(self.f.saved_counts, self.f.counts())


if __name__ == '__main__':
    unittest.main()
