from types import SimpleNamespace

from django.db import connection, migrations
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
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


class WebSessionSchemaMigrationTests(TransactionTestCase):
    previous = ('audits', '0017_expand_password_change_log_identity')
    latest = ('audits', '0018_remove_legacy_web_session_lock_fields')
    legacy_fields = ('is_locked', 'lock_password_failures')

    def setUp(self):
        self.user = User(username='web-session-schema-test')
        User.objects.bulk_create([self.user])
        self.addCleanup(self.migrate, self.latest)

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target])

    def columns(self):
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, UserSession._meta.db_table)
        return {field.name for field in description}

    def create_session(self, model=UserSession, **extra):
        return model.objects.create(
            user_id=self.user.pk, key='schema-test-browser', ip='127.0.0.1', type='W', **extra,
        )

    def assert_current_schema(self):
        self.assertTrue(set(self.legacy_fields).isdisjoint(self.columns()))
        session = self.create_session()
        self.assertTrue(UserSession.objects.filter(pk=session.pk).exists())

    def test_fresh_install_allows_login_session_inserts(self):
        self.assert_current_schema()

    def test_original_0013_upgrade_preserves_sessions_and_allows_new_logins(self):
        state = self.migrate(self.previous)
        self.assertTrue(set(self.legacy_fields).issubset(self.columns()))
        previous = state.apps.get_model('audits', 'UserSession')
        session = self.create_session(previous, is_locked=True, lock_password_failures=2)

        self.migrate(self.latest)

        self.assertTrue(UserSession.objects.filter(pk=session.pk, key=session.key).exists())
        self.assert_current_schema()

    def test_recorded_empty_0013_upgrade_preserves_sessions_without_recreating_columns(self):
        state = self.migrate(self.previous)
        previous = state.apps.get_model('audits', 'UserSession')
        session = self.create_session(previous)
        # Match the empty-0013 installation: migration history remains applied,
        # but neither physical column exists. Use standard backend schema edits.
        for name in self.legacy_fields:
            operation = migrations.RemoveField('usersession', name)
            before = state.clone()
            operation.state_forwards('audits', state)
            with connection.schema_editor() as editor:
                operation.database_forwards('audits', editor, before, state)

        self.migrate(self.latest)

        self.assertTrue(UserSession.objects.filter(pk=session.pk, key=session.key).exists())
        self.assert_current_schema()
