from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import serializers

from accounts.api.account.personal import PersonalAssetCredentialViewSet
from accounts.personal_credentials import get_personal_credential_update_diff
from accounts.serializers import PersonalAssetCredentialSerializer


class PersonalCredentialUpdateAuditTestCase(SimpleTestCase):
    def setUp(self):
        self.credential = SimpleNamespace(
            username='old-user',
            secret_type='password',
            comment='old comment',
            is_active=True,
        )

    @staticmethod
    def get_value(diff, field_name):
        return next(
            item['value'] for item in diff.values()
            if item['name'] == field_name
        )

    def test_update_diff_records_changed_values_and_masks_secret(self):
        before, after = get_personal_credential_update_diff(
            self.credential,
            {
                'secret_type': 'ssh_key',
                'comment': 'new comment',
                'is_active': False,
                'secret': 'new-plaintext-secret',
                'expected_version': 1,
            },
        )

        self.assertEqual(self.get_value(before, 'secret_type'), 'password')
        self.assertEqual(self.get_value(after, 'secret_type'), 'ssh_key')
        self.assertEqual(self.get_value(before, 'comment'), 'old comment')
        self.assertEqual(self.get_value(after, 'comment'), 'new comment')
        self.assertIs(self.get_value(before, 'is_active'), True)
        self.assertIs(self.get_value(after, 'is_active'), False)
        self.assertEqual(self.get_value(before, 'secret'), '******')
        self.assertEqual(self.get_value(after, 'secret'), '******')
        self.assertNotIn('new-plaintext-secret', repr((before, after)))
        self.assertNotIn(
            'expected_version', {item['name'] for item in before.values()}
        )

    def test_update_diff_omits_unchanged_and_immutable_fields(self):
        before, after = get_personal_credential_update_diff(
            self.credential,
            {
                'username': 'new-user',
                'asset': object(),
                'protocol': 'ssh',
                'expected_version': 1,
            },
        )

        self.assertEqual(before, {})
        self.assertEqual(after, {})

    def test_serializer_rejects_username_change(self):
        serializer = PersonalAssetCredentialSerializer(instance=self.credential)

        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.validate({
                'username': 'new-user',
                'expected_version': 1,
            })

        self.assertIn('username', cm.exception.detail)

    @patch('accounts.api.account.personal.record_personal_credential_audit')
    def test_perform_update_records_the_pre_save_diff(self, record_audit):
        updated_credential = SimpleNamespace(
            username='old-user',
            secret_type='password',
            comment='new comment',
            is_active=True,
        )
        serializer = SimpleNamespace(
            instance=self.credential,
            validated_data={
                'comment': 'new comment',
                'secret': 'new-plaintext-secret',
                'expected_version': 1,
            },
            save=lambda: updated_credential,
        )
        view = PersonalAssetCredentialViewSet()
        view.request = SimpleNamespace(user=object())

        view.perform_update(serializer)

        kwargs = record_audit.call_args.kwargs
        self.assertEqual(
            self.get_value(kwargs['before'], 'comment'), 'old comment'
        )
        self.assertEqual(
            self.get_value(kwargs['after'], 'comment'), 'new comment'
        )
        self.assertEqual(self.get_value(kwargs['before'], 'secret'), '******')
        self.assertEqual(self.get_value(kwargs['after'], 'secret'), '******')
        self.assertNotIn('new-plaintext-secret', repr(record_audit.call_args))
