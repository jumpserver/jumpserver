from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from reports.mixins import CREATABLE_REPORT_TYPES, REPORT_FILTER_FIELDS, resolve_range
from reports.api.report import (
    ReportSerializer,
    ReportViewSet,
    build_template_item,
    merge_report_filters,
)
from reports.models import Report


class ReportRangeTests(SimpleTestCase):
    def test_resolve_range_uses_preset_days(self):
        result = resolve_range(preset='last_week', days=1)
        self.assertEqual((result['end'] - result['start']).days, 6)

    def test_resolve_range_swaps_reversed_dates(self):
        result = resolve_range(start='2026-03-10', end='2026-03-01')
        self.assertEqual(str(result['start']), '2026-03-01')
        self.assertEqual(str(result['end']), '2026-03-10')


class ReportApiHelperTests(SimpleTestCase):
    def test_build_template_item_contains_switching_metadata(self):
        item = build_template_item('AssetReport')
        self.assertEqual(item['tp'], 'AssetReport')
        self.assertEqual(item['actions'], ['save'])
        self.assertEqual(item['view_modes'], ['chart', 'table'])
        self.assertIn('asset_id', item['filters'])

    def test_user_reports_use_user_id_filter(self):
        item = build_template_item('UserLoginReport')
        self.assertIn('user_id', item['filters'])
        self.assertNotIn('username', item['filters'])

    def test_merge_report_filters_supports_override_and_clear(self):
        report = SimpleNamespace(
            tp='UserLoginReport',
            filters={'user_id': 'user-1', 'range_preset': 'last_week'}
        )
        merged = merge_report_filters(report, {
            'user_id': '',
            'start': '2026-03-01',
            'end': '2026-03-07',
        })
        self.assertNotIn('user_id', merged)
        self.assertEqual(merged['start'], '2026-03-01')
        self.assertEqual(merged['end'], '2026-03-07')
        self.assertEqual(merged['range_preset'], 'last_week')

    def test_report_type_can_not_be_modified(self):
        serializer = ReportSerializer(instance=Report(tp='UserLoginReport'))
        with self.assertRaisesMessage(Exception, 'Report type can not be modified'):
            serializer.validate_tp('AssetReport')

    def test_statistics_reports_are_creatable(self):
        self.assertIn('AssetStatistics', CREATABLE_REPORT_TYPES)
        self.assertIn('AccountStatistics', CREATABLE_REPORT_TYPES)
        self.assertIn('asset_id', REPORT_FILTER_FIELDS['AssetStatistics'])
        self.assertIn('account', REPORT_FILTER_FIELDS['AccountStatistics'])

    def test_build_template_item_supports_statistics_reports(self):
        asset_item = build_template_item('AssetStatistics')
        account_item = build_template_item('AccountStatistics')
        self.assertEqual(asset_item['tp'], 'AssetStatistics')
        self.assertEqual(account_item['tp'], 'AccountStatistics')
        self.assertIn('asset_id', asset_item['filters'])
        self.assertIn('account', account_item['filters'])


class ReportPermissionMappingTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_create_uses_type_specific_create_permission(self):
        view = ReportViewSet()
        view.action = 'create'
        view.request = self.factory.post('/api/v1/reports/reports/', {
            'tp': 'AssetReport'
        }, format='json')
        perms = view.get_rbac_perms()
        self.assertEqual(perms['create'], 'rbac.add_assetactivityreport')

    @patch('reports.api.report.Report.objects')
    def test_destroy_uses_type_specific_delete_permission(self, mocked_objects):
        view = ReportViewSet()
        view.action = 'destroy'
        view.request = self.factory.delete('/api/v1/reports/reports/1/')
        view.kwargs = {'pk': '1'}
        mocked_objects.filter.return_value.values_list.return_value.first.return_value = 'AccountStatistics'

        perms = view.get_rbac_perms()

        self.assertEqual(perms['destroy'], 'rbac.delete_accountstatisticsreport')