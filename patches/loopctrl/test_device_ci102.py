"""TEST102 finite selector and historical-only unchanged Runtime contracts."""
import importlib.util
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1]/'.github/workflows/loopctrl-geometry.yml'
# Author inventories are source-bound; fixture dependencies do not add test scopes.
EXPECTED_HOST_SCOPES = 15
EXPECTED_HOST_METHODS = 80
EXPECTED_NEW_METHODS = 41


def runner_module():
    spec=importlib.util.spec_from_file_location('device_host_runner102',HERE/'run_test102_host.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def one_case(outcome='green'):
    def test(self):
        if outcome=='skip':self.skipTest('not executed')
        elif outcome=='failure':self.fail('semantic failure')
        elif outcome=='error':raise RuntimeError('environment failure')
    return type('Selected',(unittest.TestCase,),{'test_one':test})('test_one')


class DeviceHostSelection102Tests(unittest.TestCase):
    def test_historical_runtime_policy_rejects_changed_runtime_and_current_execution_claim(self):
        runner=runner_module()
        before={'LoopCtrlUITests/NG2Runtime.swift':runner.UNCHANGED_RUNTIME_SHA256,
            'LoopCtrlUITests/NG2Controller.c':runner.HISTORICAL_CONTROLLER_SHA256}
        current=dict(before,**{'LoopCtrlUITests/NG2Controller.c':'d'*64})
        value=runner.runtime_history_identity(before,current)
        self.assertEqual('historical_only_unchanged_runtime',value['policy'])
        self.assertIs(value['executed_this_run'],False)
        self.assertIs(value['current_controller_execution'],False)
        self.assertIs(value['historical_mac']['executed_this_run'],False)
        self.assertEqual(runner.HISTORICAL_CONTROLLER_SHA256,value['historical_mac']['controller_sha256'])
        self.assertEqual('d'*64,value['current_controller_sha256'])
        for changed in (dict(current,**{'LoopCtrlUITests/NG2Runtime.swift':'0'*64}),before,
            {'LoopCtrlUITests/NG2Runtime.swift':runner.UNCHANGED_RUNTIME_SHA256}):
            with self.assertRaises(ValueError):runner.runtime_history_identity(before,changed)
        bad=dict(before,**{'LoopCtrlUITests/NG2Controller.c':'e'*64})
        with self.assertRaises(ValueError):runner.runtime_history_identity(bad,current)

    def test_device_lane_102_preserves_profiles_and_skips_unchanged_mac_callbacks(self):
        source=WORKFLOW.read_text()
        host=source.split('  test061-host-contracts:\n',1)[1].split('  focused-build:\n',1)[0]
        for version in ('094','095','096','097','098','099','100','101','102'):
            self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test'+version+'_host.py',host)
        self.assertLess(host.index('DEVICE_PROFILE=101'),host.index('DEVICE_PROFILE=102'))
        self.assertIn('set -euo pipefail',host)
        self.assertLess(host.index('"$NATIVE_HOST_RUNNER" driver upstream'),host.index('device_profile=$DEVICE_PROFILE'))
        build=source.split('  focused-build:\n',1)[1].split('\n  build:\n',1)[0]
        for title in ('Install TEST094 focused Swift fixture image decoder',
            'Verify TEST094 actual authenticated owner and public cycle schema',
            'Verify TEST094 immutable spool and actual filesystem fault boundaries',
            'Verify TEST094 immutable terminal export and exact image roundtrip',
            'Verify TEST094 selected actual Runtime cycle callbacks'):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertIn("device_profile != '101'",block)
            self.assertIn("device_profile != '102'",block)
        for title in ('Verify TEST096 bounded pre-PAUSE Runtime adoption callbacks',
            'Verify TEST099 frozen stop diagnostics and qualified handoff callbacks'):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertNotIn("device_profile == '102'",block)
        self.assertNotIn('check_runtime_observation101.py',build)
        self.assertNotIn('check_runtime_observation102.py',build)
        self.assertNotIn('check_runtime_partial100.py',build)
        self.assertIn('fetch-depth: 0',build)
        for title in ('Build and package unsigned IPA','Verify actual source-specific Perception compiler profile',
            'Verify package and record provenance'):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertNotIn('        if:',block)
        self.assertIn('--profile-version 3',build)
        self.assertIn('runs-on: macos-26',build)

    def test_frozen_scope_rejects_empty_duplicate_missing_and_override_cases(self):
        runner=runner_module()
        self.assertTrue(runner.SCOPE_FINALIZED, 'TEST102 final author inventory must be activated')
        runner.ensure_scope()
        self.assertEqual(EXPECTED_HOST_SCOPES,len(runner.CASES))
        self.assertEqual(EXPECTED_HOST_METHODS,sum(len(row[3]) for row in runner.CASES))
        self.assertEqual(EXPECTED_NEW_METHODS,sum(len(row[3]) for row in runner.CASES if row[0].endswith('102')))
        self.assertTrue(runner.REQUIRED_NEW_SCOPES)
        self.assertFalse({'tests.test_native_single_gold086','tests.test_native_terrain_axis091'} & {row[0] for row in runner.CASES})
        with patch.object(runner,'SCOPE_FINALIZED',False),self.assertRaises(ValueError):runner.ensure_scope()
        for rows in ((),(('m','C','dup',frozenset({'test_one'}),True),)*2):
            with patch.object(runner,'CASES',rows),self.assertRaises(ValueError):runner.ensure_scope()
        for cases in ([],[one_case(),one_case()]):
            with self.assertRaises(ValueError):runner.selected_cases(cases)
        klass=type('Selected',(unittest.TestCase,),{'test_one':lambda self:None,'test_extra':lambda self:None})
        for methods in ({'test_missing'},{'test_one'}):
            with self.assertRaises(ValueError):runner.method_cases(klass,methods,exact=True)
        for name in ('BASELINE_NAV','NECRO_TEST102_BASELINE_NAVIGATION','NECRO102_FIXTURE'):
            with patch.dict(runner.os.environ,{name:''}),self.assertRaises(ValueError):runner.reject_fixture_overrides()

    def test_native_delta_baseline_and_preserved_source_helpers_are_closed(self):
        runner=runner_module()
        self.assertEqual({'LoopCtrlUITests/NG2Controller.c','LoopCtrlUITests/NG2Ring.c'},set(runner.EXPECTED_NATIVE_CHANGES))
        self.assertEqual('cb65755b0d4a01ef90cb139b7a53af354f1bad13',runner.NATIVE_BASELINE)
        before={'allowed':'a','retained':'r'}
        self.assertEqual({'allowed'},runner.native_delta(before,{'allowed':'b','retained':'r'},{'allowed'}))
        for current in ({'allowed':'b','retained':'changed'},{'allowed':'b'},{'allowed':'b','retained':'r','extra':'x'}):
            with self.assertRaises(ValueError):runner.native_delta(before,current,{'allowed'})
        original=b'preserved source'
        self.assertEqual(runner.sha(original),runner.retained_identity(original,original,runner.sha(original)))
        with self.assertRaises(ValueError):runner.retained_identity(original+b'x',original)
        for path in ('patches/loopctrl/run_test101_host.py','patches/loopctrl/test_device_ci101.py',
            *runner.shared.PRODUCT_PATHS,*runner.shared.CURRENT_RUNTIME101_MAC_SOURCES):
            self.assertIn(path,runner.PRESERVED_REPOSITORY)
        self.assertEqual(('necroprobe/test102.py','test_102.sh'),runner.PRODUCT_PATHS)
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
                self.assertEqual(1,evidence['unit']['tests_run']);self.assertTrue((out/'test102-host-scope.json').is_file())
        with tempfile.TemporaryDirectory() as temporary,self.assertRaises(ValueError):runner.run_scope('empty',[],Path(temporary),{})


if __name__=='__main__':unittest.main()
