from email.header import decode_header, make_header
from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.utils import translation
from django.utils.translation import gettext_lazy

from common.tasks import send_mail_async
from common.utils import text_hmac_sha256


@override_settings(
    EMAIL_SUBJECT_PREFIX='[JumpServer] ',
    EMAIL_FROM='jumpserver@example.com',
    EMAIL_HOST_USER='smtp@example.com',
    LANGUAGE_CODE='en',
)
class MailDeliveryTests(SimpleTestCase):
    def setUp(self):
        self.connection = mail.get_connection('django.core.mail.backends.locmem.EmailBackend')
        connection_patch = patch('common.tasks.get_email_connection', return_value=self.connection)
        connection_patch.start()
        self.addCleanup(connection_patch.stop)
        users_patch = patch('common.tasks.User.objects.filter')
        self.users = users_patch.start()
        self.addCleanup(users_patch.stop)
        self.users.return_value.all.return_value = [
            SimpleNamespace(email='a@example.com', email_lookup=text_hmac_sha256('a@example.com'), lang='en'),
        ]
        mail.outbox.clear()

    def test_sends_once_per_recipient_regardless_of_matching_users(self):
        cases = (
            (['shared@example.com'] * 2, ['shared@example.com'], ['shared@example.com']),
            (['a@example.com', 'b@example.com'], ['a@example.com', 'b@example.com'], ['a@example.com', 'b@example.com']),
            ([], ['new@example.com'], ['new@example.com']),
            (['a@example.com', 'b@example.com'], ['a@example.com', 'b@example.com', 'a@example.com'], ['a@example.com', 'b@example.com']),
        )
        for user_emails, recipients, expected_recipients in cases:
            self.users.return_value.all.return_value = [
                SimpleNamespace(email=email, email_lookup=text_hmac_sha256(email), lang='en')
                for email in user_emails
            ]
            original_recipients = recipients.copy()
            for style in ('short', 'full', 'keyword'):
                with self.subTest(users=user_emails, recipients=recipients, style=style):
                    mail.outbox.clear()
                    kwargs = {'html_message': '<p>123456</p>'}
                    if style == 'short':
                        args = ('MFA', '123456', recipients)
                    elif style == 'full':
                        args = ('MFA', '123456', 'explicit@example.com', recipients)
                    else:
                        args = ()
                        kwargs.update(
                            subject='MFA', message='123456',
                            from_email='explicit@example.com', recipient_list=recipients,
                        )
                    send_mail_async(*args, **kwargs)

                    self.assertEqual([message.to for message in mail.outbox], [[email] for email in expected_recipients])
                    for message in mail.outbox:
                        self.assertEqual(message.body, '123456')
                        self.assertEqual(message.alternatives, [('<p>123456</p>', 'text/html')])
                        self.assertEqual(message.subject, '[JumpServer] MFA' if style == 'short' else 'MFA')
                        self.assertEqual(
                            message.from_email,
                            'jumpserver@example.com' if style == 'short' else 'explicit@example.com',
                        )
                    self.assertEqual(recipients, original_recipients)

    def test_empty_recipient_list_sends_nothing(self):
        send_mail_async('MFA', '123456', [])
        self.assertEqual(mail.outbox, [])

    def test_renders_lazy_content_in_each_recipients_language(self):
        self.users.return_value.all.return_value = [
            SimpleNamespace(email_lookup=text_hmac_sha256(email), lang=language)
            for email, language in (
                ('a@example.com', 'zh-hans'),
                ('a@example.com', 'en'),
                ('b@example.com', ''),
            )
        ]
        delivered = []

        def capture_messages(messages):
            delivered.extend(
                (message.to, translation.get_language(), message.message()) for message in messages
            )
            return len(messages)

        with translation.override('de'), patch.object(self.connection, 'send_messages', side_effect=capture_messages):
            send_mail_async(
                subject=gettext_lazy('Password'), message=gettext_lazy('Password'),
                from_email='sender@example.com',
                recipient_list=['a@example.com', 'b@example.com', 'new@example.com'],
                html_message=gettext_lazy('Password'),
            )
            self.assertEqual(translation.get_language(), 'de')

        self.assertEqual(
            [(recipients, language) for recipients, language, _ in delivered],
            [(['a@example.com'], 'zh-hans'), (['b@example.com'], 'en'), (['new@example.com'], 'de')],
        )
        for (_, language, message), expected in zip(delivered, ('密码', 'Password', 'Passwort')):
            with self.subTest(language=language):
                self.assertEqual(str(make_header(decode_header(message['Subject']))), expected)
                for alternative in message.get_payload():
                    self.assertEqual(alternative.get_payload(decode=True).decode(alternative.get_content_charset()), expected)

    def test_delivery_failure_is_logged(self):
        with patch('common.tasks.send_mail', side_effect=RuntimeError('SMTP unavailable')), \
                patch('common.tasks.logger') as logger:
            send_mail_async('MFA', '123456', ['a@example.com'])
        logger.error.assert_called_once()

    def test_verification_failure_does_not_log_or_raise_message_content(self):
        with patch('common.tasks.send_mail', side_effect=RuntimeError('code=123456')), \
                patch('common.tasks.logger') as logger:
            with self.assertRaisesRegex(RuntimeError, '^Verification email delivery failed$'):
                send_mail_async('MFA', '123456', ['a@example.com'], safe_errors=True)
        logger.error.assert_not_called()
