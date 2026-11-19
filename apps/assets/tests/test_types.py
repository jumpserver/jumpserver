from unittest.mock import patch

from django.test import SimpleTestCase

from assets.const.host import HostTypes
from assets.const.database import DatabaseTypes
from assets.const.device import DeviceTypes
from assets.const.types import AllTypes


class AllTypesAutomationMethodsTestCase(SimpleTestCase):
    def setUp(self):
        AllTypes._automation_methods_by_language = {}

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


class HostTypesInternalPlatformsTestCase(SimpleTestCase):
    def test_virtual_app_host_is_linux_with_required_ssh(self):
        platforms = HostTypes.internal_platforms()[HostTypes.LINUX]
        virtual_app_host = next(
            item for item in platforms if item['name'] == 'VirtualAppHost'
        )

        self.assertEqual(virtual_app_host['_protocols'], ['ssh'])
        self.assertEqual(
            virtual_app_host['protocols_setting']['ssh'],
            {'required': True, 'default': True},
        )
        self.assertEqual(
            virtual_app_host['automation']['ansible_config'],
            {'ansible_connection': 'ssh'},
        )


class DeviceTypesInternalPlatformsTestCase(SimpleTestCase):
    def test_vendor_platforms_use_distinct_types_in_community_edition(self):
        platform_types = DeviceTypes.internal_platforms()
        with self.settings(XPACK_LICENSE_IS_VALID=False):
            choices = dict(DeviceTypes.get_choices())

        for platform_type, name in (('cisco', 'Cisco'), ('huawei', 'Huawei'), ('h3c', 'H3C')):
            with self.subTest(platform_type=platform_type):
                self.assertEqual(platform_types[platform_type], [{'name': name}])
                self.assertIn(platform_type, choices)

        self.assertEqual(platform_types['general'], [{'name': 'General'}])


class OceanBaseTypeTestCase(SimpleTestCase):
    def test_mysql_wire_setting_exposes_modes_only_for_oceanbase(self):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        from assets.serializers.platform import PlatformProtocolSerializer

        factory = APIRequestFactory()
        for asset_type in ('oceanbase', 'mysql', ''):
            request = Request(factory.get('/', {'name': 'mysql', 'asset_type': asset_type}))
            fields = PlatformProtocolSerializer(context={'request': request}).fields['setting'].serializer.fields
            if asset_type == 'oceanbase':
                self.assertEqual(set(fields['tenant_mode'].choices), {'mysql', 'oracle'})
                self.assertEqual(fields['tenant_mode'].default, 'mysql')
            else:
                self.assertNotIn('tenant_mode', fields)

        for mode in ('oracle', 'mysql', 'invalid'):
            serializer = PlatformProtocolSerializer(data={'name': 'mysql', 'port': 2881, 'setting': {'tenant_mode': mode}})
            self.assertEqual(serializer.is_valid(), mode != 'invalid', serializer.errors)
            if mode != 'invalid':
                self.assertEqual(serializer.validated_data['setting']['tenant_mode'], mode)

    def test_oceanbase_is_enterprise_only_and_uses_mysql_wire(self):
        self.assertNotIn(DatabaseTypes.OCEANBASE, DatabaseTypes.get_community_types())
        self.assertEqual(
            DatabaseTypes._get_protocol_constrains()[DatabaseTypes.OCEANBASE],
            {'choices': ['mysql']},
        )

    def test_internal_platforms_select_tenant_mode_explicitly(self):
        platforms = DatabaseTypes.internal_platforms()[DatabaseTypes.OCEANBASE]
        self.assertEqual([p['name'] for p in platforms], ['OceanBase-MySQL', 'OceanBase-Oracle'])
        self.assertEqual(
            [p['protocols_setting']['mysql']['tenant_mode'] for p in platforms],
            ['mysql', 'oracle'],
        )
