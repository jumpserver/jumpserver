"""Browser consent and the organization boundary across OAuth token rotation."""
import base64
import hashlib
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import get_application_model, get_access_token_model, get_grant_model, get_refresh_token_model
from rest_framework.exceptions import PermissionDenied

from authentication.backends.oauth2_provider.agent import AgentAwareAuthorizationView, AgentAuthorizationServerView
from authentication.backends.oauth2_provider.client_views import ClientTokenView, ClientRevokeTokenView
from authentication.models.client_login_session import ClientLoginSession
from orgs.models import Organization
from orgs.utils import tmp_to_org
from terminal import agent_service as service
from terminal.models import AgentApplication, AgentOAuthBinding, Terminal
from users.models import User


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
        request._dont_enforce_csrf_checks = True
        return AgentAwareAuthorizationView.as_view()(request)

    def code(self, org=None, *, all_organizations=False):
        response = self.authorize()
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response['Location']).query)
        self.assertEqual(query['state'], ['org-state'])
        code = query['code'][0]
        if not all_organizations:
            # Persisted grants from before multi-organization consent must
            # retain their original scope through exchange and rotation.
            AgentOAuthBinding.objects.filter(grant__code=code).update(org_id=(org or self.second).pk)
        return code

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

    def introspect(self, result, **extra):
        return service.introspect(self.node, {
            'access_token': result['access_token'], 'resource': self.resource, **extra,
        })

    def remove_membership(self):
        self.second.members.through.objects_raw.filter(user=self.user, org_id=self.second.pk).delete()
        self.assertFalse(self.user.orgs.filter(pk=self.second.pk).exists())

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
        request.session = {}
        response = AgentAwareAuthorizationView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertNotContains(response, 'name="organization"')
        code = self.code(all_organizations=True)
        binding = AgentOAuthBinding.objects.get(grant__code=code)
        self.assertEqual(str(binding.org_id), service.ALL_AGENT_ORGANIZATIONS)
        self.assertIsNotNone(AgentApplication.objects.get(application=self.app).date_authorized)

    def test_all_organization_consent_rotation_and_current_membership(self):
        response = self.exchange(self.code(all_organizations=True), org_id=str(self.unavailable.pk))
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        principal = self.introspect(result)
        self.assertTrue(principal['all_organizations'])
        self.assertEqual(principal['org_id'], service.ALL_AGENT_ORGANIZATIONS)
        with self.assertRaises(PermissionDenied):
            self.introspect(result, org_id=str(self.unavailable.pk))
        self.remove_membership()
        context, user = service.context_identity(self.node, principal['context_token'])
        self.assertEqual(list(service.authorized_agent_organizations(user, context['org_id'])), [self.first])
        response = self.token_request({
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'], 'client_id': self.app.client_id,
        })
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        self.assertTrue(self.introspect(result)['all_organizations'])
        self.first.members.through.objects_raw.filter(user=self.user, org_id=self.first.pk).delete()
        with self.assertRaises(PermissionDenied):
            self.introspect(result)
        self.assertEqual(self.token_request({
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'], 'client_id': self.app.client_id,
        }).status_code, 400)
        response = self.authorize()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['form'].non_field_errors())

    def test_personal_revocation_rejects_existing_grants_and_refreshes(self):
        from django.db import transaction
        from rest_framework.test import APIRequestFactory, force_authenticate
        from authentication.api.agent_client_user import UserAgentClientViewSet

        response = self.exchange(self.code(all_organizations=True))
        result = json.loads(response.content)
        pending_code = self.code(all_organizations=True)
        request = APIRequestFactory().post('/revoke/')
        force_authenticate(request, user=self.user)
        with transaction.atomic():
            response = UserAgentClientViewSet.as_view({'post': 'revoke'})(request, pk=str(self.app.pk))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.exchange(pending_code).status_code, 400)
        self.assertEqual(self.token_request({
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'], 'client_id': self.app.client_id,
        }).status_code, 400)
        with self.assertRaises(PermissionDenied):
            self.introspect(result)
        self.assertFalse(AgentOAuthBinding.objects.filter(user=self.user, application=self.app).exists())

    def test_code_exchange_rotation_and_introspection_keep_selected_org(self):
        code = self.code()
        response = self.exchange(code, organization=str(self.first.pk), org_id=str(self.first.pk))
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        self.assertEqual(self.introspect(result)['org_id'], str(self.second.pk))
        with self.assertRaises(PermissionDenied):
            self.introspect(result, org_id=str(self.first.pk))
        refresh = get_refresh_token_model().objects.get(token_checksum=hashlib.sha256(result['refresh_token'].encode()).hexdigest())
        for _ in range(2):
            response = self.token_request({
                'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                'client_id': self.app.client_id, 'organization': str(self.first.pk),
            })
            self.assertEqual(response.status_code, 200, response.content)
            result = json.loads(response.content)
            self.assertEqual(self.introspect(result)['org_id'], str(self.second.pk))
        self.assertEqual(AgentOAuthBinding.objects.filter(refresh_family=refresh.token_family).count(), 1)
        self.assertFalse(AgentOAuthBinding.objects.filter(grant__isnull=False).exists())

    def test_membership_is_rechecked_on_code_exchange_refresh_and_introspection(self):
        code = self.code()
        result = self.issued()
        self.remove_membership()
        self.assertEqual(self.exchange(code).status_code, 400)
        response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                       'client_id': self.app.client_id})
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(PermissionDenied):
            self.introspect(result)

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
                    self.introspect(result, org_id=str(self.first.pk))
                response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                               'client_id': self.app.client_id})
                self.assertEqual(response.status_code, 400)

    def test_access_token_binding_survives_refresh_row_deletion(self):
        result = self.issued()
        self.assertEqual(self.introspect(result)['org_id'], str(self.second.pk))
        with self.assertRaises(PermissionDenied):
            self.introspect(result, org_id=str(self.first.pk))
        get_refresh_token_model().objects.filter(
            token_checksum=hashlib.sha256(result['refresh_token'].encode()).hexdigest(),
        ).delete()
        self.assertEqual(self.introspect(result)['org_id'], str(self.second.pk))
        with self.assertRaises(PermissionDenied):
            self.introspect(result, org_id=str(self.first.pk))

    def test_refresh_without_rotation_and_grace_retry_preserve_org(self):
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
                    self.assertEqual(self.introspect(json.loads(response.content))['org_id'], str(self.second.pk))

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
        self.assertEqual(self.introspect(result)['org_id'], str(self.second.pk))
        get_access_token_model().objects.filter(token_checksum=hashlib.sha256(result['access_token'].encode()).hexdigest()).delete()
        self.assertEqual(str(AgentOAuthBinding.objects.get(refresh_family=refresh.token_family).org_id), str(self.second.pk))
        # The provider rejects orphan refresh tokens; the authorization's org still survives.
        response = self.token_request({'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
                                       'client_id': self.app.client_id})
        self.assertEqual(response.status_code, 400)
