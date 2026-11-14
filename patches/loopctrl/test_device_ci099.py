"""TEST099 finite selector and staged Runtime semantic-Red lane contracts."""
import importlib.util
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1]/'.github/workflows/loopctrl-geometry.yml'
# These author-dependent values must be frozen before the other selector cases run.
EXPECTED_HOST_SCOPES = None
EXPECTED_HOST_METHODS = None
EXPECTED_NEW_METHODS = None


def runner_module():
    spec=importlib.util.spec_from_file_location('device_host_runner099',HERE/'run_test099_host.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def one_case(outcome='green'):
    def test(self):
        if outcome=='skip':self.skipTest('not executed')
        elif outcome=='failure':self.fail('semantic failure')
        elif outcome=='error':raise RuntimeError('environment failure')
    return type('Selected',(unittest.TestCase,),{'test_one':test})('test_one')


class DeviceHostSelection099Tests(unittest.TestCase):
    def test_runtime099_semantic_red_lane_is_standalone_and_retains_named_evidence(self):
        source=WORKFLOW.read_text()
        self.assertIn('test099-runtime-red',source)
        lane=re.split(r'\n  [A-Za-z0-9_-]+:\n',source.split('  test099-runtime-red:\n',1)[1],maxsplit=1)[0]
        self.assertIn("if: inputs.native_lane == 'test099-runtime-red'",lane)
        self.assertIn('runs-on: macos-26',lane)
        self.assertIn('check_runtime099.py',lane)
        self.assertIn('--red-only',lane)
        self.assertIn('test099-runtime-red',lane)
        self.assertIn('if: always()',lane)
        self.assertNotIn('continue-on-error:',lane)
        for excluded in ('xcodebuild', 'check_runtime_pause096.py', 'check_runtime_cycle094.py',
                         'check_ngg2.py', 'Build and package unsigned IPA'):
            self.assertNotIn(excluded,lane)

    def test_device_lane_099_preserves_prior_profiles_and_runs_current_c_callbacks(self):
        source=WORKFLOW.read_text()
        host=source.split('  test061-host-contracts:\n',1)[1].split('  focused-build:\n',1)[0]
        for version in ('094','095','096','097','098','099'):
            self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test'+version+'_host.py',host)
        self.assertLess(host.index('DEVICE_PROFILE=098'),host.index('DEVICE_PROFILE=099'))
        self.assertLess(host.index('"$NATIVE_HOST_RUNNER" driver upstream'),host.index('device_profile=$DEVICE_PROFILE'))
        self.assertIn('set -euo pipefail',host)
        build=source.split('  focused-build:\n',1)[1].split('\n  build:\n',1)[0]
        base="inputs.native_lane == 'device' && !cancelled() && steps.cycle_fixture_env.outcome == 'success'"
        for title in ('Verify TEST094 actual authenticated owner and public cycle schema',
            'Verify TEST094 immutable spool and actual filesystem fault boundaries',
            'Verify TEST094 immutable terminal export and exact image roundtrip'):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertIn('if: '+base+'\n',block)
            self.assertNotIn('continue-on-error:',block)
        old=build.split('- name: Verify TEST094 selected actual Runtime cycle callbacks\n',1)[1].split('      - ',1)[0]
        self.assertIn("device_profile != '096' && needs.test061-host-contracts.outputs.device_profile != '097' && needs.test061-host-contracts.outputs.device_profile != '098' && needs.test061-host-contracts.outputs.device_profile != '099'",old)
        previous=build.split('- name: Verify TEST095 target-only Runtime and policy wire callbacks\n',1)[1].split('      - ',1)[0]
        self.assertIn("device_profile == '095'",previous)
        current=build.split('- name: Verify TEST096 bounded pre-PAUSE Runtime adoption callbacks\n',1)[1].split('      - ',1)[0]
        self.assertIn('if: '+base+" && needs.test061-host-contracts.outputs.device_profile == '096'",current)
        self.assertIn(' || '+base+" && needs.test061-host-contracts.outputs.device_profile == '097'",current)
        self.assertIn(' || '+base+" && needs.test061-host-contracts.outputs.device_profile == '098'",current)
        self.assertIn(' || '+base+" && needs.test061-host-contracts.outputs.device_profile == '099'",current)
        self.assertIn('check_runtime_pause096.py',current)
        self.assertIn('--fault-red',current)
        self.assertIn('test096-runtime',current)
        self.assertNotIn('continue-on-error:',current)
        self.assertIn('${{ runner.temp }}/test096-runtime/',build)
        self.assertNotIn('check_runtime_pause099.py',build)
        trial=build.split('- name: Verify TEST099 frozen stop diagnostics and qualified handoff callbacks\n',1)[1].split('      - ',1)[0]
        self.assertIn('if: '+base+" && needs.test061-host-contracts.outputs.device_profile == '099'",trial)
        self.assertIn('check_runtime099.py',trial)
        self.assertIn('test099-runtime',trial)
        self.assertNotIn('--red-only',trial)
        self.assertNotIn('--fault-red',trial)
        self.assertNotIn('continue-on-error:',trial)
        self.assertIn('${{ runner.temp }}/test099-runtime/',build)
        self.assertIn('fetch-depth: 0',build)
        for title in ('Build and package unsigned IPA','Verify actual source-specific Perception compiler profile',
            'Verify package and record provenance'):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertNotIn('        if:',block)
        self.assertIn('--profile-version 3',build)
        self.assertIn('runs-on: macos-26',build)

    def test_frozen_scope_rejects_empty_duplicate_missing_and_override_cases(self):
        runner=runner_module();runner.ensure_scope()
        self.assertEqual(EXPECTED_HOST_SCOPES,len(runner.CASES))
        self.assertEqual(EXPECTED_HOST_METHODS,sum(len(row[3]) for row in runner.CASES))
        self.assertEqual(EXPECTED_NEW_METHODS,sum(len(row[3]) for row in runner.CASES if row[0].endswith('099')))
        self.assertEqual(3,len(runner.REQUIRED_NEW_SCOPES))
        self.assertNotIn('tests.test_native_single_gold086',{row[0] for row in runner.CASES})
        with patch.object(runner,'SCOPE_FINALIZED',False),self.assertRaises(ValueError):runner.ensure_scope()
        for rows in ((),(('m','C','dup',frozenset({'test_one'}),True),)*2):
            with patch.object(runner,'CASES',rows),self.assertRaises(ValueError):runner.ensure_scope()
        for cases in ([],[one_case(),one_case()]):
            with self.assertRaises(ValueError):runner.selected_cases(cases)
        klass=type('Selected',(unittest.TestCase,),{'test_one':lambda self:None,'test_extra':lambda self:None})
        for methods in ({'test_missing'},{'test_one'}):
            with self.assertRaises(ValueError):runner.method_cases(klass,methods,exact=True)
        for name in ('BASELINE_NAV','NECRO_TEST099_BASELINE_NAVIGATION','NECRO099_FIXTURE'):
            with patch.dict(runner.os.environ,{name:''}),self.assertRaises(ValueError):runner.reject_fixture_overrides()

    def test_native_delta_baseline_and_current_eight_source_nav_snapshot_are_closed(self):
        runner=runner_module()
        self.assertEqual({'LoopCtrlUITests/NG2Controller.c','LoopCtrlUITests/NG2Controller.h','LoopCtrlUITests/NG2Runtime.swift'},set(runner.EXPECTED_NATIVE_CHANGES))
        self.assertEqual('bd5edaa0e2b721926775d75b1004193e5c0e0a85',runner.NATIVE_BASELINE)
        self.assertEqual('c071f41d4a38b4b513d342ea3f3c68f5db8ec067',runner.RUNTIME_BASELINE)
        before={'allowed':'a','retained':'r'}
        self.assertEqual({'allowed'},runner.native_delta(before,{'allowed':'b','retained':'r'},{'allowed'}))
        for current in ({'allowed':'b','retained':'changed'},{'allowed':'b'},{'allowed':'b','retained':'r','extra':'x'}):
            with self.assertRaises(ValueError):runner.native_delta(before,current,{'allowed'})
        original=b'preserved source'
        self.assertEqual(runner.sha(original),runner.retained_identity(original,original,runner.sha(original)))
        with self.assertRaises(ValueError):runner.retained_identity(original+b'x',original)
        for path in ('patches/loopctrl/run_test098_host.py','patches/loopctrl/test_device_ci098.py',*runner.CURRENT_MAC_SOURCES):
            self.assertIn(path,runner.PRESERVED_REPOSITORY)
        self.assertEqual(('necroprobe/trial_evidence099.py','necroprobe/campaign099.py','necroprobe/test099.py','test_099.sh'),runner.PRODUCT_PATHS)
        self.assertIn('necroprobe/native_walk.py',runner.PRESERVED_REPOSITORY)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);upstream=root/'upstream';core=upstream/'LoopCtrlUITests';core.mkdir(parents=True)
            expected={}
            for name in runner.NAV086_FILES:
                raw=('current sealed '+name).encode();(core/name).write_bytes(raw)
                expected['LoopCtrlUITests/'+name]=runner.sha(raw)
            (core/'NG2Ring.h').write_bytes(b'extra current header outside historical eight-file Nav snapshot')
            target=root/'snapshot';identity=runner.nav086_snapshot(upstream,target,expected)
            self.assertEqual(8,identity['files']);self.assertEqual(set(runner.NAV086_FILES),{p.name for p in target.iterdir()})
            self.assertEqual({name:expected['LoopCtrlUITests/'+name] for name in runner.NAV086_FILES},identity['source_sha256'])
            changed=dict(expected);changed['LoopCtrlUITests/NG2Navigation.c']='0'*64
            with self.assertRaises(ValueError):runner.nav086_snapshot(upstream,root/'bad-snapshot',changed)

    def test_sources_have_closed_roots_and_no_symlink_substitution(self):
        runner=runner_module()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'patches/loopctrl/ngg2';folder.mkdir(parents=True)
            (folder/'NG2Ring.h').write_bytes(b'header')
            spec={'source':'NG2Ring.h','sha256':runner.sha(b'header')}
            self.assertEqual(spec['sha256'],runner.addition_identity(root,'LoopCtrlUITests/NG2Ring.h',spec))
            for dest,value in (('../Ring.h',spec),('LoopCtrlUITests/NG2Ring.h',dict(spec,source_root='foreign')),
                ('LoopCtrlUITests/NG2Ring.h',dict(spec,source='../Ring.h'))):
                with self.assertRaises(ValueError):runner.addition_identity(root,dest,value)
            (folder/'NG2Link.h').symlink_to(folder/'NG2Ring.h')
            with self.assertRaises(ValueError):runner.addition_identity(root,'LoopCtrlUITests/NG2Link.h',dict(spec,source='NG2Link.h'))

    def test_empty_skip_failure_error_never_become_current_green_evidence(self):
        runner=runner_module()
        for outcome in ('green','skip','failure','error'):
            with tempfile.TemporaryDirectory() as temporary,patch('builtins.print'):
                out=Path(temporary);evidence={}
                if outcome=='green':runner.run_scope('unit',[one_case(outcome)],out,evidence)
                else:
                    with self.assertRaises(RuntimeError):runner.run_scope('unit',[one_case(outcome)],out,evidence)
                self.assertEqual(1,evidence['unit']['tests_run']);self.assertTrue((out/'test099-host-scope.json').is_file())
        with tempfile.TemporaryDirectory() as temporary,self.assertRaises(ValueError):runner.run_scope('empty',[],Path(temporary),{})


if __name__=='__main__':unittest.main()
