from django.db import connection
from django.test.utils import CaptureQueriesContext

from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.models import (
    Account, ApplicationCredential, CredentialApplicationBinding, IntegrationApplication,
)
from accounts.tests.base import CredentialTestCase
from assets.models import Asset


class CredentialPolicyListTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.credential.mode = ApplicationCredential.Mode.subscription
        self.credential.account = None
        self.credential.alternate_account = None
        self.credential.active_account = None
        self.credential.save()
        self.credential.subscription_accounts.set([self.primary, self.backup])

    def list_policies(self, **params):
        view = ApplicationCredentialViewSet.as_view({'get': 'list'})
        response = view(self.request(
            'get', '/api/v1/accounts/application-credentials/',
            data={'limit': 10, **params},
        ))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data['results'][0]

    def test_list_counts_accounts_and_distinct_assets_without_client_activity(self):
        asset = Asset.objects.create(
            name='second-database', address='127.0.0.2', platform=self.platform,
        )
        account = Account.objects.create(name='third-account', username='third-account', asset=asset)
        self.credential.subscription_accounts.add(account)
        application = IntegrationApplication.objects.create(name='second-application')
        CredentialApplicationBinding.objects.create(
            credential=self.credential, application=application,
        )

        with CaptureQueriesContext(connection) as queries:
            row = self.list_policies()

        self.assertEqual(row['subscription_accounts_amount'], 3)
        self.assertEqual(row['subscription_assets_amount'], 2)
        self.assertEqual(row['applications_amount'], 2)
        self.assertNotIn('subscription_accounts', row)
        self.assertEqual(len(row['subscription_accounts_preview']), 3)
        self.assertEqual(
            {str(account['id']) for account in row['subscription_accounts_preview']},
            {str(self.primary.id), str(self.backup.id), str(account.id)},
        )
        self.assertNotIn('applications', row)
        self.assertNotIn('last_fetched', row)
        self.assertFalse(any('accounts_credentialclientstatus' in query['sql'] for query in queries))

    def test_large_subscription_has_a_bounded_list_payload(self):
        accounts = Account.objects.bulk_create([
            Account(name=f'large-account-{index}', username=f'large-account-{index}', asset=self.asset)
            for index in range(120)
        ])
        self.credential.subscription_accounts.add(*accounts)

        row = self.list_policies(fields_size='small')

        self.assertEqual(row['subscription_accounts_amount'], 122)
        self.assertEqual(row['subscription_assets_amount'], 1)
        self.assertNotIn('subscription_accounts', row)
        self.assertEqual(len(row['subscription_accounts_preview']), 3)
        self.assertTrue(all('secret' not in account for account in row['subscription_accounts_preview']))
        self.assertNotIn('last_fetched', row)

    def test_detail_keeps_the_account_asset_mapping_without_last_fetched(self):
        view = ApplicationCredentialViewSet.as_view({'get': 'retrieve'})
        response = view(self.request(
            'get', f'/api/v1/accounts/application-credentials/{self.credential.id}/',
        ), pk=self.credential.id)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn('last_fetched', response.data)
        self.assertEqual(
            {str(account['id']) for account in response.data['subscription_accounts']},
            {str(self.primary.id), str(self.backup.id)},
        )
        self.assertTrue(all(
            str(account['asset']['id']) == str(self.asset.id)
            for account in response.data['subscription_accounts']
        ))

    def test_preview_limit_is_per_policy(self):
        accounts = Account.objects.bulk_create([
            Account(name=f'preview-{index}', username=f'preview-{index}', asset=self.asset)
            for index in range(6)
        ])
        self.credential.subscription_accounts.add(*accounts[:2])
        policy = ApplicationCredential.objects.create(name='Second subscription', mode='subscription')
        policy.subscription_accounts.set(accounts[2:])
        view = ApplicationCredentialViewSet.as_view({'get': 'list'})
        response = view(self.request(
            'get', '/api/v1/accounts/application-credentials/', data={'limit': 10},
        ))

        self.assertEqual(response.status_code, 200, response.data)
        rows = {str(row['id']): row for row in response.data['results']}
        for item in [self.credential, policy]:
            preview = rows[str(item.id)]['subscription_accounts_preview']
            self.assertEqual(len(preview), 3)
            self.assertTrue(
                {str(account['id']) for account in preview}.issubset(
                    {str(account.id) for account in item.subscription_accounts.all()},
                ),
            )
