"""TEST083 selector keeps exact inventories, source binding and Green execution."""
from pathlib import Path
import importlib.util
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def runner_module():
    spec = importlib.util.spec_from_file_location('device_host_runner083', HERE/'run_test083_host.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case(name='test_one', result='green'):
    def test(self):
        if result=='skip': self.skipTest('not executed')
        elif result=='failure': self.fail('semantic failure')
        elif result=='error': raise RuntimeError('setup/compiler failure')
    return type('Selected', (unittest.TestCase,), {name:test})(name)


class DeviceHostSelection083Tests(unittest.TestCase):
    def test_empty_duplicate_or_unexpected_method_inventory_is_rejected(self):
        runner = runner_module()
        for name in (*[prefix+'CONTROLLER' for prefix in runner.FIXTURE_OVERRIDE_PREFIXES], 'BASELINE_NAV', 'NECRO_TEST083_FRAMING_BASELINE_CORE'):
            with self.subTest(empty_override=name), patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()
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
                self.assertTrue((output/'test083-host-scope.json').is_file())
