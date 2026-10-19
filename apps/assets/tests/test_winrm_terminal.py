from unittest.mock import patch

from django.test import SimpleTestCase

from assets.const import Protocol
from assets.serializers.platform import PlatformProtocolSerializer
from terminal.connect_methods import ConnectMethodUtil


class WinRMTerminalTests(SimpleTestCase):
    @patch('terminal.connect_methods.AppletMethod.get_methods', return_value={})
    @patch('terminal.connect_methods.VirtualAppMethod.get_methods', return_value={})
    def test_windows_winrm_uses_koko_web_terminal(self, *_):
        ConnectMethodUtil.refresh_methods()
        self.addCleanup(ConnectMethodUtil.refresh_methods)
        method = ConnectMethodUtil.get_connect_method('web_cli', Protocol.winrm, 'windows')
        self.assertIsNotNone(method)
        self.assertEqual(method['component'], 'koko')
        self.assertEqual(method['type'], 'web')

    def test_public_flag_remains_configurable(self):
        serializer = PlatformProtocolSerializer()
        for public in (True, False):
            data = {'name': 'winrm', 'public': public}
            self.assertEqual(serializer.validate(data.copy()), data)

    def test_tls_certificate_verification_is_enabled_by_default(self):
        setting = Protocol.settings()[Protocol.winrm]['setting']
        self.assertFalse(setting['allow_invalid_cert']['default'])
