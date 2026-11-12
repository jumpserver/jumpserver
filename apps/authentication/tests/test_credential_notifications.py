from copy import deepcopy
from datetime import datetime, timezone as dt_timezone
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from django.utils.translation import override

from authentication.notifications import CredentialCreatedMessage, CredentialActivityDigestMessage


class CredentialNotificationTests(SimpleTestCase):
    def setUp(self):
        self.enterContext(override_settings(DATA_DIR=self.enterContext(TemporaryDirectory())))
        self.enterContext(timezone.override('UTC'))
        self.enterContext(patch('notifications.notifications.get_login_title', return_value='JumpServer'))
        self.user = SimpleNamespace(name='Notification test')
        self.items = [
            {'credential_type': 'passkey', 'identifier': '12345678-abcd-1234-5678-90abcdef1234',
             'date_created': datetime(2026, 11, 12, 8, 0, tzinfo=dt_timezone.utc), 'date_last_used': None},
            {'credential_type': 'ssh_key', 'identifier': '<img src=x>', 'date_created': None,
             'date_last_used': datetime(2026, 11, 12, 9, 0, tzinfo=dt_timezone.utc)},
        ]

    def test_created_notification_keeps_passkey_terminology(self):
        for language in ['zh', 'en']:
            with self.subTest(language=language), override(language):
                message = CredentialCreatedMessage(self.user, 'passkey', 'demo', '192.0.2.26').get_html_msg()
                self.assertIn(': Passkey</li>', message['message'])
                self.assertNotIn('通行密钥', message['message'])

    def test_html_channels_show_one_row_per_credential_with_missing_dates(self):
        original = deepcopy(self.items)
        with override('zh'):
            message = CredentialActivityDigestMessage(self.user, self.items)
            for render in [message.get_site_msg_msg, message.get_email_msg]:
                with self.subTest(channel=render.__name__):
                    soup = BeautifulSoup(render()['message'], 'html.parser')
                    self.assertEqual([cell.get_text() for cell in soup.select('thead th[scope="col"]')],
                                     ['凭据类型', '标识', '创建日期', '最后使用日期'])
                    rows = [[cell.get_text(strip=True) for cell in row.select('td')]
                            for row in soup.select('tbody tr')]
                    self.assertEqual(rows, [
                        ['Passkey', '12345678...1234', '2026-11-12 08:00:00', '-'],
                        ['SSH 密钥', '<img src=x>', '-', '2026-11-12 09:00:00'],
                    ])
                    self.assertFalse(soup.select('img'))
                    self.assertIn('overflow-x:auto', str(soup.select_one('table').parent))
        self.assertEqual(self.items, original)

    def test_messaging_channels_keep_grouped_content_without_markdown_tables(self):
        with override('zh'):
            message = CredentialActivityDigestMessage(self.user, self.items)
            for render in [message.get_wecom_msg, message.get_dingtalk_msg, message.get_feishu_msg,
                           message.get_lark_msg, message.get_slack_msg]:
                with self.subTest(channel=render.__name__):
                    content = render()['message']
                    self.assertIn('### Passkey `12345678...1234`', content)
                    self.assertIn('2026-11-12 08:00:00', content)
                    self.assertIn('2026-11-12 09:00:00', content)
                    self.assertNotIn('<table', content)
                    self.assertNotIn(' | ', content)
            text = message.get_text_msg()['message']
            self.assertIn('Passkey', text)
            self.assertIn('2026-11-12 08:00:00', text)
            self.assertNotIn(' | ', text)
