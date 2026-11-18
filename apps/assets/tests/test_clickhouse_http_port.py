from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from assets.clickhouse import CLICKHOUSE_HTTP_PROTOCOL
from assets.const import Protocol
from assets.models import PlatformProtocol
from assets.serializers.asset.common import AssetProtocolsSerializer, AssetSerializer
from assets.serializers.platform import PlatformProtocolSerializer
from authentication.serializers import ConnectionTokenSecretSerializer
from ops.ansible.inventory import JMSInventory
from orgs.mixins.serializers import OrgResourceModelSerializerMixin


class ClickHouseHTTPPortTests(SimpleTestCase):
    def test_platform_no_longer_exposes_http_port_setting(self):
        self.assertEqual(Protocol.database_protocols()[Protocol.clickhouse]['port'], 9000)
        request = Request(APIRequestFactory().get('/api/v1/assets/protocol-settings/', {'name': 'clickhouse'}))
        serializer = PlatformProtocolSerializer(context={'request': request})
        self.assertNotIn('http_port', serializer.fields['setting'].serializer.fields)

    def test_platform_save_drops_obsolete_http_port(self):
        request = Request(APIRequestFactory().post('/api/v1/assets/platforms/'))
        serializer = PlatformProtocolSerializer(data={
            'name': 'clickhouse', 'port': 19000, 'setting': {'http_port': '18123', 'other': True},
        }, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['setting'], {'other': True})
        self.assertEqual(serializer.validated_data['port'], 19000)

    def test_asset_defaults_use_native_platform_port_and_standard_http(self):
        native = PlatformProtocol(id=1, name=Protocol.clickhouse, port=19000, required=True)
        platform = SimpleNamespace(protocols=Mock())
        platform.protocols.all.return_value = [native]
        serializer = AssetSerializer(data={})
        with patch.object(AssetSerializer, '_asset_platform', new_callable=PropertyMock, return_value=platform):
            serializer._set_protocols_default()
        self.assertEqual(serializer.initial_data['protocols'], [
            {'name': Protocol.clickhouse, 'port': 19000},
            {'name': CLICKHOUSE_HTTP_PROTOCOL, 'port': 8123},
        ])

    def test_asset_http_port_requires_a_valid_port_and_native_protocol(self):
        def validate(protocols, platform_type):
            platform = SimpleNamespace(protocols=Mock())
            platform.protocols.all.return_value = []
            platform.protocols.filter.return_value.exists.return_value = platform_type == Protocol.clickhouse
            data = AssetProtocolsSerializer(many=True).run_validation(protocols)
            with patch.object(AssetSerializer, '_asset_platform', new_callable=PropertyMock, return_value=platform):
                return list(AssetSerializer().validate_protocols(data))

        native = {'name': Protocol.clickhouse, 'port': 19000}
        http = {'name': CLICKHOUSE_HTTP_PROTOCOL, 'port': 18123}
        self.assertEqual(validate([native, http], Protocol.clickhouse), [native, http])
        self.assertEqual(validate([native], Protocol.clickhouse), [native])
        for port in (None, 0, -1, 65536, 3.14, True):
            with self.subTest(port=port), self.assertRaises(ValidationError):
                validate([native, {**http, 'port': port}], Protocol.clickhouse)
        for protocols, platform in (
                ([http], Protocol.clickhouse), ([native, http, http], Protocol.clickhouse),
                ([native, http], Protocol.mysql)):
            with self.subTest(platform=platform, protocols=protocols), self.assertRaises(ValidationError):
                validate(protocols, platform)
        serializer = PlatformProtocolSerializer(data=http)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_token_keeps_native_protocol_and_carries_effective_http_setting(self):
        native = {'name': Protocol.clickhouse, 'port': 19000}
        http = {'name': CLICKHOUSE_HTTP_PROTOCOL, 'port': 18123}
        for protocols, platform_port, expected in (
                ([http, native], None, 18123), ([native], None, 8123), ([native], 65536, 8123)):
            platform_setting = {'compatibility_option': 'keep'}
            if platform_port is not None:
                platform_setting['http_port'] = platform_port
            data = {
                'asset': {'protocols': protocols},
                'platform': {'protocols': [{'name': Protocol.clickhouse, 'setting': platform_setting}]},
            }
            with patch.object(OrgResourceModelSerializerMixin, 'to_representation', return_value=deepcopy(data)):
                response = ConnectionTokenSecretSerializer().to_representation(
                    SimpleNamespace(protocol=Protocol.clickhouse)
                )
            self.assertEqual(response['asset']['protocols'], [native])
            self.assertEqual(response['platform']['protocols'][0]['setting'],
                             {'http_port': expected, 'compatibility_option': 'keep'})
            self.assertEqual(platform_setting.get('http_port'), platform_port)

    def test_automation_does_not_select_http_as_primary_protocol(self):
        http = SimpleNamespace(name=CLICKHOUSE_HTTP_PROTOCOL, port=8123)
        native = SimpleNamespace(name=Protocol.clickhouse, port=9000)
        self.assertIs(JMSInventory.get_primary_protocol(
            SimpleNamespace(protocol=None), {}, [http, native]
        ), native)
