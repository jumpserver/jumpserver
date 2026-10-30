import uuid
from datetime import timedelta
from urllib.parse import urlsplit
from unittest.mock import patch

from django.test import TestCase
from django.db import transaction
from django.urls import resolve
from django.utils import timezone
from oauth2_provider.models import get_application_model, get_access_token_model, get_refresh_token_model
from rest_framework.test import APIRequestFactory, force_authenticate

from orgs.models import Organization
from orgs.utils import tmp_to_org
from terminal.agent_service import ALL_AGENT_ORGANIZATIONS
from terminal.models import AgentApplication, AgentOAuthBinding, AgentSession, Terminal
from users.models import User


class UserAgentClientTests(TestCase):
    url = '/api/v1/authentication/user-agent-clients/'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='personal-agent-user')
        cls.other = User.objects.create(username='personal-agent-other')
        cls.first = Organization.objects.create(name='Personal first')
        cls.second = Organization.objects.create(name='Personal second')
        for org in (cls.first, cls.second):
            org.add_member(cls.user)
            org.add_member(cls.other)
        cls.application = get_application_model().objects.create(
            name='Personal Agent', client_id='personal-agent-client', client_type='public',
            authorization_grant_type='authorization-code', redirect_uris='http://127.0.0.1/callback',
        )
        cls.registration = AgentApplication.objects.create(
            application=cls.application, resource='https://jumpserver.example/koko/mcp',
        )

    def setUp(self):
        self.enterContext(tmp_to_org(self.first))
        self.factory = APIRequestFactory()

    def authorize(self, user, org_id):
        access = get_access_token_model().objects.create(
            user=user, application=self.application, token=uuid.uuid4().hex, scope='agent:access',
            resource=[self.registration.resource], expires=timezone.now() + timedelta(minutes=5),
        )
        refresh = get_refresh_token_model().objects.create(
            user=user, application=self.application, access_token=access, token=uuid.uuid4().hex,
            token_family=uuid.uuid4(), resource=[self.registration.resource],
        )
        for subject in ({'access_token': access}, {'refresh_family': refresh.token_family}):
            AgentOAuthBinding.objects.create(user=user, application=self.application, org_id=org_id, **subject)
        return access, refresh

    def request(self, method='get', path=None, user=None):
        path = path or self.url
        request = getattr(self.factory, method)(path, format='json')
        if user:
            force_authenticate(request, user=user)
        match = resolve(urlsplit(path).path)
        with transaction.atomic():
            return match.func(request, **match.kwargs)

    def test_list_is_self_only_across_orgs_and_never_exposes_credentials(self):
        self.authorize(self.other, self.first.pk)
        self.assertEqual(self.request(user=self.user).data['count'], 0)
        access, refresh = self.authorize(self.user, self.first.pk)
        self.authorize(self.user, self.second.pk)
        for org in (self.first, self.second, Organization.SYSTEM_ID):
            with tmp_to_org(org):
                response = self.request(user=self.user)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 1)
                client = response.data['results'][0]
                self.assertEqual(set(client), {'id', 'name', 'client_id', 'organizations', 'all_organizations', 'status'})
                self.assertEqual({item['id'] for item in client['organizations']}, {str(self.first.pk), str(self.second.pk)})
                self.assertEqual(client['status'], 'active')
                self.assertNotIn(access.token, str(response.data))
                self.assertNotIn(refresh.token, str(response.data))
        self.assertEqual(self.request(user=self.user, path=self.url + '?search=missing').data['count'], 0)
        self.assertEqual(self.request('options', user=self.user).status_code, 200)
        for method in ('get', 'options'):
            self.assertIn(self.request(method).status_code, (401, 403))

    def test_all_org_scope_tracks_membership_and_refresh_status(self):
        access, _ = self.authorize(self.user, ALL_AGENT_ORGANIZATIONS)
        get_access_token_model().objects.filter(pk=access.pk).update(expires=timezone.now() - timedelta(seconds=1))
        self.second.members.through.objects_raw.filter(user=self.user, org_id=self.second.pk).delete()
        client = self.request(user=self.user).data['results'][0]
        self.assertTrue(client['all_organizations'])
        self.assertEqual(client['organizations'], [{'id': str(self.first.pk), 'name': self.first.name}])
        self.assertEqual(client['status'], 'active')
        get_refresh_token_model().objects.filter(user=self.user).update(revoked=timezone.now())
        self.assertEqual(self.request(user=self.user).data['results'][0]['status'], 'expired')
        self.authorize(self.user, self.first.pk)
        client = self.request(user=self.user).data['results'][0]
        self.assertFalse(client['all_organizations'])
        self.assertEqual(client['organizations'], [{'id': str(self.first.pk), 'name': self.first.name}])
        AgentApplication.objects.filter(pk=self.registration.pk).update(is_active=False)
        self.assertEqual(self.request(user=self.user).data['results'][0]['status'], 'disabled')

    def test_revoke_removes_only_own_authorizations_and_keeps_audit(self):
        access, _ = self.authorize(self.user, self.first.pk)
        self.authorize(self.user, self.second.pk)
        other_access, other_refresh = self.authorize(self.other, ALL_AGENT_ORGANIZATIONS)
        session = AgentSession.objects.create(
            user=self.user, application=self.application, terminal=Terminal.objects.create(name='personal-agent-node'),
            oauth_token=access, resource=self.registration.resource, idempotency_key='personal-history',
            request_hash='0' * 64, date_expires=timezone.now() + timedelta(minutes=5),
        )
        path = f'{self.url}{self.application.pk}/revoke/'
        self.assertEqual(self.request('post', path, self.user).status_code, 204)
        for model in (get_access_token_model(), get_refresh_token_model(), AgentOAuthBinding):
            self.assertFalse(model.objects.filter(user=self.user, application=self.application).exists())
            self.assertTrue(model.objects.filter(user=self.other, application=self.application).exists())
        self.assertTrue(get_access_token_model().objects.get(pk=other_access.pk).is_valid())
        self.assertIsNone(get_refresh_token_model().objects.get(pk=other_refresh.pk).revoked)
        self.assertTrue(AgentApplication.objects.get(pk=self.registration.pk).is_active)
        session.refresh_from_db()
        self.assertIsNone(session.oauth_token_id)
        self.assertEqual(self.request('post', path, self.user).status_code, 404)
        self.assertEqual(self.request('get', f'{self.url}{self.application.pk}/', self.user).status_code, 404)

    def test_self_revoke_cannot_touch_another_user_or_rollback_partially(self):
        access, _ = self.authorize(self.other, ALL_AGENT_ORGANIZATIONS)
        path = f'{self.url}{self.application.pk}/revoke/'
        self.assertEqual(self.request('post', path, self.user).status_code, 404)
        with patch('authentication.api.agent_client_user.record_client_operation', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.request('post', path, self.other)
        self.assertTrue(get_access_token_model().objects.filter(pk=access.pk).exists())
        self.assertTrue(AgentOAuthBinding.objects.filter(user=self.other).exists())
