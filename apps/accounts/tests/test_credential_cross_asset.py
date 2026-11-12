from uuid import uuid4
from unittest.mock import patch

from accounts.api.account.account import AccountViewSet
from accounts.credential_rotation import preflight
from accounts.models import Account, IntegrationApplication
from accounts.serializers import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase
from assets.models import Asset


class CrossAssetRotationTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.precheck_patch.stop()
        self.other_asset = Asset.objects.create(
            name='credential-test-ha', address='127.0.0.2', platform=self.platform,
        )
        self.backup.asset = self.other_asset
        self.backup.save()
        self.credential.refresh_from_db()

    def test_cross_asset_policy_can_be_created_and_updated(self):
        self.credential.delete()
        serializer = ApplicationCredentialSerializer(data={
            'name': 'HA database', 'mode': 'alternating_rotation',
            'account': str(self.primary.id), 'alternate_account': str(self.backup.id),
            'applications': [str(self.application.id)],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        credential = serializer.save()
        self.assertEqual(credential.active_account_id, self.primary.id)
        serializer = ApplicationCredentialSerializer(
            credential, data={'account': str(self.backup.id), 'alternate_account': str(self.primary.id)},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        credential = serializer.save()
        data = ApplicationCredentialSerializer(credential).data
        self.assertEqual(str(data['account']['asset']['id']), str(self.other_asset.id))
        self.assertEqual(str(data['alternate_account']['asset']['id']), str(self.asset.id))

    def test_preflight_verifies_target_asset_before_publishing(self):
        from accounts.credential_rotation import CredentialRotationManager
        from accounts.models import AutomationExecution
        from accounts.tests.test_credential_preflight import CredentialPreflightTests

        with patch('accounts.credential_rotation.preflight.dispatch'):
            CredentialRotationManager(self.credential.id).start(self.admin.name, self.admin.id)
        execution = preflight.latest(self.credential)
        self.assertEqual(execution.snapshot['assets'], [str(self.other_asset.id)])
        self.assertEqual(execution.snapshot['accounts'], [str(self.backup.id)])
        with patch.object(
            AutomationExecution, 'start', autospec=True,
            side_effect=CredentialPreflightTests.verified,
        ):
            preflight.run(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.backup.id)
        rotation = self.credential.rotation_records.get()
        self.assertEqual(rotation.change_account.asset_id, self.asset.id)

    def test_cross_asset_policy_still_requires_distinct_accounts_and_same_secret_type(self):
        for changes, field in [
            ({'alternate_account': str(self.primary.id)}, 'non_field_errors'),
            ({'applications': []}, 'applications'),
        ]:
            with self.subTest(changes=changes):
                serializer = ApplicationCredentialSerializer(self.credential, data=changes, partial=True)
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)
        self.backup.secret_type = 'ssh_key'
        self.backup.save()
        self.credential.refresh_from_db()
        serializer = ApplicationCredentialSerializer(self.credential, data={}, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_cross_asset_accounts_cannot_cross_organizations(self):
        from common.exceptions import JMSException

        # Account.save normally aligns its organization to the asset. Simulate
        # inconsistent stored data to exercise both validation boundaries.
        Account.objects.filter(pk=self.backup.pk).update(org_id=str(uuid4()))
        self.credential.refresh_from_db()
        serializer = ApplicationCredentialSerializer(self.credential, data={}, partial=True)
        self.assertFalse(serializer.is_valid())
        with self.assertRaises(JMSException):
            preflight.check(self.credential)

    def test_cross_asset_accounts_must_be_authorized_for_all_applications(self):
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save()
        serializer = ApplicationCredentialSerializer(self.credential, data={}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('applications', serializer.errors)

    def account_choices(self, application_ids, **params):
        view = AccountViewSet.as_view({'get': 'list'})
        response = view(self.request('get', '/api/v1/accounts/accounts/', data={
            'integrationapplications': application_ids,
            'fields': 'id,name,username,asset', **params,
        }))
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        return data['results'] if isinstance(data, dict) else data

    def test_account_choices_intersect_application_scopes_and_support_search(self):
        other = IntegrationApplication.objects.create(
            name='ha-reader', accounts={'type': 'ids', 'ids': [str(self.backup.id)]},
        )
        ids = f'{self.application.id},{other.id}'
        choices = self.account_choices(ids)
        self.assertEqual([str(item['id']) for item in choices], [str(self.backup.id)])
        self.assertEqual(str(choices[0]['asset']['id']), str(self.other_asset.id))
        self.assertEqual(self.account_choices(ids, search='no-such-account'), [])
        self.assertEqual(len(self.account_choices(ids, search=self.other_asset.address)), 1)
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save()
        self.assertEqual(self.account_choices(ids), [])

    def test_invalid_or_missing_application_scope_returns_no_choices(self):
        for ids in ['invalid', f'{self.application.id},{uuid4()}']:
            with self.subTest(ids=ids):
                self.assertEqual(self.account_choices(ids), [])
