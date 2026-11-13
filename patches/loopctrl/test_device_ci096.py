"""TEST096 finite selector, preserved source and bounded Runtime lane contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1]/'.github/workflows/loopctrl-geometry.yml'


def runner_module():
    spec=importlib.util.spec_from_file_location('device_host_runner096',HERE/'run_test096_host.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def one_case(outcome='green'):
    def test(self):
        if outcome=='skip':self.skipTest('not executed')
        elif outcome=='failure':self.fail('semantic failure')
        elif outcome=='error':raise RuntimeError('environment failure')
    return type('Selected',(unittest.TestCase,),{'test_one':test})('test_one')


class DeviceHostSelection096Tests(unittest.TestCase):
    def test_device_lane_096_replaces_only_obsolete_pause_fixture_with_current_boundaries(self):
        source=WORKFLOW.read_text()
        host=source.split('  test061-host-contracts:\n',1)[1].split('  focused-build:\n',1)[0]
        for version in ('094','095','096'):
            self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test'+version+'_host.py',host)
        self.assertIn('device_profile: ${{ steps.host_contracts.outputs.device_profile }}',host)
        self.assertLess(host.index('DEVICE_PROFILE=095'),host.index('DEVICE_PROFILE=096'))
        self.assertLess(host.index('"$NATIVE_HOST_RUNNER" driver upstream'),host.index('device_profile=$DEVICE_PROFILE'))
        self.assertIn('set -euo pipefail',host)
        build=source.split('  focused-build:\n',1)[1].split('\n  build:\n',1)[0]
        decoder=build.split('- name: Install TEST094 focused Swift fixture image decoder\n',1)[1].split('      - ',1)[0]
        self.assertIn("        if: inputs.native_lane == 'device'\n",decoder)
        base="if: inputs.native_lane == 'device' && !cancelled() && steps.cycle_fixture_env.outcome == 'success'"
        for title in ('Verify TEST094 actual authenticated owner and public cycle schema',
            'Verify TEST094 immutable spool and actual filesystem fault boundaries',
            'Verify TEST094 immutable terminal export and exact image roundtrip'):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertIn(base+'\n',block)
            self.assertNotIn('continue-on-error:',block)
        old=build.split('- name: Verify TEST094 selected actual Runtime cycle callbacks\n',1)[1].split('      - ',1)[0]
        self.assertIn(base+" && needs.test061-host-contracts.outputs.device_profile != '096'",old)
        self.assertIn('check_runtime_cycle094.py',old)
        previous=build.split('- name: Verify TEST095 target-only Runtime and policy wire callbacks\n',1)[1].split('      - ',1)[0]
        self.assertIn("device_profile == '095'",previous)
        target=build.split('- name: Verify TEST096 bounded pre-PAUSE Runtime adoption callbacks\n',1)[1].split('      - ',1)[0]
        self.assertIn(base+" && needs.test061-host-contracts.outputs.device_profile == '096'",target)
        self.assertIn('check_runtime_pause096.py',target)
        self.assertIn('--fault-red',target)
        self.assertIn('test096-runtime',target)
        self.assertNotIn('continue-on-error:',target)
        self.assertIn('${{ runner.temp }}/test096-runtime/',build)
        self.assertIn('fetch-depth: 0',build)
        for title in ('Build and package unsigned IPA','Verify actual source-specific Perception compiler profile',
            'Verify package and record provenance'):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertNotIn('        if:',block)
        self.assertIn('--profile-version 3',build)
        self.assertIn('runs-on: macos-26',build)

    def test_frozen_scope_rejects_empty_duplicate_missing_and_override_cases(self):
        runner=runner_module();runner.ensure_scope()
        with patch.object(runner,'SCOPE_FINALIZED',False),self.assertRaises(ValueError):runner.ensure_scope()
        for rows in ((),(('m','C','dup',frozenset({'test_one'}),True),)*2):
            with patch.object(runner,'CASES',rows),self.assertRaises(ValueError):runner.ensure_scope()
        for cases in ([],[one_case(),one_case()]):
            with self.assertRaises(ValueError):runner.selected_cases(cases)
        klass=type('Selected',(unittest.TestCase,),{'test_one':lambda self:None,'test_extra':lambda self:None})
        for methods in ({'test_missing'},{'test_one'}):
            with self.assertRaises(ValueError):runner.method_cases(klass,methods,exact=True)
        for name in ('BASELINE_NAV','NECRO_TEST096_BASELINE_NAVIGATION','NECRO096_FIXTURE'):
            with patch.dict(runner.os.environ,{name:''}),self.assertRaises(ValueError):runner.reject_fixture_overrides()

    def test_native_delta_cannot_change_protected_wire_header_or_drop_a_source(self):
        runner=runner_module()
        self.assertEqual({'LoopCtrlUITests/NG2Controller.c','LoopCtrlUITests/NG2Navigation.c',
                          'LoopCtrlUITests/NG2Ring.c','LoopCtrlUITests/NG2Runtime.swift'},set(runner.EXPECTED_NATIVE_CHANGES))
        before={'allowed':'a','retained':'r'}
        self.assertEqual({'allowed'},runner.native_delta(before,{'allowed':'b','retained':'r'},{'allowed'}))
        for current in ({'allowed':'b','retained':'changed'},{'allowed':'b'},{'allowed':'b','retained':'r','extra':'x'}):
            with self.assertRaises(ValueError):runner.native_delta(before,current,{'allowed'})
        original=b'preserved source'
        self.assertEqual(runner.sha(original),runner.retained_identity(original,original,runner.sha(original)))
        with self.assertRaises(ValueError):runner.retained_identity(original+b'x',original)
        self.assertIn('patches/loopctrl/check_runtime_cycle094.py',runner.PRESERVED_REPOSITORY)
        self.assertIn('patches/loopctrl/check_runtime_target_only095.py',runner.PRESERVED_REPOSITORY)
        self.assertIn('necroprobe/cycle_publication.py',runner.PRESERVED_REPOSITORY)
        self.assertEqual(('necroprobe/test096.py','test_096.sh'),runner.PRODUCT_PATHS)

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
                self.assertEqual(1,evidence['unit']['tests_run']);self.assertTrue((out/'test096-host-scope.json').is_file())
        with tempfile.TemporaryDirectory() as temporary,self.assertRaises(ValueError):runner.run_scope('empty',[],Path(temporary),{})


if __name__=='__main__':unittest.main()
