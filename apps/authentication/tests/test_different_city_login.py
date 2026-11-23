from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from audits.models import UserLoginLog
from authentication.utils import check_different_city_login_if_need


@override_settings(SECURITY_CHECK_DIFFERENT_CITY_LOGIN=True, LANGUAGE_CODE='en')
class DifferentCityLoginTests(TestCase):
    def setUp(self):
        self.user = SimpleNamespace(username='city-test', name='City Test')
        self.request = object()
        self.now = timezone.now()
        self.enterContext(patch('authentication.utils.timezone.now', return_value=self.now))
        self.ip = self.enterContext(patch('authentication.utils.get_request_ip', return_value='8.8.8.8'))
        self.enterContext(patch('authentication.utils.get_ip_city', return_value='Shanghai'))
        self.message = self.enterContext(patch('authentication.utils.DifferentCityLoginMessage'))

    def add_login(self, city, days=1, **overrides):
        fields = {
            'username': f'{self.user.name}({self.user.username})',
            'ip': '8.8.8.8', 'city': city, 'status': True,
            'datetime': self.now - timedelta(days=days), 'type': 'W',
        }
        fields.update(overrides)
        UserLoginLog.objects.bulk_create([UserLoginLog(**fields)])

    def assert_no_alert(self):
        check_different_city_login_if_need(self.user, self.request)
        self.message.assert_not_called()

    def assert_alert(self):
        check_different_city_login_if_need(self.user, self.request)
        self.message.assert_called_once_with(self.user, '8.8.8.8', 'Shanghai')
        self.message.return_value.publish_async.assert_called_once_with()

    def test_same_ip_and_city_after_more_than_seven_days_does_not_alert(self):
        self.add_login('Shanghai', days=30)
        self.assert_no_alert()

    def test_changed_ip_in_same_last_city_does_not_alert(self):
        self.add_login('Shanghai', days=30, ip='1.1.1.1')
        self.assert_no_alert()

    def test_recent_city_other_than_last_city_does_not_alert(self):
        self.add_login('Beijing', days=1)
        self.add_login('Shanghai', days=3)
        self.assert_no_alert()

    def test_city_seen_exactly_seven_days_ago_does_not_alert(self):
        self.add_login('Beijing', days=1)
        self.add_login('Shanghai', days=7)
        self.assert_no_alert()

    def test_older_city_outside_window_still_alerts(self):
        self.add_login('Beijing', days=1)
        self.add_login('Shanghai', datetime=self.now - timedelta(days=7, microseconds=1))
        self.assert_alert()

    def test_different_city_after_long_absence_alerts(self):
        self.add_login('Beijing', days=30)
        self.assert_alert()

    def test_new_city_after_recent_login_alerts(self):
        self.add_login('Beijing')
        self.assert_alert()

    def test_legacy_username_history_is_used(self):
        self.add_login('Beijing', days=30, username=self.user.username)
        self.assert_alert()

    def test_failed_login_does_not_suppress_alert(self):
        self.add_login('Beijing', days=30)
        self.add_login('Shanghai', status=False)
        self.assert_alert()

    def test_another_users_city_does_not_suppress_alert(self):
        self.add_login('Beijing', days=30)
        self.add_login('Shanghai', username='other-user')
        self.assert_alert()

    def test_no_successful_public_login_history_does_not_alert(self):
        self.assert_no_alert()
        self.add_login('Beijing', status=False)
        self.add_login('Beijing', username='other-user')
        self.add_login('LAN', ip='192.168.1.1')
        self.assert_no_alert()

    @override_settings(SECURITY_CHECK_DIFFERENT_CITY_LOGIN=False)
    def test_disabled_setting_does_not_alert(self):
        self.add_login('Beijing')
        self.assert_no_alert()

    def test_private_or_missing_ip_does_not_alert(self):
        self.add_login('Beijing')
        for ip in ('192.168.1.1', '127.0.0.1', '::1', 'fd00::1', None):
            with self.subTest(ip=ip):
                self.ip.return_value = ip
                self.assert_no_alert()
