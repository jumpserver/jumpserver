from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from assets.const import Protocol
from assets.models import PlatformProtocol
from assets.serializers.platform import PlatformProtocolSerializer


class ClickHouseHTTPPortTests(SimpleTestCase):
    def setting_serializer(self):
        request = Request(APIRequestFactory().get('/api/v1/assets/protocol-settings/', {'name': 'clickhouse'}))
        return PlatformProtocolSerializer(context={'request': request}).fields['setting'].serializer

    def test_default_http_port_is_separate_from_native_port(self):
        self.assertEqual(Protocol.database_protocols()[Protocol.clickhouse]['port'], 9000)
        field = self.setting_serializer().fields['http_port']
        self.assertEqual((field.default, field.min_value, field.max_value), (8123, 1, 65535))
        self.assertEqual(self.setting_serializer().run_validation({}), {'http_port': 8123})
        protocol = PlatformProtocol(name='clickhouse', port=19000, setting={'http_port': 18123})
        self.assertEqual(self.setting_serializer().to_representation(protocol.setting), {'http_port': 18123})
        self.assertEqual(protocol.port, 19000)

    def test_invalid_ports_are_rejected_by_the_actual_setting_serializer(self):
        from rest_framework.exceptions import ValidationError
        for value in (0, -1, 65536, 'invalid', True, 8123.5):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.setting_serializer().run_validation({'http_port': value})
        for value in (1, 65535, '18123'):
            self.assertEqual(self.setting_serializer().run_validation({'http_port': value})['http_port'], int(value))

    def test_legacy_setting_is_not_mutated_by_reading_metadata(self):
        setting = {}
        self.setting_serializer().to_representation(setting)
        self.assertEqual(setting, {})

    def test_nested_platform_save_validates_http_port_without_query_name(self):
        request = Request(APIRequestFactory().post('/api/v1/assets/platforms/'))
        for value in (0, 65536, 'invalid'):
            with self.subTest(value=value):
                serializer = PlatformProtocolSerializer(data={
                    'name': 'clickhouse', 'port': 9000, 'setting': {'http_port': value},
                }, context={'request': request})
                self.assertFalse(serializer.is_valid())
                self.assertIn('http_port', serializer.errors['setting'])
        serializer = PlatformProtocolSerializer(data={
            'name': 'clickhouse', 'port': 19000, 'setting': {'http_port': '18123'},
        }, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['setting']['http_port'], 18123)
        self.assertEqual(serializer.validated_data['port'], 19000)
