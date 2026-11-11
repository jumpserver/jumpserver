from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from authentication.api.connection_token import RDPFileClientProtocolURLMixin
from assets.const import Protocol
from terminal.connect_methods import ConnectMethodUtil, NativeClient
from terminal.models import Endpoint


class NativeDatabaseConnectMethodTests(SimpleTestCase):
    @override_settings(VENDOR='jumpserver', XPACK_LICENSE_IS_VALID=True)
    @patch('terminal.connect_methods.AppletMethod.get_methods', return_value={})
    @patch('terminal.connect_methods.VirtualAppMethod.get_methods', return_value={})
    def test_db2_and_clickhouse_offer_all_connection_paths(self, *_):
        ConnectMethodUtil.refresh_methods()
        self.addCleanup(ConnectMethodUtil.refresh_methods)
        for protocol in (Protocol.db2, Protocol.clickhouse):
            with self.subTest(protocol=protocol):
                methods = ConnectMethodUtil.get_protocols_connect_methods()[protocol]
                self.assertEqual(
                    {(method['component'], method['value']) for method in methods},
                    {('koko', 'web_cli'), ('chen', 'web_gui'),
                     ('magnus', 'db_client'), ('magnus', 'db_guide')},
                )
                self.assertTrue(Protocol.database_protocols()[protocol]['xpack'])
                self.assertEqual(Endpoint(magnus_port=15525).get_port(None, protocol), 15525)

    @override_settings(VENDOR='jumpserver', XPACK_LICENSE_IS_VALID=False)
    def test_new_native_methods_still_require_enterprise_license(self):
        methods = NativeClient.get_methods()
        self.assertNotIn(Protocol.db2, methods)
        self.assertNotIn(Protocol.clickhouse, methods)
        self.assertIn(Protocol.mysql, methods)
        self.assertIn(Protocol.redis, methods)

    @override_settings(VENDOR='custom')
    def test_new_native_methods_follow_oracle_vendor_visibility(self):
        clients = NativeClient.get_native_clients()
        for protocol in (Protocol.db2, Protocol.clickhouse, Protocol.oracle):
            self.assertNotIn(protocol, clients)
        self.assertIn(Protocol.mysql, clients)

    def test_existing_endpoint_ports_are_unchanged(self):
        endpoint = Endpoint(magnus_port=15525, ssh_port=2222, rdp_port=3389)
        for protocol in (Protocol.mysql, Protocol.mariadb, Protocol.postgresql,
                         Protocol.oracle, Protocol.dameng, Protocol.sqlserver,
                         Protocol.redis, Protocol.mongodb):
            self.assertEqual(endpoint.get_port(None, protocol), 15525)
        self.assertEqual(endpoint.get_port(None, Protocol.ssh), 2222)
        self.assertEqual(endpoint.get_port(None, Protocol.sftp), 2222)
        self.assertEqual(endpoint.get_port(None, Protocol.rdp), 3389)
        self.assertEqual(Protocol.database_protocols()[Protocol.db2]['port'], 50000)

    @override_settings(VENDOR='jumpserver', XPACK_LICENSE_IS_VALID=True)
    @patch('terminal.connect_methods.AppletMethod.get_methods', return_value={})
    @patch('terminal.connect_methods.VirtualAppMethod.get_methods', return_value={})
    def test_native_launch_payload_uses_proxy_endpoint_token_and_asset_database(self, *_):
        ConnectMethodUtil.refresh_methods()
        self.addCleanup(ConnectMethodUtil.refresh_methods)
        view = RDPFileClientProtocolURLMixin()
        view.request = Mock()
        view.get_token_account_display = lambda _: 'db-account'
        view.get_smart_endpoint = Mock(return_value=Endpoint(
            host='gateway.example.com', magnus_port=15525,
        ))
        for protocol in (Protocol.db2, Protocol.clickhouse):
            asset = SimpleNamespace(
                id='asset-id', category='database', type=protocol, name='test',
                address='backend.example.com', spec_info={'db_name': 'ANALYTICS'},
            )
            token = SimpleNamespace(
                id='selector-token', value='access-secret', org_id='org-id',
                protocol=protocol, connect_method='db_client', asset=asset,
            )
            with self.subTest(protocol=protocol), patch(
                'authentication.api.connection_token.get_request_os', return_value='windows',
            ), patch(
                'authentication.api.connection_token.build_absolute_uri',
                return_value='https://gateway.example.com/',
            ):
                data = view.get_client_protocol_data(token)
                self.assertEqual(data['protocol'], protocol)
                self.assertEqual(data['endpoint'], {'host': 'gateway.example.com', 'port': 15525})
                self.assertEqual(data['token'], {'id': 'selector-token', 'value': 'access-secret'})
                self.assertEqual(data['asset']['info']['db_name'], 'ANALYTICS')
