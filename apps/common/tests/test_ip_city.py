from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from common.utils.ip.ipip import utils as ipip_utils


class IpCityLookupTests(SimpleTestCase):
    def test_missing_result_returns_none(self):
        with patch.object(ipip_utils, 'init_ipip_db'), \
                patch.object(ipip_utils, 'ipip_db') as database:
            database.find_info.return_value = None

            self.assertIsNone(ipip_utils.get_ip_city_by_ipip('203.0.113.1'))

    def test_found_result_keeps_city_and_country(self):
        with patch.object(ipip_utils, 'init_ipip_db'), \
                patch.object(ipip_utils, 'ipip_db') as database:
            database.find_info.return_value = SimpleNamespace(
                city_name='Shanghai',
                country_name='China',
            )

            self.assertEqual(
                ipip_utils.get_ip_city_by_ipip('203.0.113.1'),
                {'city': 'Shanghai', 'country': 'China'},
            )
