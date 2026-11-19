import json
from copy import deepcopy
from unittest.mock import MagicMock, call, patch

from django.test import RequestFactory, SimpleTestCase
from django.utils import translation

from audits.handler import OperatorLogHandler
from audits.tasks import batch_delete, delete_expired_commands_by_day


class OperateLogRedactionTestCase(SimpleTestCase):
    def setUp(self):
        self.handler = object.__new__(OperatorLogHandler)
        request = RequestFactory().post('/', REMOTE_ADDR='127.0.0.1')
        request.user = MagicMock(is_authenticated=True)
        self.enterContext(patch('audits.handler.current_request', request))

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
        self.handler.get_org_id = MagicMock(return_value='test-org')
        before = {'Attrs': {'name': 'attrs', 'value': {'access_key_secret': 'old-secret'}}}
        after = {'Attrs': {'name': 'attrs', 'value': {'access_key_secret': 'new-secret'}}}

        self.handler.create_or_update_operate_log(
            'update', 'Cloud account', before=before, after=after,
            resource_display='test-account',
        )

        self.handler.log_client.save.assert_called_once()
        saved = self.handler.log_client.save.call_args.kwargs
        self.assertEqual(saved['before'], {'Attrs': {'access_key_secret': '******'}})
        self.assertEqual(saved['after'], {'Attrs': {'access_key_secret': '******'}})

    def test_skips_unchanged_values(self):
        self.handler.log_client = MagicMock()
        self.handler.get_org_id = MagicMock(return_value='test-org')
        data = {'Attrs': {'name': 'attrs', 'value': {'access_key_secret': 'same-secret'}}}

        self.handler.create_or_update_operate_log(
            'update', 'Cloud account', before=data, after=deepcopy(data),
            resource_display='test-account',
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
