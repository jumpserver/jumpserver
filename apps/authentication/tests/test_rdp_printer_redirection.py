from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from authentication.api.connection_token import ConnectionTokenViewSet, RDPFileClientProtocolURLMixin
from terminal.connect_methods import NativeClient


class RDPPrinterRedirectionTests(SimpleTestCase):
    def test_token_options_inherit_preferences_and_allow_explicit_overrides(self):
        for stored, supplied, expected in (
            (None, {}, False),
            ('True', {}, True),
            ('False', {}, False),
            ('True', {'printers_redirect': False}, False),
            ('False', {'printers_redirect': True}, True),
            ('True', {'printers_redirect': 'false'}, False),
        ):
            with self.subTest(stored=stored, supplied=supplied):
                preferences = [] if stored is None else [('printers_redirect', stored)]
                with patch('authentication.api.connection_token.Preference.objects.filter') as query:
                    query.return_value.values_list.return_value = preferences
                    # Applet assets do not necessarily use the RDP protocol.
                    data = {'protocol': 'http', 'connect_options': dict(supplied)}
                    ConnectionTokenViewSet()._insert_connect_options(data, SimpleNamespace(lang='en'))
                self.assertIn('printers_redirect', query.call_args.kwargs['name__in'])
                self.assertIs(data['connect_options']['printers_redirect'], expected)

    def test_rdp_file_uses_query_then_token_then_preference(self):
        for query, options, stored, expected in (
            ({}, {}, 'True', '1'),
            ({}, {'printers_redirect': False}, 'True', '0'),
            ({}, {'printers_redirect': True}, 'False', '1'),
            ({'printers_redirect': '0'}, {'printers_redirect': True}, 'True', '0'),
            ({'printers_redirect': '1'}, {'printers_redirect': False}, 'False', '1'),
        ):
            with self.subTest(query=query, options=options, stored=stored):
                preference = Mock()
                preference.get_value.side_effect = lambda name, **kw: (
                    stored if name == 'printers_redirect' else kw['default']
                )
                asset = Mock(name='Windows')
                asset.platform.protocols.filter.return_value.first.return_value = None
                token = SimpleNamespace(
                    id='token', asset=asset, connect_method=NativeClient.mstsc,
                    connect_options={'resolution': 'auto', **options},
                    user=SimpleNamespace(username='user', preference=preference),
                )
                view = RDPFileClientProtocolURLMixin()
                view.request = SimpleNamespace(query_params=query)
                view.get_smart_endpoint = Mock(return_value=SimpleNamespace(host='gateway', rdp_port=3389))
                view._try_sign_rdp_content = lambda content: content
                _, content = view.get_rdp_file_info(token)
                self.assertIn(f'redirectprinters:i:{expected}\n', content)
