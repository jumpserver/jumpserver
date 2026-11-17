from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from assets.validators import validate_asset_address, validate_ip_or_hostname


class HostAddressValidationTests(SimpleTestCase):
    def test_hostnames_with_underscores_are_accepted(self):
        for value in (
            '35.246.193.xxx_6290xxx.globalssh.cn',
            '35.246.193.xxx_6290xxx.ipssh.net',
            'server_01',
        ):
            with self.subTest(value=value):
                validate_asset_address(value)
                validate_ip_or_hostname(value)

    def test_existing_ip_and_hostname_formats_are_accepted(self):
        for value in (
            '192.0.2.1', '2001:db8::1', 'localhost', 'server-01.example.com',
            '服务器.example.com', 'a' * 63 + '.example.com',
            '.'.join(['a' * 63] * 3 + ['a' * 61]),
        ):
            with self.subTest(value=value):
                validate_ip_or_hostname(value)

    def test_invalid_hostnames_are_still_rejected(self):
        for value in (
            '', '999.1.1.1', 'host..example.com', 'host.example.com.',
            '-host_01.example.com', 'host_01-.example.com',
            'a' * 64 + '.example.com', '.'.join(['a' * 63] * 4),
            'host_01:22', 'https://host_01', 'host_01/path',
            'user@host_01', 'host_01;id', 'host 01',
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_ip_or_hostname(value)

    def test_unsafe_host_addresses_are_still_rejected(self):
        for value in (
            ' host_01', 'host_01 ', 'host_01\n', 'host\x00_01', 'host\x7f_01',
            '{{ host_01 }}', '{% host_01 %}', '{# host_01 #}',
            '#jinja2:variable_start_string:"[["',
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_asset_address(value)
                validate_ip_or_hostname(value)
