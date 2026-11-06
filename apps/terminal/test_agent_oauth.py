"""Browser consent and the organization boundary across OAuth token rotation."""
import base64
import hashlib
import json
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from django.utils.translation import override
from oauth2_provider.models import get_application_model, get_access_token_model, get_grant_model, get_refresh_token_model
from rest_framework.exceptions import PermissionDenied, ValidationError

from authentication.backends.oauth2_provider.agent import AgentAwareAuthorizationView, AgentAuthorizationServerView, AgentIdentityView
from authentication.backends.oauth2_provider.client_views import ClientTokenView, ClientRevokeTokenView
from authentication.models.client_login_session import ClientLoginSession
from common.sessions.cache import SessionStore
from orgs.models import Organization
from orgs.utils import tmp_to_org
from terminal import agent_service as service
from terminal.models import AgentApplication, AgentOAuthBinding, AgentSession, Terminal
from users.models import User


class AgentInstallGuideTests(SimpleTestCase):
    def test_public_guide_is_read_only_and_contains_no_instance_or_user_data(self):
        from django.contrib.auth.models import AnonymousUser
        from django.urls import resolve, reverse

        url = reverse('authentication:agent-install')
        view = resolve(url).func
        request = RequestFactory().get(url, {'access_token': 'private-request-token'}, HTTP_HOST='untrusted.example')
        request.user = AnonymousUser()
        with self.settings(MCP_PUBLIC_URL='https://private.example/koko/mcp', SITE_URL='https://private.example'):
            response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/markdown; charset=utf-8')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        for value in ('private.example', 'untrusted.example', 'private-request-token'):
            self.assertNotContains(response, value)
        self.assertContains(response, 'codex mcp login jumpserver --scopes agent:access')
        self.assertContains(response, 'jumpserver-mcp setup --url')
        self.assertFalse(getattr(view, 'login_required', True))
        self.assertEqual(view(RequestFactory().post(url)).status_code, 405)


class AgentOAuthOrganizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='agent-org-user', name='Agent org user')
        cls.first = Organization.objects.create(name='Agent first organization')
        cls.second = Organization.objects.create(name='Agent second organization')
        cls.unavailable = Organization.objects.create(name='Agent other organization')
        cls.first.add_member(cls.user)
        cls.second.add_member(cls.user)
        cls.node = Terminal.objects.create(name='agent-org-node', type='koko')
        cls.app = get_application_model().objects.create(
            name='Agent organization client', client_id='agent-org-client', client_type='public',
            authorization_grant_type='authorization-code', redirect_uris='http://127.0.0.1/callback',
            registration_source='dcr',
        )
        cls.resource = 'http://jumpserver.example/koko/mcp'
        AgentApplication.objects.create(application=cls.app, resource=cls.resource)

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.enterContext(tmp_to_org(self.first))
        self.factory = RequestFactory()
        self.verifier = 'a' * 64
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip('=')
        self.authorization = {
            'client_id': self.app.client_id, 'redirect_uri': 'http://127.0.0.1:49123/callback',
            'response_type': 'code', 'scope': service.SCOPE, 'resource': self.resource, 'state': 'org-state',
            'code_challenge': challenge, 'code_challenge_method': 'S256',
        }

    def authorize(self, **extra):
        request = self.factory.post('/authorize/', {**self.authorization, 'allow': 'Authorize', **extra})
        request.user = self.user
        request.session = SessionStore()
        request._dont_enforce_csrf_checks = True
        return AgentAwareAuthorizationView.as_view()(request)

    def code(self):
        response = self.authorize()
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response['Location']).query)
        self.assertEqual(query['state'], ['org-state'])
        return query['code'][0]

    def exchange(self, code, **extra):
        return self.token_request({
            'grant_type': 'authorization_code', 'code': code, 'client_id': self.app.client_id,
            'redirect_uri': self.authorization['redirect_uri'], 'code_verifier': self.verifier, **extra,
        })

    def token_request(self, data):
        return ClientTokenView.as_view()(self.factory.post('/token/', data))

    def issued(self):
        response = self.exchange(self.code())
        self.assertEqual(response.status_code, 200, response.content)
        return json.loads(response.content)

    def test_install_guide_is_accessible_without_a_logged_in_browser(self):
        from django.urls import reverse

        response = self.client.get(reverse('authentication:agent-install'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/markdown'))
        self.assertNotContains(response, self.user.username)

    def introspect(self, result, **extra):
        return service.introspect(self.node, {
            'access_token': result['access_token'], 'resource': self.resource,
            'capabilities': {'version': 1, 'protocols': {'ssh': 'shell'}}, **extra,
        })

    def identity(self, result, resource=None):
        from django.urls import reverse

        with self.settings(MCP_ENABLED=True, MCP_PUBLIC_URL=self.resource, MCP_DCR_ENABLED=False):
            return self.client.get(reverse('authentication:oauth2-provider:agent-identity'),
                                   {'resource': resource or self.resource},
                                   HTTP_AUTHORIZATION='Bearer ' + result['access_token'])

    def test_agent_identity_returns_only_the_bearer_subject_without_general_api_access(self):
        from oauthlib.common import Request as OAuthRequest
        from authentication.backends.oauth2_provider.agent import AgentOAuth2Validator
        from django.urls import resolve, reverse

        result = self.issued()
        response = self.identity(result)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'sub': str(self.user.id)})
        self.assertIn('no-store', response['Cache-Control'])
        self.assertFalse(AgentOAuth2Validator().validate_bearer_token(
            result['access_token'], [], OAuthRequest('http://localhost/api/v1/users/profile/'),
        ))
        view = resolve(reverse('authentication:oauth2-provider:agent-identity')).func
        self.assertFalse(view.login_required)
        request = self.factory.get('/identity/', {'resource': self.resource})
        request.user = self.user
        with self.settings(MCP_ENABLED=True, MCP_PUBLIC_URL=self.resource):
            self.assertEqual(view(request).status_code, 401)
            self.assertEqual(view(self.factory.post('/identity/')).status_code, 405)
        with self.settings(MCP_ENABLED=False):
            self.assertEqual(view(request).status_code, 404)
        with self.settings(SITE_URL='https://jumpserver.example'):
            metadata = AgentAuthorizationServerView().get_metadata(self.factory.get('/metadata'))
        self.assertTrue(metadata['agent_identity_endpoint'].endswith(reverse('authentication:oauth2-provider:agent-identity')))

    def test_agent_identity_rechecks_resource_scope_expiry_revocation_binding_and_user(self):
        for invalid in ('resource', 'scope', 'expired', 'revoked', 'disabled', 'unbound', 'inactive_user'):
            with self.subTest(invalid=invalid):
                AgentApplication.objects.filter(application=self.app).update(is_active=True)
                User.objects.filter(pk=self.user.pk).update(is_active=True)
                result = self.issued()
                token = get_access_token_model().objects.get(token_checksum=hashlib.sha256(result['access_token'].encode()).hexdigest())
                if invalid == 'scope':
                    get_access_token_model().objects.filter(pk=token.pk).update(scope='read')
                elif invalid == 'expired':
                    get_access_token_model().objects.filter(pk=token.pk).update(expires=timezone.now() - timedelta(seconds=1))
                elif invalid == 'revoked':
                    get_refresh_token_model().objects.filter(access_token=token).update(revoked=timezone.now())
                elif invalid == 'disabled':
                    AgentApplication.objects.filter(application=self.app).update(is_active=False)
                elif invalid == 'unbound':
                    AgentOAuthBinding.objects.filter(application=self.app).delete()
                elif invalid == 'inactive_user':
                    User.objects.filter(pk=self.user.pk).update(is_active=False)
                response = self.identity(result, self.resource + '/other' if invalid == 'resource' else None)
                self.assertEqual(response.status_code, 401, response.content)
                self.assertEqual(json.loads(response.content), {'error': 'invalid_token'})

    def remove_membership(self):
        self.second.members.through.objects_raw.filter(user=self.user, org_id=self.second.pk).delete()
        self.assertFalse(self.user.orgs.filter(pk=self.second.pk).exists())

    def fill_client_slots(self, count, user=None):
        user = user or self.user
        applications = []
        for _ in range(count):
            app = get_application_model().objects.create(
                name='Quota client', client_id=uuid.uuid4().hex, client_type='public',
                authorization_grant_type='authorization-code', redirect_uris='http://127.0.0.1/callback',
            )
            AgentApplication.objects.create(application=app, resource=self.resource)
            grant = get_grant_model().objects.create(
                user=user, application=app, code=uuid.uuid4().hex, scope=service.SCOPE,
                redirect_uri=app.redirect_uris, expires=timezone.now() + timedelta(minutes=5),
            )
            AgentOAuthBinding.objects.create(user=user, application=app, org_id=service.ALL_AGENT_ORGANIZATIONS, grant=grant)
            applications.append(app)
        return applications

    def test_client_limit_rejects_eleventh_client_in_form_and_validator(self):
        from oauthlib.common import Request as OAuthRequest
        from oauthlib.oauth2 import InvalidRequestError
        from authentication.backends.oauth2_provider.agent import AgentOAuth2Validator

        self.fill_client_slots(10)
        response = self.authorize()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['form'].errors.as_data()['__all__'][0].code, 'mcp_client_limit')
        request = OAuthRequest('http://localhost/authorize')
        request.client, request.user, request.scopes = self.app, self.user, [service.SCOPE]
        request.redirect_uri, request.resource = self.app.redirect_uris, [self.resource]
        request.code_challenge, request.code_challenge_method = 'a' * 43, 'S256'
        with self.assertRaises(InvalidRequestError):
            AgentOAuth2Validator().save_authorization_code(self.app.client_id, {'code': 'over-quota'}, request)
        self.assertFalse(get_grant_model().objects.filter(application=self.app).exists())
        self.assertIsNone(AgentApplication.objects.get(application=self.app).date_authorized)

    def test_reauthorization_multi_org_and_refresh_share_one_client_slot(self):
        self.fill_client_slots(9)
        result = self.issued()
        self.code()
        self.code()
        response = self.token_request({
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'], 'client_id': self.app.client_id,
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(AgentOAuthBinding.objects.filter(user=self.user).values('application_id').distinct().count(), 10)
        self.assertEqual(self.introspect(json.loads(response.content))['client_id'], self.app.client_id)

    def test_client_limit_is_per_user_even_for_shared_registrations(self):
        self.fill_client_slots(10)
        owner = self.user
        self.user = User.objects.create(username='quota-other-user')
        self.first.add_member(self.user)
        self.code()
        self.assertEqual(AgentOAuthBinding.objects.filter(user=self.user).values('application_id').distinct().count(), 1)
        self.user = owner
        self.assertEqual(self.authorize().status_code, 200)
        self.assertFalse(AgentOAuthBinding.objects.filter(user=owner, application=self.app).exists())

    def test_revoke_frees_slot_without_removing_client_audit_history(self):
        from django.db import transaction
        from rest_framework.test import APIRequestFactory, force_authenticate
        from authentication.api.agent_client_user import UserAgentClientViewSet

        applications = self.fill_client_slots(10)
        history = AgentSession.objects.create(
            user=self.user, application=applications[0], terminal=self.node, resource=self.resource,
            idempotency_key='quota-history', request_hash='0' * 64, date_expires=timezone.now() + timedelta(minutes=5),
        )
        request = APIRequestFactory().post('/revoke/')
        force_authenticate(request, user=self.user)
        with transaction.atomic():
            response = UserAgentClientViewSet.as_view({'post': 'revoke'})(request, pk=str(applications[0].pk))
        self.assertEqual(response.status_code, 204)
        self.code()
        history.refresh_from_db()
        self.assertEqual(history.application_id, applications[0].pk)
        self.assertFalse(AgentApplication.objects.filter(application=applications[0]).exists())
        self.assertEqual(AgentOAuthBinding.objects.filter(user=self.user).values('application_id').distinct().count(), 10)

    def test_disabled_and_expired_clients_still_count_and_cancellation_is_allowed(self):
        applications = self.fill_client_slots(10)
        AgentApplication.objects.filter(application=applications[0]).update(is_active=False)
        get_grant_model().objects.filter(application=applications[1]).update(expires=timezone.now() - timedelta(minutes=1))
        self.assertTrue(self.authorize().context_data['form'].non_field_errors())
        response = self.authorize(allow='')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parse_qs(urlsplit(response['Location']).query)['error'], ['access_denied'])

    def test_client_limit_message_is_localized(self):
        self.fill_client_slots(10)
        for language, expected in (('zh', '最多授权 10'), ('zh-hant', '最多授權 10')):
            with override(language):
                response = self.authorize()
                self.assertIn(expected, str(response.context_data['form'].non_field_errors()))

    def test_non_agent_oauth_authorization_is_not_limited(self):
        self.fill_client_slots(10)
        self.app = get_application_model().objects.create(
            name='Ordinary OAuth client', client_type='public', authorization_grant_type='authorization-code',
            redirect_uris='https://oauth.example/callback',
        )
        self.authorization.update(client_id=self.app.client_id, redirect_uri=self.app.redirect_uris, scope='read')
        self.authorization.pop('resource')
        response = self.authorize()
        self.assertEqual(response.status_code, 302)
        self.assertIn('code', parse_qs(urlsplit(response['Location']).query))
        self.assertFalse(AgentOAuthBinding.objects.filter(application=self.app).exists())

    def test_consent_requires_csrf_protection(self):
        request = self.factory.post('/authorize/', {**self.authorization, 'allow': 'Authorize'})
        request.user = self.user
        response = AgentAwareAuthorizationView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('csrf_failure=1', response['Location'])
        self.assertFalse(get_grant_model().objects.filter(application=self.app).exists())

    @override_settings(SECURITY_CLIENT_MAX_SESSION_TIME=1)
    def test_desktop_login_policy_survives_agent_oauth_integration(self):
        self.app = get_application_model().objects.create(
            name=settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME, client_type='public',
            authorization_grant_type='authorization-code', redirect_uris='jms2://auth/callback',
        )
        self.authorization.update({
            'client_id': self.app.client_id, 'redirect_uri': 'jms2://auth/callback', 'scope': 'read write',
        })
        self.authorization.pop('resource')
        self.assertEqual(self.authorize().status_code, 400)
        self.authorization['client_login_policy_version'] = '1'
        result = self.issued()
        self.assertEqual(result['client_login_policy']['max_session_time'], 1)
        session = ClientLoginSession.objects.get(application=self.app)
        self.assertEqual(result['client_login_expires_at'], session.expires_at.isoformat())
        self.assertFalse(AgentOAuthBinding.objects.filter(application=self.app).exists())
        session.expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=['expires_at'])
        response = self.token_request({
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
            'client_id': self.app.client_id,
        })
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(json.loads(response.content)['client_login_reason'], 'absolute_timeout')
        session.refresh_from_db()
        self.assertEqual(session.revoke_reason, 'absolute_timeout')

    def test_consent_authorizes_available_orgs_without_a_selector(self):
        request = self.factory.get('/authorize/', self.authorization)
        request.user = self.user
        request.session = SessionStore()
        response = AgentAwareAuthorizationView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertNotContains(response, 'name="organization"')
        code = self.code()
        binding = AgentOAuthBinding.objects.get(grant__code=code)
        self.assertEqual(str(binding.org_id), service.ALL_AGENT_ORGANIZATIONS)
        self.assertIsNotNone(AgentApplication.objects.get(application=self.app).date_authorized)

    def test_all_organization_consent_rotation_and_current_membership(self):
        response = self.exchange(self.code(), org_id=str(self.unavailable.pk))
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        principal = self.introspect(result)
        self.assertTrue(principal['all_organizations'])
        self.assertEqual(principal['org_id'], service.ALL_AGENT_ORGANIZATIONS)
        with self.assertRaises(ValidationError):
            self.introspect(result, org_id=str(self.unavailable.pk))
        self.remove_membership()
        context, user = service.context_identity(self.node, principal['context_token'])
        self.assertEqual(list(service.available_agent_organizations(user)), [self.first])
        response = self.token_request({
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'], 'client_id': self.app.client_id,
        })
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        self.assertTrue(self.introspect(result)['all_organizations'])

    def test_personal_revocation_rejects_existing_grants_and_refreshes(self):
        from django.db import transaction
        from rest_framework.test import APIRequestFactory, force_authenticate
        from authentication.api.agent_client_user import UserAgentClientViewSet

        response = self.exchange(self.code())
        result = json.loads(response.content)
        pending_code = self.code()
        request = APIRequestFactory().post('/revoke/')
        force_authenticate(request, user=self.user)
        with transaction.atomic():
            response = UserAgentClientViewSet.as_view({'post': 'revoke'})(request, pk=str(self.app.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AgentApplication.objects.filter(application_id=self.app.pk).exists())
        # With no audit references, revoking the last authorization also
        # removes the registration, so cached clients now fail authentication.
        self.assertEqual(self.exchange(pending_code).status_code, 401)
        self.assertEqual(self.token_request({
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'], 'client_id': self.app.client_id,
        }).status_code, 401)
        with self.assertRaises(PermissionDenied):
            self.introspect(result)
        self.assertFalse(AgentOAuthBinding.objects.filter(user=self.user, application=self.app).exists())

    def test_code_exchange_rotation_and_introspection_keep_all_organizations(self):
        code = self.code()
        response = self.exchange(code, organization=str(self.first.pk), org_id=str(self.first.pk))
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        self.assertEqual(self.introspect(result)['org_id'], service.ALL_AGENT_ORGANIZATIONS)
        refresh = get_refresh_token_model().objects.get(token_checksum=hashlib.sha256(result['refresh_token'].encode()).hexdigest())
        for _ in range(2):
            response = self.token_request({
                'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                'client_id': self.app.client_id, 'organization': str(self.first.pk),
            })
            self.assertEqual(response.status_code, 200, response.content)
            result = json.loads(response.content)
            self.assertEqual(self.introspect(result)['org_id'], service.ALL_AGENT_ORGANIZATIONS)
        self.assertEqual(AgentOAuthBinding.objects.filter(refresh_family=refresh.token_family).count(), 1)
        self.assertFalse(AgentOAuthBinding.objects.filter(grant__isnull=False).exists())

    def test_membership_is_rechecked_on_code_exchange_refresh_and_introspection(self):
        code = self.code()
        result = self.issued()
        self.remove_membership()
        self.first.members.through.objects_raw.filter(user=self.user, org_id=self.first.pk).delete()
        self.assertEqual(self.exchange(code).status_code, 400)
        response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                       'client_id': self.app.client_id})
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(PermissionDenied):
            self.introspect(result)

        response = self.authorize()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['form'].non_field_errors())

    def test_revocation_and_missing_binding_fail_closed(self):
        result = self.issued()
        response = ClientRevokeTokenView.as_view()(self.factory.post('/revoke/', {
            'client_id': self.app.client_id, 'token': result['refresh_token'], 'token_type_hint': 'refresh_token',
        }))
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(PermissionDenied):
            self.introspect(result)
        response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                       'client_id': self.app.client_id})
        self.assertEqual(response.status_code, 400)
        for source in ('dcr', 'manual'):
            with self.subTest(registration_source=source):
                self.app.registration_source = source
                self.app.save(update_fields=['registration_source'])
                result = self.issued()
                code = self.code()
                AgentOAuthBinding.objects.all().delete()
                self.assertEqual(self.exchange(code).status_code, 400)
                with self.assertRaises(PermissionDenied):
                    self.introspect(result)
                response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                               'client_id': self.app.client_id})
                self.assertEqual(response.status_code, 400)

    def test_access_token_binding_survives_refresh_row_deletion(self):
        result = self.issued()
        self.assertEqual(self.introspect(result)['org_id'], service.ALL_AGENT_ORGANIZATIONS)
        get_refresh_token_model().objects.filter(
            token_checksum=hashlib.sha256(result['refresh_token'].encode()).hexdigest(),
        ).delete()
        self.assertEqual(self.introspect(result)['org_id'], service.ALL_AGENT_ORGANIZATIONS)

    def test_refresh_without_rotation_and_grace_retry_preserve_all_organizations(self):
        for rotate in (False, True):
            with self.subTest(rotate=rotate), self.settings(OAUTH2_PROVIDER={
                **settings.OAUTH2_PROVIDER, 'ROTATE_REFRESH_TOKEN': rotate, 'REFRESH_TOKEN_GRACE_PERIOD_SECONDS': 60,
            }):
                original = self.issued()
                body = {'grant_type': 'refresh_token', 'refresh_token': original['refresh_token'],
                        'client_id': self.app.client_id, 'organization': str(self.first.pk)}
                for _ in range(2):
                    response = self.token_request(body)
                    self.assertEqual(response.status_code, 200, response.content)
                    self.assertEqual(self.introspect(json.loads(response.content))['org_id'], service.ALL_AGENT_ORGANIZATIONS)

    def test_registration_metadata_follows_current_configuration(self):
        view = AgentAuthorizationServerView.as_view()
        for enabled in (False, True, False):
            with self.subTest(enabled=enabled), self.settings(MCP_ENABLED=True, MCP_DCR_ENABLED=enabled, MCP_PUBLIC_URL=self.resource):
                response = view(self.factory.get('/.well-known/oauth-authorization-server'))
                self.assertEqual(response.status_code, 200)
                self.assertEqual('registration_endpoint' in json.loads(response.content), enabled)
                self.assertEqual(response['Cache-Control'], 'no-store')

    def test_binding_survives_access_token_expiry_and_deletion(self):
        result = self.issued()
        refresh = get_refresh_token_model().objects.get(token_checksum=hashlib.sha256(result['refresh_token'].encode()).hexdigest())
        get_access_token_model().objects.filter(pk=refresh.access_token_id).update(expires=timezone.now() - timedelta(seconds=1))
        response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                       'client_id': self.app.client_id})
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        self.assertEqual(self.introspect(result)['org_id'], service.ALL_AGENT_ORGANIZATIONS)
        get_access_token_model().objects.filter(token_checksum=hashlib.sha256(result['access_token'].encode()).hexdigest()).delete()
        self.assertEqual(str(AgentOAuthBinding.objects.get(refresh_family=refresh.token_family).org_id), service.ALL_AGENT_ORGANIZATIONS)
        # The provider rejects orphan refresh tokens; the authorization's org still survives.
        response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                       'client_id': self.app.client_id})
        self.assertEqual(response.status_code, 400)
