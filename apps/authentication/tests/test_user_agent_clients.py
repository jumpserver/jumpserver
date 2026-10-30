import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from urllib.parse import urlsplit
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.db import close_old_connections, transaction
from django.urls import resolve
from django.utils import timezone
from oauth2_provider.models import (
    get_application_model, get_access_token_model, get_grant_model, get_id_token_model, get_refresh_token_model,
)
from rest_framework.test import APIRequestFactory, force_authenticate
from oauthlib.common import Request as OAuthRequest
from oauthlib.oauth2 import InvalidGrantError, InvalidScopeError, InvalidRequestError

from orgs.models import Organization
from audits.models import OperateLog
from authentication.backends.oauth2_provider.agent import AgentOAuth2Validator
from authentication.models.client_login_session import ClientLoginSession
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.models import Role
from terminal.agent_service import ALL_AGENT_ORGANIZATIONS
from terminal.models import AgentApplication, AgentOAuthBinding, AgentSession, AgentAction, AgentEvent, Terminal
from users.models import User


class UserAgentClientTests(TestCase):
    url = '/api/v1/authentication/user-agent-clients/'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='personal-agent-user')
        cls.other = User.objects.create(username='personal-agent-other')
        cls.manager = User.objects.create(username='personal-agent-manager')
        cls.org_manager = User.objects.create(username='personal-agent-org-manager')
        cls.first = Organization.objects.create(name='Personal first')
        cls.second = Organization.objects.create(name='Personal second')
        for org in (cls.first, cls.second):
            org.add_member(cls.user)
            org.add_member(cls.other)
        cls.manager.system_roles.add_role_system_admin()
        with tmp_to_org(cls.first):
            cls.org_manager.org_roles.add(Role.BuiltinRole.org_admin.get_role())
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

    def authorize(self, user):
        access = get_access_token_model().objects.create(
            user=user, application=self.application, token=uuid.uuid4().hex, scope='agent:access',
            resource=[self.registration.resource], expires=timezone.now() + timedelta(minutes=5),
        )
        refresh = get_refresh_token_model().objects.create(
            user=user, application=self.application, access_token=access, token=uuid.uuid4().hex,
            token_family=uuid.uuid4(), resource=[self.registration.resource],
        )
        for subject in ({'access_token': access}, {'refresh_family': refresh.token_family}):
            AgentOAuthBinding.objects.create(user=user, application=self.application, org_id=ALL_AGENT_ORGANIZATIONS, **subject)
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
        self.authorize(self.other)
        self.assertEqual(self.request(user=self.user).data['count'], 0)
        access, refresh = self.authorize(self.user)
        self.authorize(self.user)
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
        access, _ = self.authorize(self.user)
        get_access_token_model().objects.filter(pk=access.pk).update(expires=timezone.now() - timedelta(seconds=1))
        self.second.members.through.objects_raw.filter(user=self.user, org_id=self.second.pk).delete()
        client = self.request(user=self.user).data['results'][0]
        self.assertTrue(client['all_organizations'])
        self.assertEqual(client['organizations'], [{'id': str(self.first.pk), 'name': self.first.name}])
        self.assertEqual(client['status'], 'active')
        get_refresh_token_model().objects.filter(user=self.user).update(revoked=timezone.now())
        self.assertEqual(self.request(user=self.user).data['results'][0]['status'], 'expired')
        self.authorize(self.user)
        client = self.request(user=self.user).data['results'][0]
        self.assertTrue(client['all_organizations'])
        self.assertEqual(client['organizations'], [{'id': str(self.first.pk), 'name': self.first.name}])
        AgentApplication.objects.filter(pk=self.registration.pk).update(is_active=False)
        self.assertEqual(self.request(user=self.user).data['results'][0]['status'], 'disabled')

    def test_admins_cannot_use_personal_api_to_read_or_revoke_other_users_clients(self):
        access, refresh = self.authorize(self.user)
        for admin in (self.manager, self.org_manager):
            with self.subTest(admin=admin):
                path = f'{self.url}?user_id={self.user.pk}'
                response = self.request(path=path, user=admin)
                self.assertEqual(response.data['count'], 0)
                self.assertEqual(response['Cache-Control'], 'no-store')
                path = f'{self.url}{self.application.pk}/'
                self.assertEqual(self.request('get', path + f'?user_id={self.user.pk}', admin).status_code, 404)
                self.assertEqual(self.request('post', path + f'revoke/?user_id={self.user.pk}', admin).status_code, 404)
        self.assertTrue(get_access_token_model().objects.filter(pk=access.pk).exists())
        self.assertIsNone(get_refresh_token_model().objects.get(pk=refresh.pk).revoked)

    def test_admin_can_manage_only_own_authorization_of_shared_client(self):
        self.first.add_member(self.manager)
        self.authorize(self.manager)
        access, refresh = self.authorize(self.user)
        response = self.request(path=f'{self.url}?user_id={self.user.pk}', user=self.manager)
        client = response.data['results'][0]
        self.assertEqual(response.data['count'], 1)
        self.assertTrue(client['all_organizations'])
        self.assertIn({'id': str(self.first.pk), 'name': self.first.name}, client['organizations'])
        self.assertNotIn('registration_id', client)
        self.assertNotIn('is_active', client)
        path = f'{self.url}{self.application.pk}/revoke/?user_id={self.user.pk}'
        self.assertEqual(self.request('post', path, self.manager).status_code, 204)
        self.assertFalse(AgentOAuthBinding.objects.filter(user=self.manager).exists())
        self.assertTrue(AgentOAuthBinding.objects.filter(user=self.user).exists())
        self.assertTrue(get_access_token_model().objects.get(pk=access.pk).is_valid())
        self.assertIsNone(get_refresh_token_model().objects.get(pk=refresh.pk).revoked)
        self.assertTrue(AgentApplication.objects.get(pk=self.registration.pk).is_active)

    def test_revoke_removes_only_own_authorizations_and_keeps_audit(self):
        access, _ = self.authorize(self.user)
        self.authorize(self.user)
        other_access, other_refresh = self.authorize(self.other)
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
        access, _ = self.authorize(self.other)
        path = f'{self.url}{self.application.pk}/revoke/'
        self.assertEqual(self.request('post', path, self.user).status_code, 404)
        with patch('authentication.api.agent_client_user.record_client_operation', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.request('post', path, self.other)
        self.assertTrue(get_access_token_model().objects.filter(pk=access.pk).exists())
        self.assertTrue(AgentOAuthBinding.objects.filter(user=self.other).exists())
        self.assertTrue(AgentApplication.objects.get(pk=self.registration.pk).is_active)
        self.application.refresh_from_db()
        self.assertEqual(self.application.redirect_uris, 'http://127.0.0.1/callback')

    def test_last_user_revoke_recycles_unused_registration_and_audits_its_identity(self):
        self.authorize(self.user)
        self.authorize(self.user)
        path = f'{self.url}{self.application.pk}/revoke/'
        self.assertEqual(self.request('post', path, self.user).status_code, 204)
        self.assertFalse(get_application_model().objects.filter(pk=self.application.pk).exists())
        self.assertFalse(AgentApplication.objects.filter(pk=self.registration.pk).exists())
        self.assertEqual(self.request(user=self.user).data['count'], 0)
        pending = OAuthRequest('http://localhost/token')
        pending.client, pending.scopes = self.application, ['agent:access']
        with self.assertRaises(InvalidScopeError):
            AgentOAuth2Validator().save_authorization_code(self.application.client_id, {'code': 'late-code'}, pending)
        with self.assertRaises(InvalidGrantError):
            AgentOAuth2Validator().save_bearer_token({'scope': 'agent:access'}, pending)
        with tmp_to_root_org():
            log = OperateLog.objects.get(resource_id=str(self.registration.pk), resource_type='Agent MCP client')
            self.assertIn(self.application.client_id, log.diff['Client ID'])
            self.assertIn('removed unused client registration', log.diff['Result'])

    def test_last_user_revoke_preserves_cross_org_audit_and_login_history(self):
        access, _ = self.authorize(self.user)
        with tmp_to_org(self.second):
            session = AgentSession.objects.create(
                user=self.user, application=self.application, terminal=Terminal.objects.create(name='recycle-audit-node'),
                oauth_token=access, resource=self.registration.resource, idempotency_key='recycle-history',
                request_hash='0' * 64, date_expires=timezone.now() + timedelta(minutes=5),
            )
            action = AgentAction.objects.create(
                session=session, user=self.user, application=self.application, kind='execute_command',
                idempotency_key='recycle-action', request_hash='1' * 64, status='succeeded',
            )
            event = AgentEvent.objects.create(
                event_id=uuid.uuid4(), action=action, sequence=1, state='succeeded',
                payload={'stream': 'stdout', 'data': 'retained output'}, payload_hash='2' * 64,
            )
        login = ClientLoginSession.objects.create(
            application=self.application, user=self.other, token_family=uuid.uuid4(),
            authenticated_at=timezone.now(), last_activity_at=timezone.now(),
            revoked_at=timezone.now(), revoke_reason='logout',
        )
        response = self.request('post', f'{self.url}{self.application.pk}/revoke/', self.user)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AgentApplication.objects.filter(pk=self.registration.pk).exists())
        self.application.refresh_from_db()
        self.assertEqual(self.application.client_id, 'personal-agent-client')
        self.assertEqual(self.application.redirect_uris, '')
        self.assertTrue(ClientLoginSession.objects.filter(pk=login.pk, user=self.other).exists())
        with tmp_to_root_org():
            session.refresh_from_db()
            self.assertIsNone(session.oauth_token_id)
            self.assertEqual(AgentAction.objects.get(pk=action.pk).application_id, self.application.pk)
            event.refresh_from_db()
            self.assertEqual(event.payload, {'stream': 'stdout', 'data': 'retained output'})
            self.assertEqual(event.payload_hash, '2' * 64)

    def test_recycle_keeps_login_history_without_agent_audit_references(self):
        self.authorize(self.user)
        login = ClientLoginSession.objects.create(
            application=self.application, user=self.user, token_family=uuid.uuid4(),
            authenticated_at=timezone.now(), last_activity_at=timezone.now(),
        )
        self.assertEqual(self.request('post', f'{self.url}{self.application.pk}/revoke/', self.user).status_code, 204)
        self.assertFalse(AgentApplication.objects.filter(pk=self.registration.pk).exists())
        self.assertTrue(ClientLoginSession.objects.filter(pk=login.pk).exists())

    def test_other_users_authorization_records_each_prevent_recycling(self):
        expires = timezone.now() + timedelta(minutes=5)
        cases = (
            (get_access_token_model(), {'token': uuid.uuid4().hex, 'expires': expires}),
            (get_refresh_token_model(), {'token': uuid.uuid4().hex, 'token_family': uuid.uuid4()}),
            (get_grant_model(), {'code': uuid.uuid4().hex, 'expires': expires, 'redirect_uri': 'http://127.0.0.1/callback'}),
            (get_id_token_model(), {'expires': expires}),
            (AgentOAuthBinding, {'org_id': self.second.pk, 'refresh_family': uuid.uuid4()}),
        )
        for model, fields in cases:
            with self.subTest(model=model.__name__):
                self.authorize(self.user)
                other = model.objects.create(user=self.other, application=self.application, **fields)
                before = model.objects.filter(pk=other.pk).values().get()
                response = self.request('post', f'{self.url}{self.application.pk}/revoke/', self.user)
                self.assertEqual(response.status_code, 204)
                self.assertEqual(model.objects.filter(pk=other.pk).values().get(), before)
                self.assertTrue(AgentApplication.objects.get(pk=self.registration.pk).is_active)
                self.application.refresh_from_db()
                self.assertEqual(self.application.redirect_uris, 'http://127.0.0.1/callback')
                other.delete()


class UserAgentClientConcurrencyTests(TransactionTestCase):
    def setUp(self):
        Organization.expire_orgs_mapping()
        Organization.default()
        Organization.system()

    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_authorizations_cannot_exceed_ten_clients(self):
        owner = User.objects.create(username='quota-concurrent-owner')
        org = Organization.objects.create(name='Client quota concurrency')
        org.add_member(owner)
        resource = 'https://jumpserver.example/koko/mcp'
        applications = []
        for index in range(11):
            app = get_application_model().objects.create(
                name='Quota concurrent client', client_id=uuid.uuid4().hex, client_type='public',
                authorization_grant_type='authorization-code', redirect_uris='http://127.0.0.1/callback',
            )
            AgentApplication.objects.create(application=app, resource=resource)
            if index < 9:
                grant = get_grant_model().objects.create(
                    user=owner, application=app, code=uuid.uuid4().hex,
                    expires=timezone.now() + timedelta(minutes=5), redirect_uri=app.redirect_uris,
                )
                AgentOAuthBinding.objects.create(user=owner, application=app, grant=grant, org_id=ALL_AGENT_ORGANIZATIONS)
            applications.append(app)
        start = Barrier(2)

        def authorize(app):
            close_old_connections()
            try:
                with tmp_to_org(org):
                    request = OAuthRequest('http://localhost/authorize')
                    request.client, request.user, request.scopes = app, owner, ['agent:access']
                    request.redirect_uri, request.resource = app.redirect_uris, [resource]
                    request.code_challenge, request.code_challenge_method = 'a' * 43, 'S256'
                    start.wait(timeout=5)
                    try:
                        AgentOAuth2Validator().save_authorization_code(app.client_id, {'code': uuid.uuid4().hex}, request)
                        return 'authorized'
                    except InvalidRequestError:
                        return 'limited'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(authorize, app) for app in applications[9:]]
            self.assertCountEqual([future.result(timeout=10) for future in results], ['authorized', 'limited'])
        self.assertEqual(AgentOAuthBinding.objects.filter(user=owner).values('application_id').distinct().count(), 10)

    @skipUnlessDBFeature('has_select_for_update')
    def test_authorization_committed_while_revoke_waits_keeps_shared_registration(self):
        owner = User.objects.create(username='recycle-concurrent-owner')
        other = User.objects.create(username='recycle-concurrent-other')
        org = Organization.objects.create(name='Concurrent client org')
        org.add_member(owner)
        org.add_member(other)
        application = get_application_model().objects.create(
            name='Concurrent Agent', client_type='public', authorization_grant_type='authorization-code',
            redirect_uris='http://127.0.0.1/callback', registration_source='dcr',
        )
        registration = AgentApplication.objects.create(application=application, resource='https://jumpserver.example/koko/mcp')
        access = get_access_token_model().objects.create(
            user=owner, application=application, token=uuid.uuid4().hex,
            scope='agent:access', expires=timezone.now() + timedelta(minutes=5),
        )
        AgentOAuthBinding.objects.create(user=owner, application=application, access_token=access, org_id=ALL_AGENT_ORGANIZATIONS)
        started = Event()

        def revoke():
            close_old_connections()
            try:
                with tmp_to_org(org):
                    request = APIRequestFactory().post(f'{UserAgentClientTests.url}{application.pk}/revoke/')
                    force_authenticate(request, user=owner)
                    started.set()
                    match = resolve(request.path)
                    return match.func(request, **match.kwargs).status_code
            finally:
                close_old_connections()

        code = uuid.uuid4().hex
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                get_application_model().objects.select_for_update().get(pk=application.pk)
                pending_revoke = pool.submit(revoke)
                self.assertTrue(started.wait(5))
                self.assertFalse(pending_revoke.done())
                request = OAuthRequest('http://localhost/authorize')
                request.client, request.user, request.scopes = application, other, ['agent:access']
                request.redirect_uri, request.resource = application.redirect_uris, [registration.resource]
                request.code_challenge, request.code_challenge_method = 'a' * 43, 'S256'
                AgentOAuth2Validator().save_authorization_code(application.client_id, {'code': code}, request)
            self.assertEqual(pending_revoke.result(timeout=10), 204)
        self.assertTrue(AgentApplication.objects.get(pk=registration.pk).is_active)
        self.assertTrue(get_grant_model().objects.filter(code=code, user=other).exists())
        self.assertTrue(AgentOAuthBinding.objects.filter(user=other, application=application).exists())
        self.assertFalse(get_access_token_model().objects.filter(pk=access.pk).exists())
