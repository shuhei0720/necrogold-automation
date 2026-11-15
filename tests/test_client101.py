"""TEST101 literal wrappers route the unchanged finite campaign safely.

Before those wrappers exist, use the actual TEST100 wrappers as the baseline.
The resulting wrong-spool/module assertions are behavioral Red, not imports.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import campaign099 as campaign
from necroprobe import native_cycle as cycle
from necroprobe import native_walk, test099, test100
from test_campaign099 import CampaignServer
from test_protocol import KEY, TOK

if importlib.util.find_spec('necroprobe.test101') is not None:
    from necroprobe.test101 import main as entry101
else:
    entry101 = test100.main


class Client101Tests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='client101-');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.destination=self.root/'mounted';self.destination.mkdir()

    def test_entry101_isolates_labels_and_recovers_same_uuid_without_continuing(self):
        base=self.root/'.necroprobe'/'runtime'/'test-101'
        old=[]
        for label in ('test-099','test-100'):
            sentinel=base.parent/label/'keep';sentinel.parent.mkdir(parents=True)
            sentinel.write_bytes(label.encode());old.append((sentinel,sentinel.read_bytes()))
        server=CampaignServer(base,cases=['negative_limit']);server.fail_export=True
        original=campaign.run;results=[];calls=[]
        def run(client,destination,**kwargs):
            self.assertEqual(base,kwargs['spool'],'TEST101 must not reuse the TEST100 local identity')
            calls.append(dict(kwargs))
            value=original(client,destination,**kwargs);results.append(value)
            return value
        lock=native_walk.device_lock
        def locks(path=None):return lock(path or self.root/'device.lock')
        with patch.object(test099,'load_pairing',return_value=(KEY,TOK)), \
             patch.object(test099,'TrialClient099',return_value=server), \
             patch.object(test099.campaign,'run',side_effect=run), \
             patch.object(test099.Path,'home',return_value=self.root), \
             patch.object(test099.Path,'cwd',return_value=self.destination), \
             patch('necroprobe.native_cycle.device_lock',locks):
            first=io.StringIO()
            with contextlib.redirect_stdout(first):self.assertEqual(2,entry101(['--until-target']))
            self.assertTrue(calls[0]['until_target']);self.assertFalse(calls[0]['recovery_only'])
            self.assertIn('TEST-101:',first.getvalue())
            original_id=cycle.load_journal(base)['run_id']
            recovered=io.StringIO()
            with contextlib.redirect_stdout(recovered):self.assertEqual(0,entry101(['--recovery']))
            self.assertFalse(calls[1]['until_target']);self.assertTrue(calls[1]['recovery_only'])
            self.assertIn('TEST-101:',recovered.getvalue())
        starts=[params['run_id'] for method,params in server.calls if method=='necro_native_start']
        self.assertEqual([original_id],starts)
        result=results[-1];ledger=result['ledger'];row=ledger['runs'][-1]
        self.assertEqual('stopped',ledger['state']);self.assertTrue(ledger['complete'])
        self.assertIsNone(ledger['pending_run_id'])
        self.assertEqual('test-101-'+original_id+'.zip',row['archive_name'])
        self.assertEqual(row['archive_name'],result['archive'].name)
        self.assertTrue(result['campaign_archive'].name.startswith('test-101-campaign-'))
        with zipfile.ZipFile(result['campaign_archive']) as saved:
            self.assertEqual(['campaign-index.json','last-run/'+row['archive_name']],saved.namelist())
            self.assertEqual(ledger,json.loads(saved.read('campaign-index.json')))
            with zipfile.ZipFile(io.BytesIO(saved.read('last-run/'+row['archive_name']))) as full:
                self.assertTrue(all(name.startswith('test-101/') for name in full.namelist()))
                self.assertIsNone(full.testzip())
        for sentinel,raw in old:self.assertEqual(raw,sentinel.read_bytes())

    def test_shell101_checks_own_module_and_rejects_conflicting_modes_before_start(self):
        root=Path(__file__).resolve().parents[1]
        shell=root/'test_101.sh'
        if not shell.exists():shell=root/'test_100.sh'
        binaries=self.root/'bin';binaries.mkdir();arguments=self.root/'arguments'
        python=binaries/'python3'
        python.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TASK101_CAPTURE_PATH"\nprintf "unsupported\\n"\n')
        python.chmod(0o700)
        environment=dict(os.environ,PATH=str(binaries)+os.pathsep+os.environ.get('PATH',''),
                         TASK101_CAPTURE_PATH=str(arguments))
        result=subprocess.run(['sh',str(shell),'--until-target'],env=environment,capture_output=True,text=True)
        self.assertEqual(1,result.returncode)
        self.assertEqual(['-m','necroprobe.test101','--check'],arguments.read_text().splitlines(),
                         'TEST101 shell must select the101 module before any keeper or game start')
        self.assertIn('TEST-101:',result.stderr)
        arguments.unlink()
        result=subprocess.run(['sh',str(shell),'--until-target','--recovery'],env=environment,
                              capture_output=True,text=True)
        self.assertEqual(2,result.returncode)
        self.assertIn('TEST-101:',result.stderr)
        self.assertFalse(arguments.exists(),'conflicting modes must stop before invoking the Python entry')


if __name__=='__main__':unittest.main()
