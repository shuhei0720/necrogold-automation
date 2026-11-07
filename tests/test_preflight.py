"""TEST041: 起動前確認だけを実行し、RPC/worker/keeperは起動しない。"""
import builtins
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import preflight


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'test_041.sh'


def first_guard_command():
    """Actual script's first Python condition; never execute the full script."""
    for line in SCRIPT.read_text().splitlines():
        if line.startswith('if ! python3 '):
            command = shlex.split(line[len('if ! '):].split('; then')[0])
            command[0] = sys.executable
            return command
    raise AssertionError('preflight guard command missing')


class PreflightTests(unittest.TestCase):
    def package(self, folder, version='VERSION = "P1.5"\n', revision='REVISION = "shop-walk-v26"\n'):
        package = Path(folder) / 'necroprobe'
        package.mkdir(exist_ok=True)
        (package / '__init__.py').write_text(version, encoding='utf-8')
        (package / 'shop_walk.py').write_text(revision, encoding='utf-8')
        return package

    def test_script_preflight_never_imports_walking_rpc_or_native_modules(self):
        # sitecustomize is process-local fault injection before the real guard.
        # The same interpreter can import Pillow; package metadata and this entry
        # module are the only necroprobe modules permitted during preflight.
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'sitecustomize.py').write_text(
                "import sys\n"
                "class DenyHeavy:\n"
                " def find_spec(self, fullname, path=None, target=None):\n"
                "  if fullname.startswith('necroprobe.') and fullname != 'necroprobe.preflight':\n"
                "   raise RuntimeError('heavy-import-denied: '+fullname)\n"
                "sys.meta_path.insert(0, DenyHeavy())\n")
            env = dict(os.environ, PYTHONPATH=os.pathsep.join((folder, str(ROOT))))
            result = subprocess.run(first_guard_command(), cwd=ROOT, env=env,
                                    text=True, capture_output=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_source_literals_are_checked_without_executing_probe_source(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'executed'
            revision = ('REVISION = "shop-walk-v26"\n'
                        'from pathlib import Path\n'
                        'Path(%r).write_text("executed")\n'
                        'raise RuntimeError("must not execute")\n') % str(marker)
            package = self.package(folder, revision=revision)
            self.assertTrue(preflight.check_version(package, 'P1.5', 'shop-walk-v26'))
            self.assertFalse(marker.exists())
            self.assertFalse(preflight.check_version(package, 'P1.4', 'shop-walk-v26'))
            self.assertFalse(preflight.check_version(package, 'P1.5', 'shop-walk-v24'))

    def test_missing_duplicate_nested_and_nonliteral_versions_are_rejected(self):
        cases = (
            '', 'OTHER = "shop-walk-v26"\n', 'REVISION = None\n', 'REVISION = 25\n',
            'REVISION = "shop-walk-" + "v25"\n',
            'REVISION = f"shop-walk-v{26}"\n',
            'REVISION = "shop-walk-v26"\nREVISION = "shop-walk-v26"\n',
            'REVISION = "shop-walk-v26"\nREVISION += ""\n',
            'REVISION: str = "shop-walk-v26"\n',
            'REVISION = OTHER = "shop-walk-v26"\n',
            'if True:\n REVISION = "shop-walk-v26"\n',
            'REVISION = "shop-walk-v26"\nif False:\n REVISION = "other"\n',
            'REVISION = "shop-walk-v26"\ndef local():\n REVISION = "other"\n',
        )
        with tempfile.TemporaryDirectory() as folder:
            for text in cases:
                with self.subTest(source=text):
                    package = self.package(folder, revision=text)
                    self.assertFalse(preflight.check_version(package, 'P1.5', 'shop-walk-v26'))
                    # The package VERSION obeys the same literal rules.
                    package = self.package(folder, version=text.replace('REVISION', 'VERSION'))
                    self.assertFalse(preflight.check_version(package, 'P1.5', 'shop-walk-v26'))

    def test_missing_unreadable_malformed_and_oversize_source_rejects_safely(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(preflight.check_version(Path(folder) / 'absent', 'P1.5', 'shop-walk-v26'))
            package = self.package(folder)
            for name in ('__init__.py', 'shop_walk.py'):
                with self.subTest(missing=name):
                    original = (package / name).read_bytes()
                    (package / name).unlink()
                    self.assertFalse(preflight.check_version(package, 'P1.5', 'shop-walk-v26'))
                    (package / name).write_bytes(original)
            with patch.object(Path, 'open', side_effect=OSError('private local path')):
                self.assertFalse(preflight.check_version(package, 'P1.5', 'shop-walk-v26'))
            for raw in (b'\xff', b'REVISION = (', b' ' * (preflight.MAX_SOURCE_BYTES + 1)):
                with self.subTest(raw_prefix=raw[:8]):
                    (package / 'shop_walk.py').write_bytes(raw)
                    self.assertFalse(preflight.check_version(package, 'P1.5', 'shop-walk-v26'))

    def test_main_checks_metadata_before_pillow_and_rejects_invalid_arguments(self):
        with patch.object(preflight, 'check_version', return_value=False) as check, redirect_stderr(io.StringIO()) as errors:
            real_import = builtins.__import__
            pillow = []
            def observed_import(name, *args, **kwargs):
                if name == 'PIL' or name.startswith('PIL.'):
                    pillow.append(name)
                    raise ImportError('must not reach Pillow after invalid metadata')
                return real_import(name, *args, **kwargs)
            with patch.object(builtins, '__import__', side_effect=observed_import):
                self.assertEqual(1, preflight.main(['P1.5', 'shop-walk-v26']))
            self.assertEqual([], pillow)
            self.assertIn('試験は開始していません', errors.getvalue())
            for args in ([], ['P1.5'], ['P1.5', 'shop-walk-v26', 'extra']):
                check.reset_mock()
                self.assertEqual(2, preflight.main(args))
                check.assert_not_called()

    def test_main_dependency_failure_is_clear_without_exposing_exception(self):
        real_import = builtins.__import__
        def no_pillow(name, *args, **kwargs):
            if name == 'PIL' or name.startswith('PIL.'):
                raise ImportError('private dependency failure detail')
            return real_import(name, *args, **kwargs)
        with patch.object(preflight, 'check_version', return_value=True), patch.object(
                builtins, '__import__', side_effect=no_pillow), redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(1, preflight.main(['P1.5', 'shop-walk-v26']))
        self.assertIn('Pillow', errors.getvalue())
        self.assertIn('試験は開始していません', errors.getvalue())
        self.assertNotIn('private dependency', errors.getvalue())

    def test_script_bad_version_stops_before_location_keeper_or_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            package = self.package(folder, revision='REVISION = "wrong-version"\n')
            (package / 'preflight.py').write_bytes((ROOT / 'necroprobe/preflight.py').read_bytes())
            script = Path(folder) / 'test_041.sh'
            script.write_bytes(SCRIPT.read_bytes())
            env = dict(os.environ, PYTHONPATH=folder)
            result = subprocess.run(['sh', str(script)], cwd=ROOT, env=env,
                                    text=True, capture_output=True, timeout=15)
        self.assertEqual(1, result.returncode)
        self.assertIn('指定された版', result.stderr)
        self.assertNotIn('/dev/location', result.stderr)
        self.assertNotIn('継続用プロセス開始', result.stdout)
        text = SCRIPT.read_text()
        self.assertLess(text.index('-m necroprobe.preflight'), text.index('cat /dev/location'))
        self.assertLess(text.index('-m necroprobe.preflight'), text.index('-m necroprobe.shop_walk'))

    def test_script_argument_validation_still_happens_before_preflight(self):
        result = subprocess.run(['sh', str(SCRIPT), '--unsupported'], cwd=ROOT,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(2, result.returncode)
        self.assertIn('引数なし', result.stderr)
        self.assertNotIn('起動前確認', result.stderr)


if __name__ == '__main__':
    unittest.main()
