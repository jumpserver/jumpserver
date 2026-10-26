from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from authentication.utils import get_effective_connect_options


class RDPSecurityOptionsTests(SimpleTestCase):
    def test_platform_default_is_resolved_by_the_connection_component(self):
        for supplied in ({}, {'rdp_security': 'default'}):
            with self.subTest(supplied=supplied):
                self.assertEqual(
                    get_effective_connect_options(supplied, 'rdp', object()), supplied,
                )

    def test_explicit_security_layers_are_preserved(self):
        for security in ('any', 'rdp', 'tls', 'nla'):
            with self.subTest(security=security):
                supplied = {'rdp_security': security, 'resolution': 'auto'}
                self.assertEqual(get_effective_connect_options(supplied, 'rdp'), supplied)

    def test_invalid_security_layers_are_rejected(self):
        for security in ('', 'invalid', None, False, 1, [], {}):
            with self.subTest(security=security):
                with self.assertRaises(ValidationError):
                    get_effective_connect_options({'rdp_security': security}, 'rdp')

    def test_other_protocols_do_not_forward_rdp_security(self):
        supplied = {'rdp_security': 'nla', 'resolution': 'auto'}
        self.assertEqual(get_effective_connect_options(supplied, 'http'), {'resolution': 'auto'})
        self.assertEqual(supplied['rdp_security'], 'nla')
