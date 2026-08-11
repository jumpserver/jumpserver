from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from audits.tasks import batch_delete, delete_expired_commands_by_day


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
