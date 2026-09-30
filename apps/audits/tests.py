from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase
from django.utils.dateparse import parse_datetime
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from audits.api import TicketAuditViewSet
from audits.tasks import batch_delete, delete_expired_commands_by_day
from tickets.models import Ticket


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
