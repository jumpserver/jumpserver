from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from accounts.utils import AccountSecretTaskStatus


@override_settings(
    CHANGE_SECRET_AFTER_SESSION_END=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class AccountSecretTaskStatusSettingsTests(SimpleTestCase):
    def setUp(self):
        self.manager = AccountSecretTaskStatus(prefix='test:session-secret:')
        self.addCleanup(cache.clear)

    def test_enable_after_manager_was_created(self):
        with override_settings(CHANGE_SECRET_AFTER_SESSION_END=True):
            self.manager.set_status('account', 'queued')
            self.assertEqual(self.manager.get_status('account'), 'queued')

    def test_disable_stops_an_existing_manager_from_enqueuing(self):
        with override_settings(CHANGE_SECRET_AFTER_SESSION_END=True):
            manager = AccountSecretTaskStatus(prefix='test:session-secret:disable:')
        manager.set_status('account', 'queued')
        self.assertEqual(manager.get('account'), {})
