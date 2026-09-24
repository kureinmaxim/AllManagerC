"""Regression tests in a temporary project; never open the user's databases or keys."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from werkzeug.datastructures import MultiDict

ROOT = Path(__file__).resolve().parents[1]


class UnificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.previous_cwd = Path.cwd()
        for name in ['app.py', 'runtime_paths.py', 'localization.py', 'yubikey_auth.py', 'security_logger.py', 'ai_services_schema.json']:
            shutil.copy2(ROOT / name, cls.work / name)
        for name in ['templates', 'static', 'translations']:
            shutil.copytree(ROOT / name, cls.work / name)
        cls.key = Fernet.generate_key().decode()
        (cls.work / '.env').write_text('SECRET_KEY=' + cls.key + '\n')
        (cls.work / 'config.json').write_text(json.dumps({'app_info': {'version': 'test'}, 'active_data_file': 'data/test.enc'}))
        (cls.work / 'yubikey_config.json').write_text('{"enabled": false, "keys": []}')
        cls.env = patch.dict(os.environ, {'SECRET_KEY': cls.key, 'YUBIKEY_STATIC_PASSWORDS': '', 'YUBIKEY_STATIC_PASSWORD': ''})
        cls.env.start()
        os.chdir(cls.work)
        sys.path.insert(0, str(cls.work))
        spec = importlib.util.spec_from_file_location('unified_app', cls.work / 'app.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.module.app.config.update(TESTING=True, SECRET_KEY='test-session-key')
        cls.module.check_internet_connection = lambda *a, **kw: False

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.previous_cwd)
        sys.path.remove(str(cls.work))
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.m = self.module
        self.m.fernet = Fernet(self.key.encode())
        self.m.SECRET_KEY = self.key
        os.environ['SECRET_KEY'] = self.key
        self.m.app.config['active_data_file'] = 'data/test.enc'
        self.m.yubikey_auth.enabled = False
        self.m.yubikey_auth.keys = []
        self.m.yubikey_auth.static_passwords = []
        (self.work / '.env').write_text('SECRET_KEY=' + self.key + '\n')
        self.client = self.m.app.test_client()
        with self.m.app.test_request_context():
            self.m.save_ai_services([])

    def add(self):
        return self.client.post('/add', data=MultiDict([
            ('name', 'Test Service'), ('provider', 'Example'), ('service_type', 'Other'),
            ('username', 'main'), ('password', 'main-secret'), ('additional_info', 'login note'),
            ('notes', 'service note'), ('extra_username[]', 'second'), ('extra_password[]', 'second-secret'),
            ('extra_username[]', 'third'), ('extra_password[]', 'third-secret'),
        ]))

    def load(self):
        with self.m.app.test_request_context():
            return self.m.load_ai_services()

    def test_create_edit_and_render_accounts(self):
        self.assertEqual(self.add().status_code, 302)
        service = self.load()[0]
        self.assertEqual(service['credentials_list'][0]['password_decrypted'], 'second-secret')
        for path in ['/', '/add', f"/edit/{service['id']}", '/settings', '/help', '/about']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        # Remove the first extra row and leave the remaining password unchanged.
        response = self.client.post(f"/edit/{service['id']}", data=MultiDict([
            ('name', 'Edited'), ('extra_index[]', '1'), ('extra_username[]', 'third-edited'),
            ('extra_password[]', ''), ('additional_info', 'kept note'),
        ]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('highlight_id=', response.location)
        records = self.load()
        self.assertEqual(len(records[0]['credentials_list']), 1)
        self.assertEqual(records[0]['credentials_list'][0]['password_decrypted'], 'third-secret')
        self.assertEqual(records[0]['credentials']['password_decrypted'], 'main-secret')

    def test_saved_data_has_no_plaintext_credentials(self):
        self.add()
        self.load()
        payload = self.m.fernet.decrypt((self.work / 'data/test.enc').read_bytes()).decode()
        self.assertNotIn('_decrypted', payload)
        self.assertNotIn('second-secret', payload)

    def test_external_key_conversion(self):
        self.add()
        other = Fernet(Fernet.generate_key())
        converted = self.m.re_encrypt_service_data(self.load()[0], self.m.fernet, other)
        self.assertEqual(other.decrypt(converted['credentials_list'][0]['password'].encode()), b'second-secret')
        self.assertNotIn('password_decrypted', converted['credentials_list'][0])

    def test_key_rotation_preserves_all_accounts(self):
        self.add()
        new_key = Fernet.generate_key().decode()
        response = self.client.post('/settings/change-key', data={'new_key': new_key, 'confirm_key': new_key})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.m.SECRET_KEY, new_key)
        service = self.load()[0]
        self.assertEqual(service['credentials']['password_decrypted'], 'main-secret')
        self.assertEqual(service['credentials_list'][0]['password_decrypted'], 'second-secret')
        payload = self.m.fernet.decrypt(Path(self.m.get_active_data_path()).read_bytes()).decode()
        self.assertNotIn('_decrypted', payload)

    def test_settings_routes_are_distinct(self):
        endpoints = {'change_main_key': '/settings/change-key', 'verify_key_data': '/settings/verify-key-data', 'generate_new_key': '/settings/generate-key'}
        for rule in self.m.app.url_map.iter_rules():
            if rule.endpoint in endpoints:
                self.assertEqual(rule.rule, endpoints[rule.endpoint])
                self.assertIn('POST', rule.methods)
        self.assertEqual(self.client.post('/settings/generate-key').status_code, 200)

    def test_bulk_delete(self):
        self.add()
        self.assertEqual(self.client.post('/delete-all-services').status_code, 302)
        self.assertEqual(self.load(), [])

    def test_enrolled_key_management_requires_login(self):
        self.m.yubikey_auth.enabled = True
        self.m.yubikey_auth.keys = [{'name': 'test-key', 'client_id': '1', 'secret_key': 'test'}]
        for path in ['/yubikey/setup', '/yubikey/remove/0', '/delete-all-services']:
            response = self.client.post(path)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith('/yubikey/login'))

    def test_windows_data_path_is_portable(self):
        self.m.app.config['active_data_file'] = r'C:\old\project\data\test.enc'
        self.assertEqual(Path(self.m.get_active_data_path()).resolve(), (self.work / 'data/test.enc').resolve())

    def test_github_icon_is_used(self):
        response = self.client.get('/')
        self.assertIn(b'images/ALLc.png', response.data)
        self.assertIn(b'images/icon.ico', response.data)

    def test_interface_language_switch_is_persistent(self):
        for language, html_lang, marker in [('ru', 'ru', 'Настройки'), ('en', 'en', 'Settings'), ('zh', 'zh-Hans', '设置')]:
            response = self.client.get(f'/language/{language}?next=/')
            self.assertEqual(response.status_code, 302)
            page = self.client.get('/').data.decode('utf-8')
            self.assertIn(f'<html lang="{html_lang}"', page)
            self.assertIn(marker, page)
        self.assertEqual(self.client.get('/language/fr').status_code, 404)

    def test_language_redirect_rejects_external_target(self):
        response = self.client.get('/language/en?next=https://example.com')
        self.assertEqual(response.location, '/')


if __name__ == '__main__':
    unittest.main()
