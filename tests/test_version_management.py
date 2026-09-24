"""Version commands run against temporary copies, never the working project."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('version_manager', ROOT / 'scripts/version.py')
versions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(versions)


class VersionManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for filename in versions.TARGETS:
            shutil.copy2(ROOT / filename, self.root / filename)
        self.config = {'app_info': {'version': '1.2.3', 'developer': 'Test'},
                       'active_data_file': 'data/private.enc', 'security': {'dev_pin': 'test'}}
        (self.root / 'config.json').write_text(json.dumps(self.config))
        with contextlib.redirect_stdout(io.StringIO()):
            versions.synchronize(self.root)

    def run_command(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return versions.main(list(args), root=self.root)

    def test_check_detects_mismatch_and_sync_repairs_it(self):
        installer = self.root / 'AllManagerC.iss'
        installer.write_text(installer.read_text().replace('1.2.3', '9.9.9'))
        before = installer.read_bytes()
        self.assertEqual(self.run_command('status'), 0)
        self.assertEqual(self.run_command('check'), 1)
        self.assertEqual(installer.read_bytes(), before)
        self.assertEqual(self.run_command('sync'), 0)
        self.assertEqual(self.run_command('check'), 0)

    def test_bump_resets_lower_components(self):
        for level, expected in [('patch', '1.2.4'), ('minor', '1.3.0'), ('major', '2.0.0')]:
            with self.subTest(level=level):
                self.assertEqual(self.run_command('set', '1.2.3'), 0)
                self.assertEqual(self.run_command('bump', level), 0)
                self.assertEqual(versions.load_config(self.root)['app_info']['version'], expected)
                self.assertEqual(self.run_command('check'), 0)

    def test_set_preserves_profile_fields(self):
        self.assertEqual(self.run_command('set', '6.10.0'), 0)
        actual = versions.load_config(self.root)
        self.assertEqual(actual['security'], self.config['security'])
        self.assertEqual(actual['active_data_file'], self.config['active_data_file'])
        self.assertEqual(actual['app_info']['developer'], 'Test')
        self.assertIn('release_date', actual['app_info'])
        self.assertEqual(self.run_command('check', '--tag', 'v6.10.0'), 0)
        self.assertEqual(self.run_command('check', '--tag', 'v6.1.0'), 1)

    def test_rejects_invalid_versions_without_writing(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        for invalid in ('1.2', 'v1.2.3', '-1.2.3', '01.2.3', '1.2.3-rc1'):
            self.assertEqual(self.run_command('set', '--', invalid), 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_missing_marker_fails_before_any_write(self):
        (self.root / 'README_ru.md').write_text('No version badge\n')
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(self.run_command('set', '2.0.0'), 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_sync_is_idempotent_and_preserves_dates(self):
        self.assertEqual(self.run_command('sync', '3.4.5'), 0)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        self.assertEqual(self.run_command('sync'), 0)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()})

    def test_cli_resolves_root_from_another_working_directory(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        shutil.copy2(ROOT / 'scripts/version.py', scripts / 'version.py')
        result = subprocess.run([sys.executable, str(scripts / 'version.py'), 'check'],
                                cwd=scripts, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
