from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.utils import translation

from common.tasks import send_mail_async


@override_settings(
    EMAIL_SUBJECT_PREFIX='[JumpServer] ',
    EMAIL_FROM='jumpserver@example.com',
    EMAIL_HOST_USER='smtp@example.com',
)
class MailDeliveryTests(SimpleTestCase):
    def setUp(self):
        connection = mail.get_connection('django.core.mail.backends.locmem.EmailBackend')
        connection_patch = patch('common.tasks.get_email_connection', return_value=connection)
        connection_patch.start()
        self.addCleanup(connection_patch.stop)
        users_patch = patch('common.tasks.User.objects.filter')
        self.users = users_patch.start()
        self.addCleanup(users_patch.stop)
        self.users.return_value.all.return_value = [
            SimpleNamespace(email='a@example.com', lang='en'),
        ]
        mail.outbox.clear()

    def test_sends_once_per_call_regardless_of_matching_users(self):
        cases = (
            (['shared@example.com'] * 2, ['shared@example.com'], ['shared@example.com']),
            (['a@example.com', 'b@example.com'], ['a@example.com', 'b@example.com'], ['a@example.com', 'b@example.com']),
            ([], ['new@example.com'], ['new@example.com']),
            (['a@example.com', 'b@example.com'], ['a@example.com', 'b@example.com', 'a@example.com'], ['a@example.com', 'b@example.com']),
        )
        for user_emails, recipients, expected_recipients in cases:
            self.users.return_value.all.return_value = [
                SimpleNamespace(email=email, lang='en') for email in user_emails
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

                    self.assertEqual(len(mail.outbox), 1)
                    message = mail.outbox[0]
                    self.assertEqual(message.to, expected_recipients)
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

    def test_preserves_callers_language(self):
        self.users.return_value.all.return_value = [
            SimpleNamespace(email='shared@example.com', lang='zh-hans'),
        ]
        languages = []
        with translation.override('en'), patch(
            'common.tasks.send_mail', side_effect=lambda *a, **kw: languages.append(translation.get_language()),
        ):
            send_mail_async('MFA', '123456', ['shared@example.com'])
        self.assertEqual(languages, ['en'])

    def test_delivery_failure_is_logged(self):
        with patch('common.tasks.send_mail', side_effect=RuntimeError('SMTP unavailable')), \
                patch('common.tasks.logger') as logger:
            send_mail_async('MFA', '123456', ['a@example.com'])
        logger.error.assert_called_once()
