from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from assets.automations.base.manager import PlaybookPrepareMixin


class DummyPlaybookPrepareManager(PlaybookPrepareMixin):
    @classmethod
    def method_type(cls):
        return 'ping'


class PlaybookPrepareMixinTestCase(SimpleTestCase):
    def setUp(self):
        self.manager = object.__new__(DummyPlaybookPrepareManager)
        self.manager.method_id_meta_mapper = {}
        self.manager.summary = {'error_assets': 0}
        self.manager.result = {'error_assets': []}
        self.manager.print_log = lambda *args, **kwargs: None
        self.platform = SimpleNamespace(automation=SimpleNamespace(
            ansible_enabled=True,
            ping_enabled=True,
            ping_method='ping_custom',
        ))

    @patch('assets.const.AllTypes.reload_automation_methods')
    def test_refreshes_method_cache_when_configured_method_is_missing(
        self, reload_methods,
    ):
        reload_methods.return_value = [{
            'id': 'ping_custom',
            'method': 'ping',
        }]

        enabled = self.manager.check_automation_enabled(
            self.platform, ['asset'],
        )

        self.assertTrue(enabled)
        self.assertIn('ping_custom', self.manager.method_id_meta_mapper)
        reload_methods.assert_called_once_with()

    @patch('assets.const.AllTypes.reload_automation_methods', return_value=[])
    def test_reports_unavailable_method_after_cache_refresh(self, _reload):
        enabled = self.manager.check_automation_enabled(
            self.platform, ['asset'],
        )

        self.assertFalse(enabled)
        self.assertEqual(self.manager.summary['error_assets'], 1)
        self.assertEqual(self.manager.result['error_assets'], ['asset'])
