from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from audits.const import LoginTypeChoices
from audits.models import UserSession
from audits.signal_handlers.login_log import create_user_session
from users.models import User


class OnlineUserSessionTests(TestCase):
    def setUp(self):
        self.user = User(
            username='cas-session-test', name='CAS session test',
            email='cas-session-test@example.invalid',
        )
        User.objects.bulk_create([self.user])
        self.log = SimpleNamespace(
            type=LoginTypeChoices.web, ip='127.0.0.1', city='',
            backend='CAS', user_agent='test-browser', datetime=timezone.now(),
        )

    def request(self, key):
        class Session(dict):
            session_key = key
        return SimpleNamespace(session=Session())

    def test_repeated_cas_callbacks_reuse_one_online_session(self):
        requests = [self.request('same-browser') for _ in range(4)]
        for request in requests:
            create_user_session(request, self.user.id, self.log)

        session = UserSession.objects.get(user=self.user)
        self.assertEqual(session.key, 'same-browser')
        self.assertEqual(
            {request.session['user_session_id'] for request in requests},
            {str(session.id)},
        )

    def test_distinct_browsers_remain_separate(self):
        for key in ('browser-one', 'browser-two'):
            create_user_session(self.request(key), self.user.id, self.log)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 2)

    def test_existing_duplicates_reuse_latest_record(self):
        for _ in range(3):
            UserSession.objects.create(
                user=self.user, key='same-browser', ip=self.log.ip,
                type=self.log.type, date_created=timezone.now(),
            )
        latest = UserSession.objects.first()
        request = self.request('same-browser')
        create_user_session(request, self.user.id, self.log)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        self.assertEqual(request.session['user_session_id'], str(latest.id))

    def test_missing_session_key_does_not_create_placeholder(self):
        create_user_session(self.request(None), self.user.id, self.log)
        self.assertFalse(UserSession.objects.exists())

    def test_non_web_login_does_not_create_online_session(self):
        self.log.type = LoginTypeChoices.terminal
        create_user_session(self.request('client-session'), self.user.id, self.log)
        self.assertFalse(UserSession.objects.exists())
