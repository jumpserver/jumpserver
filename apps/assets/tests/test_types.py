from unittest.mock import patch

from django.test import SimpleTestCase

from assets.const.types import AllTypes


class AllTypesAutomationMethodsTestCase(SimpleTestCase):
    def tearDown(self):
        AllTypes._automation_methods_by_language = {}
        super().tearDown()

    @patch('assets.models.PlatformPackage.get_all_automation_methods')
    @patch('accounts.automations.methods.get_platform_automation_methods')
    @patch('assets.automations.methods.get_platform_automation_methods')
    def test_get_automation_methods_cached_by_language(
        self,
        asset_loader,
        account_loader,
        persisted_loader,
    ):
        asset_loader.return_value = [{'id': 'asset'}]
        account_loader.return_value = [{'id': 'account'}]
        persisted_loader.return_value = [{'id': 'persisted'}]

        first = AllTypes.get_automation_methods(language='en')
        second = AllTypes.get_automation_methods(language='en')

        self.assertEqual(first, second)
        self.assertEqual(
            first,
            [{'id': 'asset'}, {'id': 'account'}, {'id': 'persisted'}]
        )
        self.assertEqual(asset_loader.call_count, 1)
        self.assertEqual(account_loader.call_count, 1)
        self.assertEqual(persisted_loader.call_count, 1)
        self.assertEqual(asset_loader.call_args[0][1], 'en')
        self.assertEqual(account_loader.call_args[0][1], 'en')
        self.assertEqual(persisted_loader.call_args.kwargs['lang'], 'en')

    @patch('assets.models.PlatformPackage.get_all_automation_methods')
    @patch('accounts.automations.methods.get_platform_automation_methods')
    @patch('assets.automations.methods.get_platform_automation_methods')
    def test_reload_automation_methods_refreshes_cache(
        self,
        asset_loader,
        account_loader,
        persisted_loader,
    ):
        asset_loader.side_effect = [[{'id': 'asset-v1'}], [{'id': 'asset-v2'}]]
        account_loader.return_value = []
        persisted_loader.return_value = []

        first = AllTypes.get_automation_methods(language='en')
        second = AllTypes.reload_automation_methods(language='en')

        self.assertEqual(first, [{'id': 'asset-v1'}])
        self.assertEqual(second, [{'id': 'asset-v2'}])
        self.assertEqual(asset_loader.call_count, 2)
