"""Verify packaged key persistence without touching the installed user's profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackagedStartupTests(unittest.TestCase):
    def test_second_launch_reuses_key_and_data(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            bundle = work / 'bundle'
            bundle.mkdir()
            (bundle / 'config.json').write_text(json.dumps({'app_info': {'version': 'test'}}))
            profile = work / 'profile'
            code = '''
import sys, os, importlib.util
from pathlib import Path
import webview
sys.path.insert(0, sys.argv[1])
sys.frozen = True
sys._MEIPASS = sys.argv[2]
spec = importlib.util.spec_from_file_location('packaged_test', Path(sys.argv[1]) / 'app.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
from app_version import VERSION
assert m.app.config['app_info']['version'] == VERSION
with m.app.test_request_context():
    marker = Path(m.APP_DATA_DIR) / 'first-run.done'
    if marker.exists():
        services = m.load_ai_services()
        assert services[0]['credentials']['password_decrypted'] == 'persistent-password'
    else:
        m.save_ai_services([{'id': 1, 'name': 'Test', 'credentials': {'password': m.encrypt_data('persistent-password')}}])
        marker.touch()
'''
            env = {k: v for k, v in os.environ.items() if k not in {'SECRET_KEY', 'FLASK_SECRET_KEY'} and not k.startswith('YUBIKEY')}
            env['ALLMANAGERC_DATA_DIR'] = str(profile)
            for _ in range(2):
                result = subprocess.run([sys.executable, '-c', code, str(ROOT), str(bundle)], env=env, cwd=work, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                if _ == 0:
                    original_env = (profile / '.env').read_bytes()
                else:
                    self.assertEqual((profile / '.env').read_bytes(), original_env)
            self.assertFalse((work / 'ai_services_schema.json').exists())
