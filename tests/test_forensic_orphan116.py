"""Prepared orphan exports are diagnostics, never manufactured C terminals.

These are procedural bytes matching NG2CycleExport's existing diagnostic
schema. They test collection/publication, not phone gameplay or lost input.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import io
from contextlib import redirect_stdout
from unittest.mock import patch

from necroprobe import native_cycle as cycle
from necroprobe.validation import ProbeError
import test_continuous_client116 as baseline


CHILD=baseline.SECOND
SLOT_BYTES=156*1024*1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parent_reservation(model, root, child=CHILD):
    """Commit the reservation before the real RS intent and keep its chain."""
    payload=dict(schema='ngg2-continuation-reservation-v1',root_id=root,run_id=child,
        index=1,predecessor_id=root,token_id='1'*32,slot_bytes=SLOT_BYTES)
    normal=[(r,copy.deepcopy(json.loads(model['records'][r['sequence']])))
        for r in model['manifest']['records'] if 0<r['sequence']<513]
    order=[]
    for row,body in normal:
        if row['kind']=='restart_intent':
            order.append((dict(kind='continuation_reservation',cycle=1),dict(payload=payload)))
        order.append((row,body))
    rechain_parent(model,root,order)


def rechain_parent(model,root,order):
    records={r['sequence']:model['records'][r['sequence']]
        for r in model['manifest']['records'] if r['sequence']==0 or r['sequence']>=513}
    metadata=[copy.deepcopy(r) for r in model['manifest']['records'] if r['sequence']==0]
    previous=None;terminal_sha=None
    for sequence,(row,body) in enumerate(order,1):
        body.update(schema='ngg2-cycle-record-v1',run_id=root,sequence=sequence,
            kind=row['kind'],cycle=row['cycle'],previous=previous)
        if row['kind']=='continuation_seal':body['payload']['terminal_sha256']=terminal_sha
        raw=cycle.canonical(body);digest=sha(raw);records[sequence]=raw
        metadata.append(dict(sequence=sequence,kind=row['kind'],cycle=row['cycle'],bytes=len(raw),sha256=digest))
        if row['kind']=='terminal':terminal_sha=digest
        previous=digest
    metadata.extend(copy.deepcopy(r) for r in model['manifest']['records'] if r['sequence']>=513)
    model['records']=records;model['manifest']['records']=metadata
    model['manifest']['total_bytes']=len(model['manifest']['images'])*len(model['image'])+sum(map(len,records.values()))


def orphan_model(root, *, header=True, artifacts=True):
    model=baseline.campaign_model(CHILD,root,1,root,None)
    records={};metadata=[];diagnostics=[]
    if header:
        body=json.loads(model['records'][0])
        body['provenance'].update(accepted_started_ns=250,generation=1)
        raw=cycle.canonical(body);records[0]=raw
        metadata.append(dict(sequence=0,kind='session',cycle=0,bytes=len(raw),sha256=sha(raw)))
    else:
        diagnostics.append(dict(code='session_header_uncommitted',authority=False))
    if artifacts:
        name='session.json' if header else '.part-00000000-0000-0000-0000-000000000001'
        original=records[0] if header else b'partial session bytes'
        value=dict(id=sha(name.encode()),name=name,kind='metadata' if header else 'uncommitted',
            bytes=len(original),sha256=sha(original),authority=False)
        raw=cycle.canonical(dict(schema='ngg2-cycle-artifacts-v1',run_id=CHILD,artifacts=[value]))
        records[557]=raw
        metadata.append(dict(sequence=557,kind='artifacts',cycle=0,bytes=len(raw),sha256=sha(raw)))
        diagnostics.append(dict(code='interrupted_artifacts',count=1,authority=False))
    model['records']=records
    model['manifest'].update(complete=False,interrupted=True,input_state=4,ui_frozen=True,
        images=[],records=metadata,diagnostics=diagnostics,total_bytes=sum(map(len,records.values())))
    return model


class OrphanServer116(baseline.ContinuousServer116):
    def __init__(self,base,*,header=True,artifacts=True):
        super().__init__(base);self.header=header;self.artifacts=artifacts;self.orphan_enabled=True
        self.after_models=self.prepare_orphan;self.tamper=None

    def prepare_orphan(self,server):
        parent_reservation(self.models[self.root],self.root)
        self.models[CHILD]=orphan_model(self.root,header=self.header,artifacts=self.artifacts)
        if self.tamper is not None:self.tamper(self)

    def wire(self,terminal=False,second=True):
        if not self.orphan_enabled:
            return super().wire(terminal,second)
        value=baseline.status_wire(terminal=terminal,second=second)
        p=value['payload'];p['root_id']=self.root;value['run_id']=self.root
        p['children'][0]['run_id']=self.root
        if second:p['children'][1]['predecessor_id']=self.root
        p['active_run_id']=CHILD if second else self.root
        for row in p['children']:
            if row['index']==0 and row['escrow_sealed']:
                seal=next(r for r in self.models[self.root]['manifest']['records'] if r['kind']=='continuation_seal')
                row['escrow_sha256']=seal['sha256']
        if terminal:
            p.update(input_state=4,ui_frozen=True,stop_reason='cancelled')
            p['children'][-1].update(state='stopped',escrow_sealed=False,escrow_sha256=None,terminal_reason=2)
        return value


class ForensicOrphanClient116Tests(unittest.TestCase):
    run_client=baseline.ContinuousClientRun116Tests.run_client

    def test_session_complete_and_uncommitted_orphans_keep_a_diagnostic_row(self):
        for header,artifacts in ((True,False),(True,True),(False,True)):
            with self.subTest(header=header,artifacts=artifacts),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=OrphanServer116(base,header=header,artifacts=artifacts)
                result=self.run_client(server,base,dest);ledger=result['ledger']
                self.assertEqual([server.root,CHILD],[r['run_id'] for r in ledger['runs']],
                    'the published diagnostic child must remain in the campaign index')
                self.assertTrue(ledger.get('collection_complete',False))
                self.assertFalse(ledger['complete']);self.assertEqual('stopped',ledger['state'])
                row=ledger['runs'][-1]
                self.assertFalse(row['verified']);self.assertTrue(row['diagnostic_only'])
                self.assertEqual(dict(scope='manifest_files_and_artifact_inventory',
                    opaque_uncommitted_bytes='device_retained_not_transferred'),row.get('diagnostic_collection'),
                    'diagnostic closure cannot claim transfer of opaque uncommitted fragments')
                self.assertEqual(('unknown',False),(row['outcome'],row['assessment_adopted']))
                self.assertEqual('campaign_terminal_missing',row['verification_error'])
                self.assertEqual(4,ledger['native_status']['input_state'])
                self.assertTrue(ledger['native_status']['ui_frozen'])
                self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))
                self.assertTrue(all(m['published'] for m in server.models.values()))
                self.assertTrue(result['campaign_archive'].is_file())

    def test_same_root_recovery_closes_then_only_a_later_explicit_call_starts(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=OrphanServer116(base,header=False);first=self.run_client(server,base,dest)
            self.assertTrue(first['ledger'].get('collection_complete',False))
            snapshots={r['archive_name']:(dest/'runtime'/r['archive_name']).read_bytes() for r in first['ledger']['runs']}
            server.calls.clear()
            recovered=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            self.assertTrue(recovered['ledger']['collection_complete']);self.assertFalse(recovered['ledger']['complete'])
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))
            self.assertEqual(snapshots,{n:(dest/'runtime'/n).read_bytes() for n in snapshots})
            old_root=server.root;server.calls.clear();server.orphan_enabled=False;server.after_models=None;server.polls=0
            # Native reserves a fresh UUID across roots; the old fixture's
            # fixed second UUID cannot name another child in this namespace.
            with patch.object(baseline,'SECOND','c'*32):
                fresh=self.run_client(server,base,dest)
            self.assertNotEqual(old_root,server.root);self.assertTrue(fresh['ledger']['complete'])
            self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))

    def test_foreign_or_unreserved_parent_link_never_closes_collection(self):
        for field,value in (('run_id','c'*32),('root_id','c'*32),('predecessor_id','c'*32),
                            ('index',True),('slot_bytes',1),('token_id','invalid')):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=OrphanServer116(base)
                def tamper(server):
                    parent=server.models[server.root]
                    item=next(r for r in parent['manifest']['records'] if r['kind']=='continuation_reservation')
                    body=json.loads(parent['records'][item['sequence']]);body['payload'][field]=value
                    baseline.replace_fixture_record(parent,item['sequence'],body)
                    seal=next(r for r in parent['manifest']['records'] if r['kind']=='continuation_seal')
                    terminal=next(r for r in parent['manifest']['records'] if r['kind']=='terminal')
                    body=json.loads(parent['records'][seal['sequence']]);body['payload']['terminal_sha256']=terminal['sha256']
                    baseline.replace_fixture_record(parent,seal['sequence'],body)
                server.tamper=tamper
                result=self.run_client(server,base,dest)
                self.assertFalse(result['ledger']['collection_complete'])
                self.assertFalse(any(r['diagnostic_only'] for r in result['ledger']['runs']))
                self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))

    def test_child_session_identity_and_owner_must_match_the_linked_parent(self):
        for field,value in (('owner_sha256','c'*64),('root_id','c'*32),('predecessor_id','c'*32)):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=OrphanServer116(base,header=True,artifacts=False)
                def tamper(server):
                    model=server.models[CHILD];body=json.loads(model['records'][0])
                    if field=='owner_sha256':body[field]=value
                    else:body['provenance']['continuous_campaign'][field]=value
                    raw=cycle.canonical(body);model['records'][0]=raw
                    model['manifest']['records'][0].update(bytes=len(raw),sha256=sha(raw))
                    model['manifest']['total_bytes']=len(raw)
                server.tamper=tamper
                result=self.run_client(server,base,dest)
                self.assertFalse(result['ledger']['collection_complete'])
                self.assertFalse(any(r['diagnostic_only'] for r in result['ledger']['runs']))

    def test_existing_game_terminal_and_raw_evidence_are_not_an_orphan_fallback(self):
        for kind in ('terminal','frame','raw_artifact'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=OrphanServer116(base)
                def tamper(server):
                    if kind in ('terminal','frame'):
                        model=baseline.campaign_model(CHILD,server.root,1,server.root,None)
                        keep={'session','terminal'} if kind=='terminal' else {'session','frame'}
                        rows=[r for r in model['manifest']['records'] if r['kind'] in keep]
                        model['records']={r['sequence']:model['records'][r['sequence']] for r in rows}
                        images=model['manifest']['images'] if kind=='frame' else []
                        model['manifest'].update(records=rows,images=images,complete=False,interrupted=True,
                            input_state=4,ui_frozen=True,total_bytes=sum(r['bytes'] for r in rows)+sum(r['bytes'] for r in images))
                        server.models[CHILD]=model
                    else:
                        model=server.models[CHILD];body=json.loads(model['records'][557])
                        a=body['artifacts'][0];a.update(name='frame-0000000000000001.rgba',kind='raw')
                        a['id']=sha(a['name'].encode());raw=cycle.canonical(body);model['records'][557]=raw
                        row=next(r for r in model['manifest']['records'] if r['kind']=='artifacts')
                        row.update(bytes=len(raw),sha256=sha(raw));model['manifest']['total_bytes']=sum(map(len,model['records'].values()))
                server.tamper=tamper
                result=self.run_client(server,base,dest)
                self.assertFalse(result['ledger']['collection_complete'])
                self.assertFalse(any(r['diagnostic_only'] for r in result['ledger']['runs']))

    def test_closed_diagnostic_zip_loss_blocks_a_later_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=OrphanServer116(base);first=self.run_client(server,base,dest)
            self.assertTrue(first['ledger']['collection_complete'])
            path=base.parent/('.'+base.name+'-publication')/(CHILD+'.zip')
            path.write_bytes(path.read_bytes()+b'changed');server.calls.clear()
            with self.assertRaisesRegex(ProbeError,'cycle_archive_changed'):
                self.run_client(server,base,dest)
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))

    def test_physical_evidence_failure_stays_pending_without_a_diagnostic_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=OrphanServer116(base);call=server.call
            def unavailable(method,params):
                if params.get('run_id')==CHILD and params.get('mode')=='manifest':
                    raise baseline.RemoteRpcError(-32096,'unclassified',True)
                return call(method,params)
            server.call=unavailable
            result=self.run_client(server,base,dest)
            self.assertFalse(result['ledger']['collection_complete'])
            self.assertFalse(any(r['diagnostic_only'] for r in result['ledger']['runs']))
            self.assertEqual('cycle_evidence_storage_unavailable',result['ledger']['last_error'])
            self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))

    def test_diagnostic_entry_reports_collection_instead_of_a_gameplay_success(self):
        from necroprobe import test116 as entry
        from necroprobe import campaign116 as campaign
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            result=self.run_client(OrphanServer116(base),base,dest);output=io.StringIO()
            with patch.object(Path,'home',return_value=dest),\
                    patch.object(entry,'load_pairing',return_value=(baseline.KEY,baseline.TOK)),\
                    patch.object(campaign,'run',return_value=result),redirect_stdout(output):
                self.assertEqual(0,entry.main(['--until-target','--python-crypto']))
            self.assertIn('診断記録と一覧を保存しました',output.getvalue())
            self.assertIn('未確定の記録片は端末に残しています',output.getvalue())
            self.assertIn('ゲームの判定完了とは区別',output.getvalue())
            self.assertNotIn('--recovery',output.getvalue())

    def test_lost_closed_selector_does_not_bypass_the_zip_check_before_new_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=OrphanServer116(base);first=self.run_client(server,base,dest)
            self.assertTrue(first['ledger']['collection_complete'])
            (base/'continuous-campaign.json').unlink()
            path=base.parent/('.'+base.name+'-publication')/(CHILD+'.zip')
            path.write_bytes(path.read_bytes()+b'changed');server.calls.clear()
            try:self.run_client(server,base,dest)
            except ProbeError:pass
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls),
                'a missing selector cannot erase the closed history archive obligation')

    def test_reservation_must_precede_the_actual_restart_intent(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=OrphanServer116(base)
            def late(server):
                model=server.models[server.root]
                normal=[(r,copy.deepcopy(json.loads(model['records'][r['sequence']])))
                    for r in model['manifest']['records'] if 0<r['sequence']<513]
                reservation=next(value for value in normal if value[0]['kind']=='continuation_reservation')
                normal=[value for value in normal if value[0]['kind']!='continuation_reservation']
                pos=next(i for i,value in enumerate(normal) if value[0]['kind']=='terminal')
                normal.insert(pos,reservation);rechain_parent(model,server.root,normal)
            server.tamper=late
            result=self.run_client(server,base,dest)
            self.assertFalse(result['ledger']['collection_complete'],
                'a reservation created after RS cannot prove the required pre-RS capacity bound')


if __name__=='__main__':
    unittest.main()
