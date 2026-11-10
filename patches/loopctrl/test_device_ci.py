"""The rapid device lane keeps local checks and the real IPA proof boundary."""
from pathlib import Path
import importlib.util
import re
import tempfile
import types
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1] / '.github/workflows/loopctrl-geometry.yml'


def runner_module():
    spec = importlib.util.spec_from_file_location('device_host_runner', HERE/'run_test062_host.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def job_blocks(source):
    jobs = source.split('\njobs:\n', 1)[1]
    marks = list(re.finditer(r'^  ([a-z0-9-]+):\n', jobs, re.MULTILINE))
    return {m.group(1): jobs[m.start():marks[i+1].start() if i+1<len(marks) else len(jobs)]
            for i,m in enumerate(marks)}


class DeviceNativeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.source = WORKFLOW.read_text()
        self.jobs = job_blocks(self.source)

    def test_default_native_lane_is_device(self):
        trigger = self.source.split('\npermissions:',1)[0]
        self.assertIn('        default: device\n', trigger)
        self.assertIn('options: [device, focused, full, test058-red, test058-quick]', trigger)
        self.assertNotRegex(trigger, r'(?m)^  push:')

    def test_device_uses_only_selected_host_contracts_before_the_existing_build(self):
        host = self.jobs['test061-host-contracts']
        self.assertIn("inputs.native_lane == 'device'", host)
        self.assertIn('run_test062_host.py', host)
        self.assertIn('"$NATIVE_HOST_RUNNER" driver upstream', host)
        build = self.jobs['focused-build']
        self.assertIn("inputs.native_lane == 'device'", build)
        self.assertIn('needs: [native-source-ready, test061-host-contracts]', build)
        self.assertNotIn('native-host-contracts', build)

    def test_device_gates_broad_synthetic_and_unchanged_rpc_tests(self):
        build = self.jobs['focused-build']
        names = ['Run actual Runtime TEST061 public integration fixtures',
                 'Detect TEST061 boundary rollback faults',
                 'Run independent actual Runtime shop world16 endpoint',
                 'Run actual LoopCtrlKit API and capability contracts']
        for name in names:
            self.assertIn('- name: '+name+"\n        if: inputs.native_lane != 'device'\n", build)

    def test_device_still_builds_and_verifies_actual_ipa_without_a_condition(self):
        build = self.jobs['focused-build']
        for name in ['Generate and inspect actual source-specific project configuration',
                     'Build and package unsigned IPA',
                     'Verify actual source-specific Perception compiler profile',
                     'Verify package and record provenance', 'Save unsigned IPA']:
            block = build.split('- name: '+name+'\n',1)[1].split('      - ',1)[0]
            self.assertNotIn('        if:', block, name)
        self.assertIn('make ipa UNSIGNED=1', build)
        self.assertIn('check_perception_build.py --compile-profile upstream', build)
        self.assertIn('verify_package.py upstream driver upstream/release/LoopCtrl.ipa', build)
        self.assertIn('if: always()\n        env:\n          NATIVE_ARG_PROOF:', build)
        self.assertIn('upstream/LoopCtrl.xcodeproj/project.pbxproj', build)
        self.assertIn('${{ runner.temp }}/ngg2/perception-build/', build)


def case(name='test_one', result='green'):
    def test(self):
        if result=='skip': self.skipTest('not executed')
        elif result=='failure': self.fail('semantic failure')
        elif result=='error': raise RuntimeError('setup/compiler failure')
    return type('Selected', (unittest.TestCase,), {name:test})(name)


class DeviceHostSelectionTests(unittest.TestCase):
    def test_empty_duplicate_or_unexpected_method_inventory_is_rejected(self):
        runner = runner_module()
        for values in ([], [case(),case()]):
            with self.subTest(count=len(values)),self.assertRaises(ValueError):
                runner.selected_cases(values)
        for missing,extra in ((True,False),(False,True)):
            methods={'test_expected'}
            if missing: methods.clear()
            if extra: methods.add('test_unregistered')
            klass=type('Selected',(unittest.TestCase,),{m:(lambda self:None) for m in methods})
            with self.subTest(missing=missing,extra=extra),self.assertRaises(ValueError):
                runner.method_cases(klass,{'test_expected'},exact=True)

    def test_all_core_bindings_precede_method_selection_and_no_world_suite_is_loaded(self):
        runner=runner_module();modules={}
        for name,class_name,_,methods,exact in runner.NATIVE_CASES:
            klass=type(class_name,(unittest.TestCase,),{m:(lambda self:None) for m in methods})
            modules[name]=types.SimpleNamespace(**{class_name:klass})
        for name in runner.CORE_MODULES:
            modules.setdefault(name,types.SimpleNamespace())
        original=runner.method_cases; calls=[]
        def selected(klass,methods,exact=False):
            self.assertTrue(all(m.CORE==Path('/patched/LoopCtrlUITests') for m in modules.values()))
            calls.append(klass.__name__)
            return original(klass,methods,exact=exact)
        with patch.object(runner.importlib,'import_module',side_effect=modules.__getitem__), \
                patch.object(runner,'method_cases',side_effect=selected):
            suites=runner.native_suites(Path('/patched'))
        self.assertEqual(len(calls),len(runner.NATIVE_CASES))
        self.assertEqual(len(suites),len(runner.NATIVE_CASES))
        self.assertNotIn('test_native_goal_world',' '.join(modules))
        self.assertNotIn('test_native_recovery_world',' '.join(modules))

    def test_selected_cases_must_execute_green_without_skip_or_error(self):
        runner=runner_module()
        for result in ('green','failure','error','skip'):
            with self.subTest(result=result),tempfile.TemporaryDirectory() as directory,patch('builtins.print'):
                output=Path(directory);record={}
                if result=='green': runner.run_scope('unit',[case(result=result)],output,record)
                else:
                    with self.assertRaises(RuntimeError):
                        runner.run_scope('unit',[case(result=result)],output,record)
                self.assertEqual(record['unit']['tests_run'],1)
                self.assertTrue((output/'test062-host-scope.json').is_file())


if __name__=='__main__': unittest.main()
