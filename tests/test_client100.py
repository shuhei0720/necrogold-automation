"""Versioned client labels share the finite campaign and recovery contract.

Before the TEST100 entry exists, its explicit fallback is the old TEST099
entry, so wrong routing and archive labels fail assertions, not imports.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import campaign099 as campaign
from necroprobe import native_cycle as cycle
from necroprobe import native_walk, test099
from necroprobe.validation import ProbeError
from test_campaign099 import CampaignServer
from test_protocol import KEY, TOK

if importlib.util.find_spec('necroprobe.test100') is not None:
    from necroprobe.test100 import main as entry100
else:
    entry100 = test099.main


class Client100Tests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='client100-');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.base=self.root/'local'/'test-100';self.base.mkdir(parents=True)
        self.destination=self.root/'mounted';self.destination.mkdir()
        self.server=CampaignServer(self.base,cases=['negative_limit'])

    def invoke(self,**kwargs):
        original=native_walk.device_lock
        def locks(path=None):return original(path or self.root/'device.lock')
        with patch('necroprobe.native_cycle.device_lock',locks):
            return campaign.run(self.server,self.destination,spool=self.base,notice=lambda _:None,**kwargs)

    def assert_labels(self,result,label):
        ledger=result['ledger'];row=ledger['runs'][-1]
        self.assertEqual(label+'-'+row['run_id']+'.zip',row['archive_name'])
        self.assertEqual(row['archive_name'],result['archive'].name)
        returned=result['campaign_archive']
        self.assertTrue(returned.name.startswith(label+'-campaign-'))
        with zipfile.ZipFile(returned) as saved:
            self.assertEqual(['campaign-index.json','last-run/'+row['archive_name']],saved.namelist())
            self.assertEqual(ledger,json.loads(saved.read('campaign-index.json')))
            with zipfile.ZipFile(io.BytesIO(saved.read('last-run/'+row['archive_name']))) as full:
                self.assertTrue(all(name.startswith(label+'/') for name in full.namelist()))
                self.assertIsNone(full.testzip())

    def test_test100_archive_index_and_nested_run_use_separate_label(self):
        result=self.invoke()
        self.assert_labels(result,'test-100')
        self.assertEqual('single',result['stop_reason'])
        self.assertTrue(result['ledger']['complete'])

    def test_test100_interrupted_collection_recovers_same_uuid_and_label(self):
        self.server.fail_export=True
        first=self.invoke(until_target=True)
        original=cycle.load_journal(self.base)['run_id']
        self.assertIsNone(first['archive'])
        recovered=self.invoke(recovery_only=True)
        starts=[params['run_id'] for method,params in self.server.calls if method=='necro_native_start']
        self.assertEqual([original],starts)
        # The interrupted collection already recorded its cancellation intent.
        self.assertEqual('cancelled',recovered['stop_reason'])
        self.assertTrue(recovered['ledger']['complete'])
        self.assertIsNone(recovered['ledger']['pending_run_id'])
        self.assert_labels(recovered,'test-100')

    def test_default_test099_labels_and_recovery_stay_unchanged(self):
        self.base=self.root/'local'/'test-099';self.base.mkdir()
        self.server=CampaignServer(self.base,cases=['negative_limit'])
        first=self.invoke();recovered=self.invoke(recovery_only=True)
        self.assert_labels(first,'test-099');self.assert_labels(recovered,'test-099')
        self.assertEqual(first['ledger']['campaign_id'],recovered['ledger']['campaign_id'])
        starts=[params['run_id'] for method,params in self.server.calls if method=='necro_native_start']
        self.assertEqual([first['ledger']['runs'][0]['run_id']],starts)
        moved=self.root/'local'/'test-100';moved.rmdir()
        shutil.copytree(self.base,moved)
        shutil.copytree(self.base.parent/'.test-099-publication',moved.parent/'.test-100-publication')
        self.base=moved;self.server.base=moved
        rejected=None
        try:self.invoke(recovery_only=True)
        except ProbeError as error:rejected=error.code
        self.assertEqual('campaign_ledger_invalid',rejected,'a copied099 ledger is not a100 campaign')

    def test_test100_entry_routes_own_spool_and_preserves_closed_test_number(self):
        calls=[]
        def run(_client,_destination,**kwargs):
            calls.append(kwargs)
            return dict(ledger=dict(state='pending',runs=[]),stop_reason='pending',record=None,campaign_archive=None)
        with patch.object(test099,'load_pairing',return_value=(KEY,TOK)), \
             patch.object(test099,'TrialClient099',return_value=object()), \
             patch.object(test099.campaign,'run',side_effect=run), \
             patch.object(test099.Path,'home',return_value=self.root):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):self.assertEqual(2,entry100(['--recovery']))
            self.assertEqual(self.root/'.necroprobe'/'runtime'/'test-100',calls[-1]['spool'])
            self.assertTrue(calls[-1]['recovery_only']);self.assertFalse(calls[-1]['until_target'])
            self.assertIn('TEST-100:',output.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(2,test099.main([]))
            self.assertEqual(self.root/'.necroprobe'/'runtime'/'test-099',calls[-1]['spool'])
            for invalid in ('../100','10','１００',100):
                with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                    test099.main([],test_number=invalid)
        root=Path(__file__).resolve().parents[1]
        shell=root/'test_100.sh'
        if not shell.exists():shell=root/'test_099.sh'
        result=subprocess.run(['sh',str(shell),'--until-target','--recovery'],capture_output=True,text=True)
        self.assertEqual(2,result.returncode)
        self.assertIn('TEST-100:',result.stderr)


if __name__=='__main__':unittest.main()
