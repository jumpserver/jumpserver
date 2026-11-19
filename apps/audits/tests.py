import json
from copy import deepcopy
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase
from django.utils import translation
from django.utils.dateparse import parse_datetime
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from audits.api import TicketAuditViewSet
from audits.handler import OperatorLogHandler
from audits.tasks import batch_delete, delete_expired_commands_by_day
from tickets.models import Ticket


class OperateLogRedactionTestCase(SimpleTestCase):
    def setUp(self):
        self.handler = object.__new__(OperatorLogHandler)

    def test_masks_nested_dicts_without_changing_source_data(self):
        before = {'Attrs': {'name': 'attrs', 'value': {
            'access_key_secret': 'old-cloud-secret',
            'credentials': {'Client_Secret': 'old-client-secret'},
            'region': 'ap-shanghai',
            'enabled': False,
            'secret_type': 'password',
            'secret_strategy': 'custom',
            'password_rules': {'length': 16},
        }}}
        after = deepcopy(before)
        after['Attrs']['value']['access_key_secret'] = 'new-cloud-secret'
        after['Attrs']['value']['credentials']['Client_Secret'] = 'new-client-secret'
        original = deepcopy((before, after))

        masked_before, masked_after = self.handler.data_processing(before, after)

        expected = {'Attrs': {
            'access_key_secret': '******',
            'credentials': {'Client_Secret': '******'},
            'region': 'ap-shanghai',
            'enabled': False,
            'secret_type': 'password',
            'secret_strategy': 'custom',
            'password_rules': {'length': 16},
        }}
        self.assertEqual(masked_before, expected)
        self.assertEqual(masked_after, expected)
        self.assertEqual((before, after), original)

    def test_masks_nested_lists_before_serialization(self):
        values = [
            {'password': 'list-password', 'ports': [22, 443]},
            [{'token': 'nested-token', 'enabled': True}],
        ]
        expected = [
            {'password': '******', 'ports': [22, 443]},
            [{'token': '******', 'enabled': True}],
        ]
        for container in (list, tuple):
            for prefix in ([], ['primary']):
                with self.subTest(container=container, prefix=prefix):
                    data = {'Attrs': {'name': 'attrs', 'value': container(prefix + values)}}
                    original = deepcopy(data)

                    before, after = self.handler.data_processing(data, data)

                    self.assertEqual(json.loads(before['Attrs']), prefix + expected)
                    self.assertEqual(json.loads(after['Attrs']), prefix + expected)
                    self.assertEqual(data, original)

    def test_masks_lists_inside_dicts(self):
        data = {'Attrs': {'name': 'attrs', 'value': {
            'regions': ['ap-shanghai'],
            'accounts': [{'credentials': [{'private_key': 'nested-private-key'}]}],
        }}}
        original = deepcopy(data)

        before, after = self.handler.data_processing(None, data)

        self.assertIsNone(before)
        self.assertEqual(after, {'Attrs': {
            'regions': ['ap-shanghai'],
            'accounts': [{'credentials': [{'private_key': '******'}]}],
        }})
        self.assertEqual(data, original)

    @translation.override('en')
    def test_preserves_top_level_redaction_and_display(self):
        data = {
            'Secret': {'name': 'password', 'value': 'top-level-password'},
            'Enabled': {'name': 'enabled', 'value': True},
            'Disabled': {'name': 'disabled', 'value': False},
            'Names': {'name': 'names', 'value': ['alice', 'bob']},
            'Ports': {'name': 'ports', 'value': [22, 443]},
            'Empty': {'name': 'empty', 'value': []},
            'Type': {'name': 'secret_type', 'value': 'password'},
        }
        before, after = self.handler.data_processing(data, None)

        self.assertIsNone(after)
        self.assertEqual(before, {
            'Secret': '******', 'Enabled': 'Yes', 'Disabled': 'No',
            'Names': 'alice,bob', 'Ports': '[22, 443]', 'Empty': '',
            'Type': 'password',
        })

    @patch('audits.handler.transaction.atomic')
    def test_records_secret_only_changes_with_masked_values(self, atomic):
        self.handler.log_client = MagicMock()
        before = {'Attrs': {'name': 'attrs', 'value': {'access_key_secret': 'old-secret'}}}
        after = {'Attrs': {'name': 'attrs', 'value': {'access_key_secret': 'new-secret'}}}

        self.handler.create_or_update_operate_log(
            'update', 'Cloud account', before=before, after=after,
            user=MagicMock(is_authenticated=True), org_id='test-org',
            remote_addr='127.0.0.1', resource_display='test-account', resource_id='test-id',
        )

        self.handler.log_client.save.assert_called_once()
        saved = self.handler.log_client.save.call_args.kwargs
        self.assertEqual(saved['before'], {'Attrs': {'access_key_secret': '******'}})
        self.assertEqual(saved['after'], {'Attrs': {'access_key_secret': '******'}})

    def test_skips_unchanged_values(self):
        self.handler.log_client = MagicMock()
        data = {'Attrs': {'name': 'attrs', 'value': {'access_key_secret': 'same-secret'}}}

        self.handler.create_or_update_operate_log(
            'update', 'Cloud account', before=data, after=deepcopy(data),
            user=MagicMock(is_authenticated=True), org_id='test-org',
            remote_addr='127.0.0.1', resource_display='test-account', resource_id='test-id',
        )

        self.handler.log_client.save.assert_not_called()


class AuditTaskTestCase(SimpleTestCase):
    @patch('audits.tasks.transaction.atomic')
    def test_batch_delete_always_reads_first_page(self, atomic):
        queryset = MagicMock()
        queryset.count.return_value = 7
        queryset.__getitem__.return_value.values_list.side_effect = [
            [1, 2, 3], [4, 5, 6], [7],
        ]

        batch_delete(queryset, batch_size=3)

        self.assertEqual(
            queryset.__getitem__.call_args_list,
            [call(slice(None, 3))] * 3,
        )
        self.assertEqual(
            queryset.model.objects.filter.call_args_list,
            [
                call(id__in=[1, 2, 3]),
                call(id__in=[4, 5, 6]),
                call(id__in=[7]),
            ],
        )
        atomic.assert_called_once_with()

    @patch('audits.tasks.Command')
    def test_delete_expired_commands_with_empty_queryset(self, command):
        queryset = command.objects.order_by.return_value.filter.return_value
        queryset.aggregate.return_value = {'min_ts': None}

        delete_expired_commands_by_day(keep_days=30)


class TicketAuditDateFilterTestCase(SimpleTestCase):
    @patch('audits.api.current_org', new_callable=MagicMock)
    def test_list_and_exports_filter_created_dates_with_existing_filters(self, current_org):
        current_org.is_root.return_value = False
        current_org.id = '00000000-0000-0000-0000-000000000002'
        dates = {
            'date_from': '2026-09-01T00:00:00+08:00',
            'date_to': '2026-09-30T23:59:59.999+08:00',
        }
        date_field = Ticket._meta.get_field('date_created')
        for format_ in ('json', 'csv', 'xlsx'):
            for keys in ((), ('date_from',), ('date_to',), tuple(dates)):
                with self.subTest(format=format_, dates=keys):
                    params = {
                        'format': format_, 'limit': 20,
                        'type': 'login_asset_confirm', 'state': 'approved',
                        **{key: dates[key] for key in keys},
                    }
                    request = APIRequestFactory().get('/api/v1/audits/tickets/', params)
                    view = TicketAuditViewSet(
                        request=Request(request), action='list', format_kwarg=format_,
                    )
                    queryset = view.filter_queryset(view.get_queryset())
                    lookups = {
                        lookup.lookup_name: lookup.rhs
                        for lookup in queryset.query.where.children
                        if getattr(getattr(lookup, 'lhs', None), 'target', None) == date_field
                    }
                    self.assertEqual(lookups, {
                        lookup: parse_datetime(dates[key])
                        for key, lookup in (('date_from', 'gte'), ('date_to', 'lte'))
                        if key in keys
                    })
                    _, sql_params = queryset.query.sql_with_params()
                    for value in (str(current_org.id), 'login_asset_confirm', 'approved'):
                        self.assertIn(value, sql_params)
