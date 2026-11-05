import json
from uuid import uuid4

from accounts.models import (
    Account, ApplicationCredential, CredentialApplicationBinding,
    CredentialClientInstance, CredentialClientStatus, IntegrationApplication,
)
from accounts.tests.base import CredentialTestCase
from accounts.tests.test_application_access import ApplicationAccessTests
from django.test import override_settings
from orgs.models import Organization
from orgs.utils import tmp_to_org


class SDKMetadataTests(CredentialTestCase):
    signed_request = ApplicationAccessTests.signed_request

    def test_application_and_current_instance_are_scoped_and_secret_free(self):
        other = IntegrationApplication.objects.create(name='Other application', secret='other-secret')
        response = self.signed_request('application', {
            'instance_id': 'metadata', 'app_id': str(other.id),
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data, {
            'id': str(self.application.id), 'name': self.application.name,
            'org_id': str(self.org.id), 'is_active': True,
            'accounts_count': 2, 'policies_count': 1,
        })
        client = self.signed_request('client', {'instance_id': 'metadata'})
        self.assertEqual(client.status_code, 200, client.data)
        self.assertEqual(client['Cache-Control'], 'no-store')
        self.assertEqual(client.data['instance_id'], 'metadata')
        self.assertEqual(client.data['type'], 'sdk')
        self.assertEqual(client.data['client_version'], '1.0.0')
        self.assertEqual(client.data['protocol_version'], 1)
        self.assertEqual(client.data['config_schema_version'], 0)
        self.assertEqual(client.data['id'], str(CredentialClientInstance.objects.get(
            application=self.application, instance_id='metadata',
        ).id))
        text = json.dumps([response.data, client.data])
        for secret in (self.application.secret, other.secret, self.primary.secret, self.backup.secret):
            self.assertNotIn(secret, text)
        self.assertFalse(CredentialClientStatus.objects.filter(fetched_revision__gt=0).exists())
        self.assertFalse(CredentialClientStatus.objects.filter(applied_revision__gt=0).exists())
        other_response = self.signed_request('application', {'instance_id': 'other'}, identity=str(other.id), secret=other.secret)
        self.assertEqual(other_response.status_code, 200, other_response.data)
        self.assertEqual(other_response.data['id'], str(other.id))
        other_policy = self.signed_request('policy', {'instance_id': 'other', 'key': self.credential.key}, identity=str(other.id), secret=other.secret)
        self.assertEqual(other_policy.status_code, 404, other_policy.data)

    def test_agent_application_identity_gets_its_own_metadata(self):
        response = self.signed_request('client', {'instance_id': 'agent-metadata'}, source='jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['type'], 'agent')
        self.assertEqual(response.data['config_schema_version'], 1)

    def test_policy_list_and_detail_include_only_bound_authorized_metadata(self):
        hidden = Account.objects.create(name='hidden-account', username='hidden', asset=self.asset, secret='hidden-secret')
        subscription = ApplicationCredential.objects.create(name='Subscribed database')
        subscription.subscription_accounts.set([self.primary, hidden])
        CredentialApplicationBinding.objects.create(credential=subscription, application=self.application)
        unbound = ApplicationCredential.objects.create(name='Unbound')
        response = self.signed_request('policies', {'instance_id': 'policies', 'limit': 1})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual({p['id'] for p in response.data['policies']}, {str(self.credential.id), str(subscription.id)})
        by_id = {p['id']: p for p in response.data['policies']}
        self.assertEqual(by_id[str(subscription.id)]['accounts_count'], 1)
        self.assertIsNone(by_id[str(subscription.id)]['active_account_id'])
        self.assertIsNone(by_id[str(subscription.id)]['account_switch'])
        rotation = by_id[str(self.credential.id)]
        self.assertEqual(rotation['accounts_count'], 2)
        self.assertEqual(rotation['active_account_id'], str(self.primary.id))
        self.assertEqual(set(rotation['account_switch']['account_ids']), {str(self.primary.id), str(self.backup.id)})
        for selector in ({'key': subscription.key}, {'policy_id': str(subscription.id)}):
            detail = self.signed_request('policy', {'instance_id': 'policies', **selector})
            self.assertEqual(detail.status_code, 200, detail.data)
            self.assertEqual(detail.data, by_id[str(subscription.id)])
            self.assertEqual(detail['Cache-Control'], 'no-store')
        text = json.dumps(response.data)
        for secret in (self.application.secret, self.primary.secret, self.backup.secret, hidden.secret, str(hidden.id), str(unbound.id)):
            self.assertNotIn(secret, text)
        filtered = self.signed_request('policies', {'instance_id': 'policies', 'search': 'Subscribed'})
        self.assertEqual([p['id'] for p in filtered.data['policies']], [str(subscription.id)])

    def test_disabled_policy_is_visible_but_unbound_missing_and_unauthorized_are_not(self):
        self.credential.is_active = False
        self.credential.save(update_fields=['is_active'])
        response = self.signed_request('policy', {'instance_id': 'policies', 'key': self.credential.key})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['is_active'])
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save(update_fields=['accounts'])
        listing = self.signed_request('policies', {'instance_id': 'policies'})
        self.assertEqual(listing.data['policies'], [])
        for selector in ({'key': self.credential.key}, {'policy_id': str(uuid4())}):
            response = self.signed_request('policy', {'instance_id': 'policies', **selector})
            self.assertEqual(response.status_code, 404, response.data)
        unbound = ApplicationCredential.objects.create(name='Unbound')
        response = self.signed_request('policy', {'instance_id': 'policies', 'key': unbound.key})
        self.assertEqual(response.status_code, 404, response.data)

    def test_foreign_organization_binding_is_not_visible(self):
        other_org = Organization.objects.create(name='Metadata other organization')
        with tmp_to_org(other_org):
            foreign = ApplicationCredential.objects.create(name='Foreign policy')
        self.assertEqual(foreign.org_id, other_org.id)
        CredentialApplicationBinding.objects.create(credential=foreign, application=self.application)
        response = self.signed_request('policies', {'instance_id': 'policies'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn(str(foreign.id), json.dumps(response.data))
        response = self.signed_request('policy', {'instance_id': 'policies', 'key': foreign.key})
        self.assertEqual(response.status_code, 404, response.data)

    def test_invalid_selectors_missing_identity_and_disabled_client(self):
        for params in ({}, {'key': self.credential.key, 'policy_id': str(self.credential.id)}, {'policy_id': 'invalid'}):
            response = self.signed_request('policy', {'instance_id': 'invalid', **params})
            self.assertEqual(response.status_code, 400, response.data)
        response = self.signed_request('application', {})
        self.assertEqual(response.status_code, 400, response.data)
        CredentialClientInstance.objects.create(application=self.application, instance_id='disabled', type='sdk', is_active=False)
        for action in ('application', 'client', 'policies', 'policy'):
            params = {'instance_id': 'disabled'}
            if action == 'policy': params['key'] = self.credential.key
            response = self.signed_request(action, params)
            self.assertEqual(response.status_code, 403, response.data)

    @override_settings(APPLICATION_ACCOUNT_SCOPE_LIMIT=1)
    def test_scope_limit_is_enforced_on_application_and_policy_queries(self):
        for action in ('application', 'policies', 'policy'):
            params = {'instance_id': 'limit'}
            if action == 'policy': params['key'] = self.credential.key
            response = self.signed_request(action, params)
            self.assertEqual(response.status_code, 403, response.data)
