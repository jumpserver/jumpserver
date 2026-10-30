from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from authentication.api.connection_token import (
    ConnectionTokenViewSet, RDPFileClientProtocolURLMixin,
)
from authentication.serializers.connect_token_secret import ConnectionTokenSecretSerializer
from authentication.utils import get_effective_connect_options


class OracleSysdbaOptionsTests(SimpleTestCase):
    def asset(self, enabled):
        protocols = Mock()
        protocols.filter.return_value.first.return_value = SimpleNamespace(setting={'sysdba': enabled})
        return SimpleNamespace(
            platform=SimpleNamespace(protocols=protocols), id='asset-id', name='oracle',
            category='database', type='oracle', address='db.example.com',
            spec_info={'db_name': 'ORCL'},
        )

    def test_platform_setting_wins_over_default_false(self):
        for enabled in (True, False, 'true', 'false'):
            for supplied in ({}, {'use_sysdba': False}, {'use_sysdba': True}):
                with self.subTest(enabled=enabled, supplied=supplied):
                    original = dict(supplied)
                    options = get_effective_connect_options(supplied, 'oracle', self.asset(enabled))
                    expected = enabled in (True, 'true') or supplied.get('use_sysdba', False)
                    self.assertIs(options['use_sysdba'], expected)
                    self.assertEqual(supplied, original)

    def test_other_protocols_do_not_inherit_oracle_roles(self):
        asset = self.asset(True)
        options = get_effective_connect_options({'use_sysdba': True, 'charset': 'utf8'}, 'mysql', asset)
        self.assertEqual(options, {'charset': 'utf8'})
        asset.platform.protocols.filter.assert_not_called()

    def test_absent_platform_protocol_defaults_to_normal(self):
        asset = self.asset(True)
        asset.platform.protocols.filter.return_value.first.return_value = None
        self.assertIs(get_effective_connect_options({}, 'oracle', asset)['use_sysdba'], False)
        self.assertIs(get_effective_connect_options({}, 'oracle')['use_sysdba'], False)

    def test_component_secret_and_client_url_inherit_for_existing_tokens(self):
        token = SimpleNamespace(
            id='token-id', value='synthetic-secret', protocol='oracle',
            connect_method='db_client', connect_options={'use_sysdba': False},
            asset=self.asset(True), org_id='org-id',
        )
        self.assertIs(ConnectionTokenSecretSerializer.get_connect_options(token)['use_sysdba'], True)
        view = RDPFileClientProtocolURLMixin()
        view.request = Mock()
        view.get_token_account_display = lambda _: 'sys'
        view.get_smart_endpoint = Mock(return_value=SimpleNamespace(
            host='gateway.example.com', get_port=lambda *_: 5525,
        ))
        with patch('authentication.api.connection_token.get_request_os', return_value='mac'), patch(
            'authentication.api.connection_token.ConnectMethodUtil.get_connect_method',
            return_value={'type': 'native', 'endpoint_protocol': 'oracle'},
        ), patch('authentication.api.connection_token.build_absolute_uri',
                 return_value='https://gateway.example.com/', create=True):
            data = view.get_client_protocol_data(token)
        self.assertEqual(data['connect_options'], {'use_sysdba': True})
        self.assertEqual(token.connect_options, {'use_sysdba': False})

    def test_token_creation_and_exchange_keep_the_effective_role(self):
        view = ConnectionTokenViewSet()
        view.request = Mock()
        view.get_user = Mock(return_value=SimpleNamespace())
        view._insert_connect_options = Mock()
        view._validate = Mock(return_value={})
        asset = self.asset(True)
        serializer = SimpleNamespace(validated_data={
            'asset': asset, 'account': 'sys', 'protocol': 'oracle',
            'connect_method': 'db_client', 'connect_options': {'use_sysdba': False},
        })
        with patch('authentication.api.connection_token.get_request_ip_or_data', return_value='127.0.0.1'):
            view.validate_serializer(serializer)
            self.assertIs(serializer.validated_data['connect_options']['use_sysdba'], True)
            token = SimpleNamespace(
                user=SimpleNamespace(), asset=asset, account='sys', protocol='oracle',
                connect_method='db_client', connect_options={'use_sysdba': False},
                input_username='', personal_credential_id=None, face_monitor_token='',
            )
            view.validate_exchange_token(token)
        self.assertIs(token.connect_options['use_sysdba'], True)
