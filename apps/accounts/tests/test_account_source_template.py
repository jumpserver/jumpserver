import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from accounts.serializers.account.account import AccountDetailSerializer


class AccountSourceTemplateTests(SimpleTestCase):
    def setUp(self):
        self.template_id = uuid.uuid4()
        self.account = SimpleNamespace(source='template', source_id=str(self.template_id),
                                       org_id='org', follow_template=False)

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter')
    def test_detached_account_still_exposes_source_template(self, query):
        query.return_value.values.return_value.first.return_value = {
            'id': self.template_id, 'name': 'Linux admin',
        }
        self.assertEqual(AccountDetailSerializer.get_source_template(self.account), {
            'id': str(self.template_id), 'name': 'Linux admin',
        })
        query.assert_called_once_with(id=str(self.template_id), org_id='org')
        query.return_value.values.assert_called_once_with('id', 'name')

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter')
    def test_non_template_source_does_not_query_templates(self, query):
        self.account.source = 'local'
        self.assertIsNone(AccountDetailSerializer.get_source_template(self.account))
        query.assert_not_called()

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter')
    def test_deleted_template_returns_null_and_preserves_source_id(self, query):
        query.return_value.values.return_value.first.return_value = None
        self.assertIsNone(AccountDetailSerializer.get_source_template(self.account))
        self.assertEqual(self.account.source_id, str(self.template_id))

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter', side_effect=ValueError)
    def test_invalid_legacy_source_id_does_not_break_detail(self, query):
        self.account.source_id = 'invalid'
        self.assertIsNone(AccountDetailSerializer.get_source_template(self.account))

    def test_source_template_is_read_only(self):
        self.assertTrue(AccountDetailSerializer().fields['source_template'].read_only)
