from pathlib import Path
import shlex
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from libs.ansible.modules_utils.remote_client import _parse_gateway_args
from ops.ansible.inventory import JMSInventory, shell_join


class GatewayCredentialTests(SimpleTestCase):
    def test_gateway_password_is_private_and_absent_from_command_arguments(self):
        password = "dummy 'quoted' $password 50%% 中文"
        gateway = SimpleNamespace(
            username='gateway', address='127.0.0.1', port=2223,
            private_key=None, password=password,
        )
        inventory = object.__new__(JMSInventory)
        for use_nc in (False, True):
            with self.subTest(nc=use_nc), TemporaryDirectory(prefix="gateway '50% ") as root, \
                    patch.object(inventory, 'get_gateway_ssh_settings', return_value={'nc': use_nc}):
                args = inventory.make_proxy_command(gateway, root)['ansible_ssh_common_args']
                proxy = shlex.split(shlex.split(args)[1].removeprefix('ProxyCommand='))
                self.assertEqual(proxy[:2], ['sshpass', '-f'])
                self.assertNotIn(password, args)
                password_file = Path(proxy[2].replace('%%', '%'))
                self.assertEqual(password_file.parent, Path(root))
                self.assertEqual(password_file.stat().st_mode & 0o777, 0o600)
                self.assertEqual(password_file.read_text(), password)
                self.assertEqual(_parse_gateway_args(args), {
                    'password': password, 'username': 'gateway', 'remote_addr': '127.0.0.1',
                    'port': 2223, 'key_path': None,
                })

    def test_gateway_parser_keeps_legacy_arguments_and_rejects_missing_password_file(self):
        command = shell_join(['sshpass', '-p', 'literal%%%%password',
                              'ssh', '-i', '/private/key', '-p', '2223', '--', 'user@gateway'])
        parsed = _parse_gateway_args('-o ' + shlex.quote('ProxyCommand=' + command))
        self.assertEqual(parsed['password'], 'literal%%password')
        self.assertEqual(parsed['key_path'], '/private/key')
        with TemporaryDirectory() as root:
            command = shell_join(['sshpass', '-f', root + '/missing', 'ssh', '--', 'user@gateway'])
            with self.assertRaises(FileNotFoundError):
                _parse_gateway_args('-o ' + shlex.quote('ProxyCommand=' + command))
