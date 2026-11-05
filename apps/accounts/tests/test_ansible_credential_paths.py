import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import uuid

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from accounts.models import Account


class AnsibleCredentialPathTests(SimpleTestCase):
    def test_become_key_is_written_into_the_task_directory(self):
        login = Account(username='login', secret_type='ssh_key', secret='test-private-key')
        account = Account(username='target', secret_type='password', secret='target-password',
                          su_from=login)
        account.platform = SimpleNamespace(su_enabled=True, ansible_become_method='su')
        with TemporaryDirectory() as root:
            auth = account.get_ansible_become_auth(path_dir=root)
            key = Path(auth['ansible_ssh_private_key_file'])
            self.assertEqual(key.parent, Path(root))
            self.assertEqual(key.read_text(), login.secret)
            self.assertEqual(key.stat().st_mode & 0o777, 0o400)
            self.assertEqual(auth['ansible_become_password'], account.secret)
            with override_settings(PROJECT_DIR=root):
                (Path(root) / 'tmp').mkdir()
                legacy = account.get_ansible_become_auth()
                self.assertEqual(Path(legacy['ansible_ssh_private_key_file']).parent,
                                 Path(root) / 'tmp')

    def test_ssh_wrapper_uses_the_session_temporary_directory(self):
        wrapper = Path(settings.APPS_DIR) / 'ops/ansible/serialized_ssh.py'
        with TemporaryDirectory() as root:
            result = subprocess.run(
                [sys.executable, str(wrapper), '-o', 'HostName=' + uuid.uuid4().hex, '-V'],
                env={**os.environ, 'TMPDIR': root}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list(Path(root).glob('jumpserver-ansible-ssh-*.lock'))), 1)
