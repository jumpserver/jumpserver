"""Security and recovery boundaries; uses no network assets or executor workers."""
import base64
import hashlib
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, RequestFactory, override_settings
from django.http import Http404, QueryDict
from django.utils import timezone
from oauthlib.common import Request as OAuthRequest
from oauthlib.oauth2 import InvalidRequestError
from oauth2_provider.models import get_application_model, get_access_token_model, get_refresh_token_model
from rest_framework.exceptions import PermissionDenied, ValidationError

from authentication.backends.oauth2_provider.agent import AgentOAuth2Validator
from orgs.models import Organization
from orgs.utils import tmp_to_org
from terminal import agent_service as service
from terminal.models import AgentApplication, AgentOAuthBinding, AgentSession, AgentAction, AgentEvent, Terminal
from users.models import User


class AgentBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='agent-boundary-user', name='Agent boundary user')
        cls.org, _ = Organization.objects.get_or_create(id=Organization.DEFAULT_ID, defaults={'name': 'Default'})
        cls.org.add_member(cls.user)
        cls.node = Terminal.objects.create(name='agent-boundary-node', type='koko')
        cls.other_node = Terminal.objects.create(name='agent-boundary-other', type='koko')
        Application = get_application_model()
        cls.app = Application.objects.create(
            name='Agent boundary client', client_id='agent-boundary', client_type='public',
            authorization_grant_type='authorization-code', redirect_uris='http://127.0.0.1/callback',
            registration_source='dcr',
        )
        cls.resource = 'https://jumpserver.example/koko/mcp'
        AgentApplication.objects.create(application=cls.app, resource=cls.resource)

    def setUp(self):
        self.org_context = self.enterContext(tmp_to_org(self.org))
        self.token = get_access_token_model().objects.create(
            user=self.user, application=self.app, token=uuid.uuid4().hex, scope=service.SCOPE,
            expires=timezone.now() + timedelta(minutes=5), resource=[self.resource],
        )
        self.refresh = get_refresh_token_model().objects.create(
            user=self.user, application=self.app, access_token=self.token,
            token=uuid.uuid4().hex, token_family=uuid.uuid4(), resource=[self.resource],
        )
        for subject in ({'access_token': self.token}, {'refresh_family': self.refresh.token_family}):
            AgentOAuthBinding.objects.create(user=self.user, application=self.app, org_id=self.org.pk, **subject)
        self.session = AgentSession.objects.create(
            user=self.user, application=self.app, terminal=self.node, oauth_token=self.token,
            oauth_family=self.refresh.token_family, resource=self.resource, idempotency_key='connection',
            request_hash='0' * 64, date_expires=timezone.now() + timedelta(hours=1),
            requested={'protocol': 'ssh', 'asset_id': str(uuid.uuid4()), 'account': 'root'},
        )
        self.action = AgentAction.objects.create(
            session=self.session, user=self.user, application=self.app, kind='file_read',
            idempotency_key='read', request={'path': '/file'}, request_hash='1' * 64, status='dispatching',
        )

    def test_user_deletion_preserves_audit_and_revokes_execution(self):
        from terminal.api.agent import AgentAuditAPI
        display = str(self.user)
        User.objects.filter(pk=self.user.pk).delete()
        self.session.refresh_from_db()
        self.action.refresh_from_db()
        for item in (self.session, self.action):
            self.assertIsNone(item.user_id)
            self.assertEqual(AgentAuditAPI.serialize(item)['user_display'], display)
        self.assertIsNone(AgentAuditAPI.serialize(self.session)['user_id'])
        with self.assertRaises(PermissionDenied):
            service.check_session_authority(self.session, connection=False)
        # Component-bound receipts still deliver evidence after the owner is gone.
        receipt = service.owned_session(self.node, self.session.id, service.session_capability(self.session), check=False)
        service.append_event(self.action, {'session_token': service.session_capability(receipt),
            'event_id': str(uuid.uuid4()), 'sequence': 1, 'state': 'failed', 'payload': {'error': 'owner deleted'}})
        self.assertEqual(self.action.events.count(), 1)

    def test_expired_agent_history_preserves_identity_after_rename_and_delete(self):
        display = str(self.user)
        User.objects.filter(pk=self.user.pk).update(name='Renamed')
        self.session.refresh_from_db()
        self.action.refresh_from_db()
        self.session.date_closed = timezone.now()
        self.session.date_expires = timezone.now() - timedelta(days=1)
        self.session.save()
        self.action.save()
        self.user.delete()
        for item in (self.session, self.action):
            item.refresh_from_db()
            self.assertIsNone(item.user_id)
            self.assertEqual(item.user_display, display)

    def test_introspection_binds_resource_org_and_execution_node(self):
        result = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        context, user = service.context_identity(self.node, result['context_token'])
        self.assertEqual(context['org_id'], str(self.org.id))
        self.assertEqual(user.id, self.user.id)
        with self.assertRaises(PermissionDenied):
            service.context_identity(self.other_node, result['context_token'])
        with self.assertRaises(PermissionDenied):
            service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource + '/other'})
        with self.assertRaises(Http404):
            service.owned_session(self.other_node, self.session.id, service.session_capability(self.session), check=False)

    def test_rotation_preserves_session_but_revocation_blocks_execution(self):
        self.refresh.revoked = timezone.now()
        self.refresh.save(update_fields=['revoked'])
        replacement = get_refresh_token_model().objects.create(
            user=self.user, application=self.app, token=uuid.uuid4().hex,
            token_family=self.refresh.token_family, resource=[self.resource],
        )
        self.token.delete()
        self.session.refresh_from_db()
        service.check_session_authority(self.session, connection=False)
        replacement.revoke()
        with self.assertRaises(PermissionDenied):
            service.check_session_authority(self.session, connection=False)
        # The signed receipt capability still permits delayed, bounded evidence.
        self.session.date_closed = timezone.now()
        self.session.save(update_fields=['date_closed'])
        receipt = service.owned_session(self.node, self.session.id, service.session_capability(self.session), check=False)
        event = {'session_token': service.session_capability(receipt), 'event_id': str(uuid.uuid4()),
                 'sequence': 1, 'state': 'failed', 'payload': {'error': 'connection lost'}}
        service.append_event(self.action, event)
        service.append_event(self.action, event)
        self.assertEqual(AgentEvent.objects.filter(action=self.action).count(), 1)
        with self.assertRaises(service.Conflict):
            service.append_event(self.action, {**event, 'payload': {'error': 'different'}})

    def test_evidence_sequence_terminal_state_and_stop_confirmation(self):
        event = {'session_token': 'receipt', 'event_id': str(uuid.uuid4()), 'sequence': 2,
                 'state': 'running', 'payload': {}}
        with self.assertRaises(service.Conflict):
            service.append_event(self.action, event)
        event['sequence'] = 1
        service.append_event(self.action, event)
        with self.assertRaises(ValidationError):
            service.append_event(self.action, {**event, 'event_id': str(uuid.uuid4()), 'sequence': 2, 'state': 'cancelled'})
        service.append_event(self.action, {**event, 'event_id': str(uuid.uuid4()), 'sequence': 2,
                                          'state': 'unknown', 'payload': {'stop_confirmed': False}})
        service.append_event(self.action, {**event, 'event_id': str(uuid.uuid4()), 'sequence': 3})
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, 'unknown')
        self.assertEqual(self.action.last_sequence, 3)

    def test_unclaimed_unknown_receipt_converges_and_cannot_be_replayed(self):
        from terminal.api.agent import AgentComponentAPI
        self.action.status = 'queued'
        self.action.save(update_fields=['status'])
        event = {'session_token': service.session_capability(self.session),
                 'event_id': str(uuid.uuid4()), 'sequence': 1, 'state': 'unknown',
                 'payload': {'error': 'executor restarted before claim acknowledgement'}}
        api = AgentComponentAPI(operation='events')
        with self.assertRaises(service.Conflict):
            api.action_operation(self.node, self.action.id, {**event, 'state': 'running'})
        first = api.action_operation(self.node, self.action.id, event)
        self.assertEqual(first['status'], 'unknown')
        self.assertEqual(api.action_operation(self.node, self.action.id, event)['status'], 'unknown')
        self.action.refresh_from_db()
        self.assertEqual(self.action.events.count(), 1)
        self.assertIsNotNone(self.action.date_finished)
        self.assertIsNone(self.action.date_started)
        api.operation = 'claim'
        self.assertFalse(api.action_operation(self.node, self.action.id, {
            'session_token': event['session_token'],
        })['claimed'])

    def test_registered_client_requires_pkce_resource_and_has_no_core_api_access(self):
        validator = AgentOAuth2Validator()
        request = OAuthRequest('https://jumpserver.example/authorize')
        request.client, request.scopes = self.app, [service.SCOPE]
        request.resource, request.code_challenge = [self.resource], 'x' * 43
        request.code_challenge_method = 'plain'
        with self.assertRaises(InvalidRequestError):
            validator.save_authorization_code(self.app.client_id, {'code': 'denied'}, request)
        self.assertFalse(validator.validate_bearer_token(self.token.token, [], request))
        self.assertTrue(self.app.redirect_uri_allowed('http://127.0.0.1:48751/callback'))
        self.assertFalse(self.app.redirect_uri_allowed('http://127.0.0.1:48751/other'))
        self.assertFalse(validator.validate_scopes(self.app.client_id, ['read'], self.app, request))

    def test_authorization_code_exchange_requires_verifier_and_preserves_resource(self):
        for secure, scheme in ((True, 'https'), (False, 'http')):
            with self.subTest(secure=secure):
                self.resource = f'{scheme}://jumpserver.example/koko/mcp'
                AgentApplication.objects.filter(application=self.app).update(resource=self.resource)
                self.check_authorization_code_exchange(secure=secure)

    def test_browser_authorization_returns_registered_loopback_code(self):
        from urllib.parse import parse_qs, urlsplit
        from oauth2_provider.models import get_grant_model
        from authentication.backends.oauth2_provider.agent import AgentAwareAuthorizationView

        self.app.redirect_uris = 'http://127.0.0.1/callback/client?channel=pc http://[::1]/callback/client?channel=pc'
        self.app.save(update_fields=['redirect_uris'])
        factory, view = RequestFactory(), AgentAwareAuthorizationView.as_view()
        for secure, host in ((False, '127.0.0.1'), (True, '[::1]')):
            with self.subTest(secure=secure, host=host):
                callback = f'http://{host}:48751/callback/client?channel=pc'
                body = {'client_id': self.app.client_id, 'redirect_uri': callback, 'response_type': 'code',
                        'scope': service.SCOPE, 'resource': self.resource, 'state': 'client-state',
                        'code_challenge': 'x' * 43, 'code_challenge_method': 'S256'}
                request = factory.get('/authorize/', body, secure=secure)
                request.user = self.user
                response = view(request)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context_data['form'].initial['redirect_uri'], callback)
                request = factory.post('/authorize/', {**body, 'allow': 'Authorize'}, secure=secure)
                request.user = self.user
                request._dont_enforce_csrf_checks = True
                response = view(request)
                self.assertEqual(response.status_code, 302)
                query = parse_qs(urlsplit(response['Location']).query)
                self.assertEqual(query['state'], ['client-state'])
                self.assertEqual(query['channel'], ['pc'])
                grant = get_grant_model().objects.get(code=query['code'][0])
                self.assertEqual(grant.redirect_uri, callback)
                self.assertEqual(grant.resource, [self.resource])

    def test_loopback_redirect_exception_is_limited_to_active_registered_agent(self):
        from django.core.exceptions import DisallowedRedirect
        from authentication.backends.oauth2_provider.agent import AgentAwareAuthorizationView

        callback = 'http://127.0.0.1:48751/callback'
        view = AgentAwareAuthorizationView()
        view.oauth2_data = {}
        for requested, target in (
            (callback + '/other', callback + '/other'),
            ('http://remote.example/callback', 'http://remote.example/callback'),
            (callback + '?unregistered=1', callback + '?unregistered=1'),
            (callback, callback.replace(':48751', ':48752')),
            (callback, callback + '/other'),
            (callback, callback + '#fragment'),
        ):
            with self.subTest(requested=requested, target=target):
                view.request = RequestFactory().post('/authorize/', {'redirect_uri': requested})
                with self.assertRaises(DisallowedRedirect):
                    view.redirect(target, self.app)
        view.request = RequestFactory().post('/authorize/', {'redirect_uri': callback})
        AgentApplication.objects.filter(application=self.app).update(is_active=False)
        with self.assertRaises(DisallowedRedirect):
            view.redirect(callback + '?error=access_denied', self.app)
        AgentApplication.objects.filter(application=self.app).delete()
        with self.assertRaises(DisallowedRedirect):
            view.redirect(callback + '?code=not-issued', self.app)

    def test_disabled_client_rejects_agent_access_without_touching_other_apps(self):
        other = get_application_model().objects.create(
            name='Other OAuth application', client_id='other-oauth', client_type='public',
            authorization_grant_type='authorization-code',
        )
        AgentApplication.objects.filter(application=self.app).update(is_active=False)
        self.assertTrue(get_application_model().objects.filter(pk=other.pk).exists())
        with self.assertRaises(PermissionDenied):
            service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        with self.assertRaises(PermissionDenied):
            service.check_session_authority(self.session, connection=False)

    def check_authorization_code_exchange(self, *, secure):
        import json
        from oauth2_provider.models import get_grant_model
        from oauth2_provider.views import TokenView, RevokeTokenView
        verifier = 'a' * 64
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        grant = get_grant_model().objects.create(
            user=self.user, application=self.app, code=uuid.uuid4().hex,
            expires=timezone.now() + timedelta(minutes=1), redirect_uri='http://127.0.0.1:45678/callback',
            scope=service.SCOPE, code_challenge=challenge, code_challenge_method='S256', resource=[self.resource],
        )
        AgentOAuthBinding.objects.create(user=self.user, application=self.app, org_id=self.org.pk, grant=grant)
        body = {'grant_type': 'authorization_code', 'code': grant.code, 'client_id': self.app.client_id,
                'redirect_uri': grant.redirect_uri, 'resource': self.resource, 'code_verifier': 'b' * 64}
        factory = RequestFactory()
        view = TokenView.as_view()
        bad = view(factory.post('/token/', body, secure=secure))
        self.assertEqual(bad.status_code, 400)
        body['code_verifier'] = verifier
        response = view(factory.post('/token/', body, secure=secure))
        self.assertEqual(response.status_code, 200, response.content)
        result = json.loads(response.content)
        issued = get_access_token_model().objects.get(token_checksum=hashlib.sha256(result['access_token'].encode()).hexdigest())
        self.assertEqual(issued.resource, [self.resource])
        refresh = get_refresh_token_model().objects.get(access_token=issued)
        rotated_response = view(factory.post('/token/', {
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'],
            'client_id': self.app.client_id, 'resource': self.resource,
        }, secure=secure))
        self.assertEqual(rotated_response.status_code, 200, rotated_response.content)
        rotated = json.loads(rotated_response.content)
        self.assertTrue(service.authority_exists(self.user.id, self.app.id, issued.id, refresh.token_family))
        response = RevokeTokenView.as_view()(factory.post('/revoke/', {
            'client_id': self.app.client_id, 'token': rotated['refresh_token'], 'token_type_hint': 'refresh_token',
        }, secure=secure))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(service.authority_exists(self.user.id, self.app.id, issued.id, refresh.token_family))

    def test_all_organizations_discovery_pagination_execution_and_membership_revocation(self):
        from accounts.models import Account
        from assets.models import Asset, Platform
        from perms.models import AssetPermission
        from terminal.api.agent import AgentComponentAPI

        second = Organization.objects.create(name='Agent multi second')
        second.add_member(self.user)
        other = Organization.objects.create(name='Agent multi unavailable')
        platform = Platform.objects.create(name='Agent multi Linux', category='host', type='linux')
        platform.protocols.create(name='ssh', port=22)
        assets = []
        accounts = []
        for org in (self.org, second, other):
            with tmp_to_org(org):
                asset = Asset.objects.create(name='Same asset name', address='192.0.2.2', platform=platform)
                asset.protocols.create(name='ssh', port=22)
                account = Account.objects.create(name='root', username='root', asset=asset, secret='test-only-secret')
                permission = AssetPermission.objects.create(name='Agent multi access', accounts=['root'], protocols=['ssh'])
                permission.users.add(self.user)
                permission.assets.add(asset)
                assets.append(asset)
                accounts.append(account)
        with tmp_to_org(second):
            denied = Asset.objects.create(name='Not granted', address='192.0.2.3', platform=platform)
        legacy = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        AgentOAuthBinding.objects.filter(user=self.user, application=self.app).update(org_id=service.ALL_AGENT_ORGANIZATIONS)
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        query = {'context_token': principal['context_token'], 'limit': 1}
        page = AgentComponentAPI.assets(self.node, query)
        rows = list(page['results'])
        while page['next_offset'] is not None:
            page = AgentComponentAPI.assets(self.node, {**query, 'offset': page['next_offset']})
            rows.extend(page['results'])
        self.assertEqual({row['id'] for row in rows}, {str(asset.pk) for asset in assets[:2]})
        self.assertEqual(len(rows), 2)
        self.assertEqual({row['org_id'] for row in rows}, {str(self.org.pk), str(second.pk)})
        self.assertTrue(all(row['org_name'] for row in rows))
        for asset in (assets[2], denied):
            self.assertEqual(AgentComponentAPI.assets(self.node, {**query, 'asset_id': str(asset.pk)})['results'], [])
        connections = []
        for index, asset in enumerate(assets[:2]):
            body = {'context_token': principal['context_token'], 'asset_id': str(asset.pk),
                    'account': str(accounts[index].pk), 'protocol': 'ssh', 'idempotency_key': 'multi-connect'}
            connection = service.create_session(self.node, body)
            connections.append(connection)
            self.assertEqual(service.create_session(self.node, body)['id'], connection['id'])
            with tmp_to_org(asset.org_id):
                session = AgentSession.objects.get(pk=connection['id'])
                self.assertEqual(session.org_id, str(asset.org_id))
                self.assertEqual(session.actions.get(kind='connect_asset').org_id, str(asset.org_id))
        with self.assertRaises(Http404):
            service.create_session(self.node, {**body, 'context_token': legacy['context_token'], 'idempotency_key': 'legacy-denied'})
        reader = AgentComponentAPI(operation='get')
        handoff = service.create_action(self.node, {
            'context_token': principal['context_token'], 'session_id': connections[1]['id'],
            'kind': 'open_terminal', 'idempotency_key': 'multi-handoff', 'request': {},
        })
        with tmp_to_org(second):
            self.assertEqual(AgentAction.objects.get(pk=handoff['id']).org_id, str(second.pk))
        self.assertEqual(reader.action_operation(self.node, connections[1]['action_id'], {
            'context_token': principal['context_token'],
        })['id'], connections[1]['action_id'])
        second.members.through.objects_raw.filter(user=self.user, org_id=second.pk).delete()
        self.assertEqual(AgentComponentAPI.assets(self.node, {**query, 'asset_id': str(assets[1].pk)})['results'], [])
        with self.assertRaises(PermissionDenied):
            reader.action_operation(self.node, connections[1]['action_id'], {'context_token': principal['context_token']})
        with self.assertRaises(Http404):
            service.create_session(self.node, {**body, 'idempotency_key': 'removed-org'})

    def test_real_connection_authorization_idempotency_claim_and_permission_revocation(self):
        from accounts.models import Account
        from assets.models import Asset, Platform
        from perms.models import AssetPermission
        from terminal.api.agent import AgentComponentAPI
        from terminal.models import Session
        platform = Platform.objects.create(name='Agent test Linux', category='host', type='linux')
        platform.protocols.create(name='ssh', port=22)
        asset = Asset.objects.create(name='Agent test asset', address='192.0.2.1', platform=platform)
        asset.protocols.create(name='ssh', port=22)
        account = Account.objects.create(name='root', username='root', asset=asset, secret='test-only-secret')
        permission = AssetPermission.objects.create(name='Agent test access', accounts=['root'], protocols=['ssh'])
        permission.users.add(self.user)
        permission.assets.add(asset)
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        body = {'context_token': principal['context_token'], 'asset_id': str(asset.id), 'account': str(account.id),
                'protocol': 'ssh', 'idempotency_key': 'real-connect', 'remote_addr': '127.0.0.1'}
        first = service.create_session(self.node, body)
        self.assertEqual(service.create_session(self.node, body)['id'], first['id'])
        with self.assertRaises(service.Conflict):
            service.create_session(self.node, {**body, 'account': '@INPUT'})
        cancelled = service.create_session(self.node, {**body, 'idempotency_key': 'cancelled-connect'})
        canceller = AgentComponentAPI(operation='cancel')
        canceller.action_operation(self.node, cancelled['action_id'], {'context_token': principal['context_token']})
        api = AgentComponentAPI(operation='credentials')
        with self.assertRaises(service.Conflict):
            api.session_operation(self.node, cancelled['id'], {'session_token': cancelled['session_token']})
        cancelled_session = AgentSession.objects.get(pk=cancelled['id'])
        self.assertIsNone(cancelled_session.connection_token.date_last_used)
        credentials = api.session_operation(self.node, first['id'], {'session_token': first['session_token']})
        self.assertEqual(credentials['account']['username'], 'root')
        with self.assertRaises(service.Conflict):
            api.session_operation(self.node, first['id'], {'session_token': first['session_token']})
        session = AgentSession.objects.get(pk=first['id'])
        terminal = Session.objects.create(
            terminal=self.node, user_id=str(self.user.id), user=str(self.user), asset_id=str(asset.id),
            asset=str(asset), account_id=str(account.id), account='root(root)', protocol='ssh', login_from='WT',
        )
        api.operation = 'bind'
        api.session_operation(self.node, first['id'], {
            'session_token': first['session_token'], 'terminal_session_id': str(terminal.id),
        })
        terminal.refresh_from_db()
        self.assertEqual(terminal.login_from, 'AG')
        connect = session.actions.get(kind='connect_asset')
        service.append_event(connect, {'session_token': first['session_token'], 'event_id': str(uuid.uuid4()),
                                       'sequence': 1, 'state': 'succeeded', 'payload': {}})
        action_body = {'context_token': principal['context_token'], 'session_id': first['id'],
                       'kind': 'execute_command', 'idempotency_key': 'command', 'request': {'command': 'pwd'}}
        with self.assertRaisesMessage(ValidationError, 'Unsupported action kind'):
            service.create_action(self.node, {**action_body, 'kind': 'terminal_input',
                'request': {'terminal_id': str(terminal.id), 'input': 'pwd\n'}})
        for field, value in (('offset', 1), ('encoding', 'base64')):
            with self.subTest(field=field), self.assertRaisesMessage(ValidationError, 'Unknown or invalid request fields'):
                service.create_action(self.node, {**action_body, 'kind': 'file_read',
                    'request': {'path': '/file', field: value}})
        action = service.create_action(self.node, action_body)
        self.assertEqual(service.create_action(self.node, action_body)['id'], action['id'])
        api.operation = 'claim'
        claim = api.action_operation(self.node, action['id'], {'session_token': first['session_token']})
        self.assertTrue(claim['claimed'])
        self.assertFalse(api.action_operation(self.node, action['id'], {'session_token': first['session_token']})['claimed'])
        from acls.models import CommandFilterACL, CommandGroup
        reviewer = User.objects.create(username='agent-reviewer', name='Agent reviewer')
        self.org.add_member(reviewer)
        rule = CommandFilterACL.objects.create(name='Agent review', action='review', priority=1,
            users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        group = CommandGroup.objects.create(name='Agent review group', content='review-required')
        rule.command_groups.add(group)
        rule.reviewers.add(reviewer)
        review_body = {**action_body, 'idempotency_key': 'reviewed-command',
                       'request': {'command': 'review-required', 'cwd': '/tmp', 'env': {'MODE': 'read'}}}
        reviewed = service.create_action(self.node, review_body)
        self.assertFalse(api.action_operation(self.node, reviewed['id'], {'session_token': first['session_token']})['claimed'])
        frozen = AgentAction.objects.get(pk=reviewed['id'])
        self.assertEqual(frozen.status, 'awaiting_approval')
        self.assertEqual(frozen.ticket.meta['agent_action']['request_hash'], frozen.request_hash)
        frozen.ticket.approve(reviewer)
        self.assertTrue(api.action_operation(self.node, reviewed['id'], {'session_token': first['session_token']})['claimed'])
        other_body = {**review_body, 'idempotency_key': 'other-reviewed-command',
                      'request': {**review_body['request'], 'cwd': '/var'}}
        other = service.create_action(self.node, other_body)
        api.operation = 'authorize'
        api.action_operation(self.node, other['id'], {'session_token': first['session_token']})
        other_action = AgentAction.objects.get(pk=other['id'])
        self.assertNotEqual(other_action.ticket_id, frozen.ticket_id)
        other_action.ticket = frozen.ticket
        other_action.save(update_fields=['ticket'])
        api.operation = 'claim'
        rejected = api.action_operation(self.node, other['id'], {'session_token': first['session_token']})
        self.assertFalse(rejected['claimed'])
        self.assertEqual(rejected['status'], 'rejected')
        from acls.models import LoginAssetACL
        login_rule = LoginAssetACL.objects.create(name='Agent login review', action='accept', priority=1,
            review_enabled=True, users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        login_rule.reviewers.add(reviewer)
        login_body = {**body, 'idempotency_key': 'reviewed-connect'}
        pending = service.create_session(self.node, login_body)
        self.assertEqual(pending['status'], 'awaiting_approval')
        service.create_session(self.node, login_body)
        pending_session = AgentSession.objects.get(pk=pending['id'])
        pending_session.connection_token.from_ticket.approve(reviewer)
        self.assertEqual(service.create_session(self.node, login_body)['status'], 'ready')
        permission.is_active = False
        permission.save(update_fields=['is_active'])
        fresh = AgentSession.objects.select_related('connection_token').get(pk=first['id'])
        with self.assertRaises(PermissionDenied):
            service.check_session_authority(fresh)
        from authentication.tasks import clean_expire_token
        with override_settings(SECURITY_EXPIRED_TOKEN_RECORD_KEEP_DAYS=0):
            clean_expire_token()
            session.refresh_from_db()
            self.assertIsNotNone(session.connection_token_id)
            session.date_expires = timezone.now() - timedelta(seconds=1)
            session.save(update_fields=['date_expires'])
            clean_expire_token()
        session.refresh_from_db()
        self.assertIsNone(session.connection_token_id)
        received = AgentAction.objects.get(pk=action['id'])
        service.append_event(received, {'session_token': 'receipt', 'event_id': str(uuid.uuid4()),
            'sequence': 1, 'state': 'succeeded', 'payload': {'exit_code': 0}})
        self.assertEqual(received.status, 'succeeded')

    def test_close_cancels_unclaimed_handoff_and_preserves_late_evidence(self):
        from terminal.api.agent import AgentComponentAPI
        from terminal.models import Session
        terminal = Session.objects.create(terminal=self.node, user='test', user_id=str(self.user.id),
            asset='test', asset_id=str(uuid.uuid4()), account='test', account_id='test', protocol='ssh')
        self.session.terminal_session = terminal
        self.session.save(update_fields=['terminal_session'])
        self.action.kind, self.action.status = 'open_terminal', 'awaiting_input'
        self.action.save(update_fields=['kind', 'status'])
        api = AgentComponentAPI(operation='close')
        with override_settings(XPACK_LICENSE_IS_VALID=True, CHANGE_SECRET_AFTER_SESSION_END=True), patch(
            'terminal.serializers.SessionSerializer.enqueue_change_secret_task',
        ) as change_secret:
            for _ in range(2):
                api.session_operation(self.node, self.session.id, {'session_token': service.session_capability(self.session)})
            change_secret.assert_called_once()
        self.action.refresh_from_db()
        terminal.refresh_from_db()
        self.assertEqual(self.action.status, 'cancelled')
        self.assertTrue(terminal.is_finished)
        for sequence, state in enumerate(('awaiting_input', 'unknown', 'failed'), start=1):
            service.append_event(self.action, {'session_token': 'receipt', 'event_id': str(uuid.uuid4()),
                'sequence': sequence, 'state': state, 'payload': {'error': 'late observation'}})
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, 'cancelled')
        self.assertEqual(self.action.result, {})
        self.assertEqual(self.action.events.count(), 3)

    def handoff_asset(self):
        from accounts.models import Account
        from assets.models import Asset, Platform
        from perms.models import AssetPermission
        platform = Platform.objects.create(name='Agent handoff Linux', category='host', type='linux')
        platform.protocols.create(name='ssh', port=22)
        asset = Asset.objects.create(name='Agent handoff asset', address='192.0.2.2', platform=platform)
        asset.protocols.create(name='ssh', port=22)
        account = Account.objects.create(name='root', username='root', asset=asset, secret='test-only-secret')
        permission = AssetPermission.objects.create(name='Agent handoff access', accounts=['root'], protocols=['ssh'])
        permission.users.add(self.user)
        permission.assets.add(asset)
        self.session.requested = {'asset_id': str(asset.id), 'account': str(account.id), 'protocol': 'ssh'}
        self.session.save(update_fields=['requested'])
        return asset, account, permission

    def native_session(self):
        from terminal.models import Session
        asset, account, _ = self.handoff_asset()
        self.session.connection_token = service.create_connection_token(self.user, self.session.requested)
        self.session.terminal_session = Session.objects.create(
            terminal=self.node, user=str(self.user), user_id=str(self.user.id),
            asset=str(asset), asset_id=str(asset.id), account='root(root)', account_id=str(account.id), protocol='ssh',
        )
        self.session.credentials_released, self.session.status = True, 'ready'
        self.session.save()
        return asset

    def test_command_warning_notifies_once_and_prompt_requires_human_terminal(self):
        from acls.models import CommandFilterACL, CommandGroup
        from terminal.api.agent import AgentComponentAPI
        asset = self.native_session()
        rule = CommandFilterACL.objects.create(name='Agent warning', action='warning', priority=1,
            users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        group = CommandGroup.objects.create(name='Agent warning command', content='whoami')
        rule.command_groups.add(group)
        rule.reviewers.add(self.user)
        for policy in ('accept', 'notify_and_warn'):
            sibling = CommandFilterACL.objects.create(name=f'Agent competing {policy}', action=policy,
                priority=1, users=rule.users, assets=rule.assets, accounts=rule.accounts)
            sibling.command_groups.add(group)
        self.assertEqual(service.command_policy(self.session, 'whoami')[0].id, sibling.id)
        sibling.is_active = False
        sibling.save(update_fields=['is_active'])
        api = AgentComponentAPI(operation='claim')
        with patch('terminal.notifications.CommandWarningMessage.publish_async') as notify:
            for policy in ('warning', 'notify_and_warn', 'accept'):
                rule.action = policy
                rule.save(update_fields=['action'])
                action = AgentAction.objects.create(session=self.session, user=self.user, application=self.app,
                    kind='execute_command', idempotency_key=policy, request={'command': 'whoami'}, request_hash='5' * 64)
                with self.captureOnCommitCallbacks(execute=True):
                    result = api.action_operation(self.node, action.id, {'session_token': service.session_capability(self.session)})
                    repeated = api.action_operation(self.node, action.id, {'session_token': service.session_capability(self.session)})
                self.assertFalse(repeated['claimed'])
                self.assertEqual(result['claimed'], policy != 'notify_and_warn')
                if policy == 'warning':
                    self.assertEqual(result['result']['command_policy']['risk_level'], 4)
                    action.refresh_from_db()
                    service.append_event(action, {'session_token': 'receipt', 'event_id': str(uuid.uuid4()),
                        'sequence': 1, 'state': 'succeeded', 'payload': {'exit_code': 0}})
                    self.assertEqual(action.result['command_policy']['acl_id'], str(rule.id))
                elif policy == 'notify_and_warn':
                    self.assertTrue(result['result']['requires_terminal'])
                    self.assertEqual(result['status'], 'rejected')
            notify.assert_called_once()

    def test_final_actions_close_pending_command_reviews(self):
        from acls.models import CommandFilterACL, CommandGroup
        from terminal.api.agent import AgentComponentAPI
        asset = self.native_session()
        self.action.status = 'succeeded'
        self.action.save(update_fields=['status'])
        rule = CommandFilterACL.objects.create(name='Agent pending review', action='review', priority=1,
            users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        rule.command_groups.add(CommandGroup.objects.create(name='Agent review command', content='whoami'))
        rule.reviewers.add(self.user)
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        for outcome in ('cancel', 'expired', 'policy_changed', 'close'):
            action = AgentAction.objects.create(session=self.session, user=self.user, application=self.app,
                kind='execute_command', idempotency_key=outcome, request={'command': 'whoami'}, request_hash='6' * 64)
            service.authorize_action(action)
            ticket = action.ticket
            with self.captureOnCommitCallbacks(execute=True):
                if outcome == 'cancel':
                    AgentComponentAPI(operation='cancel').action_operation(self.node, action.id,
                        {'context_token': principal['context_token']})
                elif outcome == 'expired':
                    service.append_event(action, {'session_token': 'receipt', 'event_id': str(uuid.uuid4()),
                        'sequence': 1, 'state': 'expired', 'payload': {}})
                elif outcome == 'policy_changed':
                    rule.priority += 1
                    rule.save(update_fields=['priority'])
                    action = AgentAction.objects.get(pk=action.pk)
                    service.authorize_action(action)
                else:
                    AgentComponentAPI(operation='close').session_operation(self.node, self.session.id,
                        {'session_token': service.session_capability(self.session)})
            ticket.refresh_from_db()
            self.assertEqual(ticket.state, 'closed', outcome)

    def test_cancelled_connection_review_remains_open_for_other_tokens(self):
        from acls.models import LoginAssetACL
        from authentication.models import ConnectionToken
        from terminal.api.agent import AgentComponentAPI
        asset, _, _ = self.handoff_asset()
        rule = LoginAssetACL.objects.create(name='Agent shared login review', action='accept', review_enabled=True,
            users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        rule.reviewers.add(self.user)
        token = service.create_connection_token(self.user, self.session.requested)
        self.session.connection_token = token
        self.session.save(update_fields=['connection_token'])
        service.refresh_connection_status(self.session)
        token = self.session.connection_token
        ticket = token.from_ticket
        shared = ConnectionToken.objects.get(pk=token.pk)
        shared.pk = uuid.uuid4()
        shared.save(force_insert=True)
        self.action.kind, self.action.status = 'connect_asset', 'awaiting_approval'
        self.action.save(update_fields=['kind', 'status'])
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        with self.captureOnCommitCallbacks(execute=True):
            AgentComponentAPI(operation='cancel').action_operation(self.node, self.action.id,
                {'context_token': principal['context_token']})
        ticket.refresh_from_db()
        token.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertTrue(token.acl_context['cancelled'])
        with self.captureOnCommitCallbacks(execute=True):
            service.cancel_connection_controls(shared)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'closed')

    def test_browser_handoff_after_native_failure_uses_fresh_token_and_real_session(self):
        from accounts.models import Account
        from terminal.agent_views import AgentSessionView
        from terminal.api.agent import AgentComponentAPI
        from terminal.serializers import SessionSerializer
        asset, account, _ = self.handoff_asset()
        # Native exec cannot perform this interactive privilege switch. The
        # standard terminal must receive the original su-from account instead.
        asset.platform.su_enabled = True
        asset.platform.save(update_fields=['su_enabled'])
        account.su_from = Account.objects.create(name='login', username='login', asset=asset, secret='test-only-login')
        account.save(update_fields=['su_from'])
        # The original one-time connection failed and has already been cleaned
        # up. Only the bounded logical Agent session remains.
        self.session.connection_token = service.create_connection_token(self.user, self.session.requested)
        self.session.status = 'failed'
        self.session.save()
        original_token_id = self.session.connection_token_id
        self.session.connection_token.delete()
        self.session.refresh_from_db()
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        data = {'context_token': principal['context_token'], 'session_id': str(self.session.id),
                'kind': 'open_terminal', 'idempotency_key': 'human-fallback', 'request': {}}
        created = service.create_action(self.node, data)
        self.assertEqual(service.create_action(self.node, data)['id'], created['id'])
        with self.assertRaises(service.Conflict):
            service.create_action(self.node, {**data, 'kind': 'execute_command',
                'idempotency_key': 'no-native-command', 'request': {'command': 'pwd'}})
        api = AgentComponentAPI(operation='claim')
        self.assertTrue(api.action_operation(self.node, created['id'], {
            'session_token': service.session_capability(self.session),
        })['claimed'])
        self.action = AgentAction.objects.get(pk=created['id'])
        service.append_event(self.action, {'session_token': 'receipt', 'event_id': str(uuid.uuid4()),
            'sequence': 1, 'state': 'awaiting_input', 'payload': {}})
        request = RequestFactory().post('/core/auth/agent/session/', {'operation': 'credentials', 'action': str(self.action.id)})
        request.user = self.user
        response = AgentSessionView.as_view()(request, session_id=self.session.id)
        self.assertEqual(response.status_code, 302)
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, 'awaiting_input')
        self.assertNotEqual(self.action.interactive_token_id, original_token_id)
        self.assertEqual(response.url, '/luna/koko/connect?token=' + str(self.action.interactive_token_id))
        from authentication.serializers import ConnectionTokenSecretSerializer
        from authentication.services.connection_token import get_connection_token_secret
        secret = get_connection_token_secret(self.action.interactive_token, ConnectionTokenSecretSerializer)
        self.assertEqual(secret['account']['su_from']['username'], 'login')
        terminal = SessionSerializer().create({
            'user_id': str(self.user.id), 'asset_id': str(asset.id), 'account_id': str(account.id),
            'account': 'root(root)', 'protocol': 'ssh', 'terminal': self.node, 'org_id': str(self.org.id),
            'token_id': str(self.action.interactive_token_id),
        })
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, 'succeeded')
        self.assertEqual(self.action.interactive_session_id, terminal.id)
        self.assertEqual(terminal.login_from, 'AG')
        self.assertEqual(terminal.get_login_from_display(), 'Agent')
        self.assertEqual(SessionSerializer().fields['login_from'].run_validation('AG'), 'AG')
        web_terminal = SessionSerializer().create({
            'user_id': str(self.user.id), 'asset_id': str(asset.id), 'account_id': str(account.id),
            'account': 'root(root)', 'protocol': 'ssh', 'terminal': self.node, 'org_id': str(self.org.id),
            'login_from': 'WT',
        })
        self.assertEqual(web_terminal.login_from, 'WT')

    def test_live_monitor_policy_keeps_logical_session_and_gates_human_terminal(self):
        from unittest.mock import PropertyMock, patch
        from acls.models import LoginAssetACL
        from authentication.api.face import FaceMonitorContext
        from authentication.const import FACE_CONTEXT_CACHE_KEY_PREFIX
        from django.core.cache import cache
        from terminal.agent_views import AgentSessionView
        from terminal.api.agent import AgentComponentAPI
        asset, account, _ = self.handoff_asset()
        LoginAssetACL.objects.create(name='Agent live face', action='accept', face_online_enabled=True,
            users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        connected = service.create_session(self.node, {
            'context_token': principal['context_token'], 'asset_id': str(asset.id),
            'account': str(account.id), 'protocol': 'ssh', 'idempotency_key': 'face-connect',
        })
        self.assertTrue(connected['requires_terminal'])
        self.assertIsNone(connected['connection_token_id'])
        created = service.create_action(self.node, {'context_token': principal['context_token'],
            'session_id': connected['id'], 'kind': 'open_terminal', 'idempotency_key': 'face-human', 'request': {}})
        claimed = AgentComponentAPI(operation='claim').action_operation(self.node, created['id'], {
            'session_token': connected['session_token'],
        })
        self.assertTrue(claimed['claimed'])
        view = AgentSessionView.as_view()

        def post(body):
            request = RequestFactory().post('/core/auth/agent/session/', {'action': created['id'], **body})
            request.user, request.session = self.user, {}
            return view(request, session_id=connected['id'])

        response = post({'operation': 'credentials'})
        self.assertEqual(response.status_code, 200)
        action = AgentAction.objects.get(pk=created['id'])
        token = action.interactive_token
        monitor = FaceMonitorContext.get(token.face_monitor_token)
        self.assertEqual(str(monitor.user_id), str(self.user.id))
        self.addCleanup(monitor._destroy)
        self.assertNotContains(response, 'id="agent-human-terminal"')
        with patch.object(User, 'is_face_code_set', new_callable=PropertyMock, return_value=True):
            response = post({'step': 'face', 'retry_face': 'true'})
        token.refresh_from_db()
        face_key = f"{FACE_CONTEXT_CACHE_KEY_PREFIX}_{token.acl_context['face_token']}"
        face = cache.get(face_key)
        face.update({'is_finished': True, 'success': True})
        cache.set(face_key, face, 60)
        self.addCleanup(cache.delete, face_key)
        response = post({'step': 'face'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/luna/facelive/monitor?token=' + token.face_monitor_token)
        self.assertContains(response, 'id="agent-human-terminal"')
        self.assertNotContains(response, 'src="/luna/koko/connect')
        token.refresh_from_db()
        monitor._destroy()
        with self.assertRaises(PermissionDenied):
            token.is_valid()

    def test_handoff_rechecks_permission_grant_and_logical_session_lifetime(self):
        _, _, permission = self.handoff_asset()
        self.action.kind, self.action.status = 'open_terminal', 'accepted'
        self.action.save(update_fields=['kind', 'status'])
        service.check_handoff_authority(self.session)
        permission.is_active = False
        permission.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            service.authorize_action(self.action)
        permission.is_active = True
        permission.save(update_fields=['is_active'])
        for field in ('date_closed', 'date_expires'):
            original = getattr(self.session, field)
            setattr(self.session, field, timezone.now() - timedelta(seconds=1))
            with self.assertRaises(PermissionDenied):
                service.check_handoff_authority(self.session)
            setattr(self.session, field, original)
        self.refresh.revoke()
        with self.assertRaises(PermissionDenied):
            service.check_handoff_authority(self.session)

    def test_shared_connection_service_keeps_web_creation_and_acl_initialization(self):
        from acls.models import LoginAssetACL
        from authentication.api.connection_token import ConnectionTokenViewSet
        from authentication.models import ConnectionToken
        from rest_framework.test import APIRequestFactory, force_authenticate
        asset, account, _ = self.handoff_asset()
        LoginAssetACL.objects.create(name='Agent shared reason', action='accept', reason_enabled=True,
            users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        request = APIRequestFactory().post('/api/v1/authentication/connection-token/?acl_stepwise=1', {
            'asset': str(asset.id), 'account': str(account.id), 'protocol': 'ssh', 'connect_method': 'web_cli',
        }, format='json')
        force_authenticate(request, user=self.user)
        response = ConnectionTokenViewSet.as_view({'post': 'create'}, permission_classes=[])(request)
        self.assertEqual(response.status_code, 201, response.data)
        web = ConnectionToken.objects.get(pk=response.data['id'])
        agent = service.create_connection_token(self.user, self.session.requested)
        self.assertEqual(web.acl_context['requirements'], {'reason': 'pending'})
        for field in ('user_id', 'asset_id', 'account', 'protocol', 'connect_options', 'acl_context', 'is_active'):
            self.assertEqual(getattr(web, field), getattr(agent, field), field)

    @override_settings(TRUSTED_IP_VERIFY_ENABLED=True)
    def test_component_source_ip_reaches_login_policy_with_signed_ip_mode(self):
        from acls.models import LoginAssetACL
        asset, _, _ = self.handoff_asset()
        LoginAssetACL.objects.create(name='Agent verified source', action='accept', reason_enabled=True,
            rules={'ip_group': ['192.0.2.12']}, users={'type': 'ids', 'ids': [str(self.user.id)]},
            assets={'type': 'ids', 'ids': [str(asset.id)]}, accounts=['root'])
        token = service.create_connection_token(self.user, {**self.session.requested, 'remote_addr': '192.0.2.12'})
        self.assertEqual(token.remote_addr, '192.0.2.12')
        self.assertEqual(token.acl_context['requirements'], {'reason': 'pending'})
        with self.assertRaises(ValidationError):
            service.create_connection_token(self.user, {**self.session.requested, 'remote_addr': '192.0.2.12, 127.0.0.1'})

    def test_audit_links_select_authorized_organization_over_browser_cookie(self):
        from orgs.middleware import OrgMiddleware
        from terminal.agent_views import AgentAuditView
        browser_org = Organization.objects.create(name='Agent browser organization')
        browser_org.add_member(self.user)
        url = service.action_data(self.action)['audit_url']
        self.assertTrue(url.endswith(f'?oid={self.org.id}'))
        request = RequestFactory().get(url, HTTP_COOKIE=f'X-JMS-ORG={browser_org.id}')
        request.user, request.session = self.user, {}
        view = AgentAuditView.as_view(kind='actions')
        with tmp_to_org(browser_org):
            response = OrgMiddleware(lambda req: view(req, object_id=self.action.id))(request)
        self.assertContains(response, f'/core/auth/agent/audit/sessions/?oid={self.org.id}')
        self.assertContains(response, f'/core/auth/agent/audit/actions/?oid={self.org.id}')

    def test_audit_html_escapes_output_preserves_newlines_and_isolates_organizations(self):
        from terminal.agent_views import AgentAuditView
        from orgs.utils import tmp_to_root_org
        service.append_event(self.action, {'session_token': 'receipt', 'event_id': str(uuid.uuid4()),
            'sequence': 1, 'state': 'running', 'payload': {'stream': 'stdout', 'encoding': 'base64', 'data': base64.b64encode(b'first\n<script>alert(1)</script>').decode()}})
        request = RequestFactory().get('/core/auth/agent/audit/actions/')
        request.user = self.user
        request.session = {}
        response = AgentAuditView.as_view(kind='actions')(request, object_id=self.action.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'first\n&lt;script&gt;alert(1)&lt;/script&gt;')
        other_org = Organization.objects.create(name='Agent isolated organization')
        other_user = User.objects.create(username='agent-other-owner', name='Other owner')
        other_org.add_member(other_user)
        with tmp_to_org(other_org):
            foreign = AgentSession.objects.create(user=other_user, application=self.app, terminal=self.node,
                resource=self.resource, idempotency_key='other-org', request_hash='2' * 64,
                date_expires=timezone.now() + timedelta(hours=1))
            foreign_action = AgentAction.objects.create(session=foreign, user=other_user, application=self.app,
                kind='file_read', idempotency_key='other-org-action', request_hash='3' * 64)
        with tmp_to_root_org(), self.assertRaises(Http404):
            AgentAuditView.as_view(kind='actions')(request, object_id=foreign_action.id)

    def test_manual_credentials_are_completed_only_by_browser_owner(self):
        from assets.models import Asset, Platform
        from perms.models import AssetPermission
        from terminal.agent_views import AgentSessionView
        platform = Platform.objects.create(name='Agent manual Linux', category='host', type='linux')
        platform.protocols.create(name='ssh', port=22)
        asset = Asset.objects.create(name='Agent manual asset', address='192.0.2.3', platform=platform)
        asset.protocols.create(name='ssh', port=22)
        permission = AssetPermission.objects.create(name='Agent manual access', accounts=['@INPUT'], protocols=['ssh'])
        permission.users.add(self.user)
        permission.assets.add(asset)
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        result = service.create_session(self.node, {'context_token': principal['context_token'],
            'asset_id': str(asset.id), 'account': '@INPUT', 'protocol': 'ssh', 'idempotency_key': 'manual'})
        session = AgentSession.objects.get(pk=result['id'])
        self.assertIsNone(session.connection_token_id)
        request = RequestFactory().post('/core/auth/agent/session/', {
            'operation': 'credentials', 'input_username': 'manual', 'input_secret': 'private-to-core',
            'input_secret_type': 'password',
        })
        request.user, request.session = self.user, {}
        response = AgentSessionView.as_view()(request, session_id=session.id)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'private-to-core')
        session.refresh_from_db()
        self.assertEqual(session.status, 'ready')
        self.assertEqual(session.connection_token.input_username, 'manual')
        self.assertEqual(session.connection_token.input_secret, 'private-to-core')

    def test_audit_lists_and_session_actions_are_paginated(self):
        from terminal.api.agent import AgentAuditAPI
        from terminal.agent_views import AgentAuditView
        AgentAction.objects.bulk_create([
            AgentAction(session=self.session, user=self.user, application=self.app, kind='file_read',
                        idempotency_key=f'page-{index}', request_hash='4' * 64)
            for index in range(101)
        ])
        request = RequestFactory().get('/api/v1/terminal/agent/audit/actions/')
        request.user, request.session, request.query_params = self.user, {}, request.GET
        api = AgentAuditAPI(kind='actions')
        first = api.get(request).data
        self.assertEqual(len(first['results']), 100)
        self.assertEqual(first['count'], 102)
        self.assertEqual(first['next_offset'], 100)
        request.query_params = QueryDict('limit=10000')
        self.assertEqual(len(api.get(request).data['results']), 100)
        request.query_params = QueryDict('offset=100')
        second = api.get(request).data
        self.assertEqual(len(second['results']), 2)
        self.assertIsNone(second['next_offset'])
        self.assertFalse({item['id'] for item in first['results']} & {item['id'] for item in second['results']})
        request.query_params = QueryDict()
        session_page = AgentAuditAPI(kind='sessions').get(request, self.session.id).data
        self.assertEqual(len(session_page['actions']), 100)
        self.assertEqual(session_page['next_offset'], 100)
        page = AgentAuditView.as_view(kind='sessions')(request, object_id=self.session.id)
        self.assertContains(page, '?offset=100')

    def audit_api(self, kind, params=None, method='get'):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from terminal.api.agent import AgentAuditAPI
        request = getattr(APIRequestFactory(), method)(
            f'/api/v1/terminal/agent/audit/{kind}/', params or {},
        )
        force_authenticate(request, self.user)
        response = AgentAuditAPI.as_view(kind=kind)(request)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_audit_metadata_exposes_search_filters_and_sorting(self):
        for kind in ('sessions', 'actions'):
            data = self.audit_api(kind, method='options')
            self.assertIn('status', data['filters'])
            self.assertIn('account', data['filters'])
            self.assertIn('icontains_any', data['filters']['account']['operators'])
            self.assertTrue(data['filters']['status']['choices'])
            self.assertEqual(data['search']['param'], 'search')
            self.assertIn('date_created', [field['name'] for field in data['ordering']['fields']])
            self.assertNotIn('capability', data['actions']['GET'])
        self.assertIn('kind', data['filters'])
        self.assertIn('session_id', data['filters'])

    def test_audit_action_queries_filter_before_ordering_and_pagination(self):
        older = timezone.now() - timedelta(days=2)
        match = AgentAction.objects.create(
            session=self.session, user=self.user, application=self.app, kind='file_read',
            idempotency_key='audit-match', request_hash='2' * 64, status='succeeded', date_created=older,
        )
        AgentAction.objects.create(
            session=self.session, user=self.user, application=self.app, kind='execute_command',
            idempotency_key='audit-other-kind', request_hash='3' * 64, status='succeeded',
        )
        params = {
            'kind': 'file_read', 'status__in': 'dispatching,succeeded',
            'account__icontains_any': 'oot,deploy', 'protocol__in': 'ssh,sftp',
            'user_display__icontains': self.user.username, 'search': self.app.client_id,
            'session_id': str(self.session.id), 'order': 'date_created', 'limit': 1,
        }
        first = self.audit_api('actions', params)
        self.assertEqual(first['count'], 2)
        self.assertEqual([item['id'] for item in first['results']], [str(match.id)])
        self.assertEqual(first['next_offset'], 1)
        second = self.audit_api('actions', {**params, 'offset': 1})
        self.assertEqual([item['id'] for item in second['results']], [str(self.action.id)])
        self.assertIsNone(second['next_offset'])
        by_date = self.audit_api('actions', {**params, 'date_to': older.isoformat()})
        self.assertEqual(by_date['count'], 1)
        by_search = self.audit_api('actions', {'search': 'execute_command'})
        self.assertEqual(by_search['count'], 1)

    def test_audit_session_queries_filter_requested_fields_and_dates(self):
        older = timezone.now() - timedelta(days=2)
        session = AgentSession.objects.create(
            user=self.user, application=self.app, terminal=self.node, resource=self.resource,
            idempotency_key='audit-sftp', request_hash='5' * 64, status='closed',
            requested={'asset_id': str(uuid.uuid4()), 'protocol': 'sftp', 'account': 'deploy'},
            date_created=older, date_expires=older + timedelta(hours=1),
        )
        params = {
            'protocol__in': 'sftp', 'account__icontains_any': 'deploy,root', 'status': 'closed',
            'asset_id': session.requested['asset_id'], 'search': 'deploy',
            'date_to': older.isoformat(), 'order': 'account', 'limit': 15,
        }
        data = self.audit_api('sessions', params)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['id'], str(session.id))
        self.assertEqual(self.audit_api('sessions', {**params, 'date_from': timezone.now().isoformat()})['count'], 0)

    def test_audit_queries_preserve_owner_and_organization_scope(self):
        other = User.objects.create(username='agent-audit-other')
        self.org.add_member(other)
        session = AgentSession.objects.create(
            user=other, application=self.app, terminal=self.node, resource=self.resource,
            idempotency_key='audit-other-owner', request_hash='6' * 64,
            date_expires=timezone.now() + timedelta(hours=1),
        )
        AgentAction.objects.create(
            session=session, user=other, application=self.app, kind='file_read',
            idempotency_key='audit-other-owner', request_hash='7' * 64,
        )
        self.assertEqual(self.audit_api('sessions', {'id': str(session.id)})['count'], 0)
        self.assertEqual(self.audit_api('actions', {'session_id': str(session.id)})['count'], 0)
        other_org = Organization.objects.create(name='Agent audit other organization')
        with tmp_to_org(other_org):
            foreign = AgentSession.objects.create(
                user=self.user, application=self.app, terminal=self.node, resource=self.resource,
                idempotency_key='audit-other-org', request_hash='8' * 64,
                date_expires=timezone.now() + timedelta(hours=1),
            )
        self.assertEqual(self.audit_api('sessions', {'id': str(foreign.id)})['count'], 0)

    def test_access_only_authorization_expires_without_refresh_family(self):
        self.refresh.delete()
        self.session.oauth_family = None
        self.session.save(update_fields=['oauth_family'])
        self.token.expires = timezone.now() - timedelta(seconds=1)
        self.token.save(update_fields=['expires'])
        with self.assertRaises(PermissionDenied):
            service.check_session_authority(self.session, connection=False)

    def test_asset_account_pages_include_all_authorized_accounts_with_bounded_output(self):
        from accounts.models import Account
        from assets.models import Asset, Platform
        from perms.models import AssetPermission
        from terminal.api.agent import AgentComponentAPI
        platform = Platform.objects.create(name='Agent account page Linux', category='host', type='linux')
        platform.protocols.create(name='ssh', port=22)
        asset = Asset.objects.create(name='Agent account page asset', address='192.0.2.4', platform=platform)
        asset.protocols.create(name='ssh', port=22)
        accounts = Account.objects.bulk_create([
            Account(name=f'account-{i:03}', username=f'account-{i:03}', asset=asset) for i in range(101)
        ])
        permission = AssetPermission.objects.create(name='Agent account page access', accounts=['@ALL', '@INPUT'], protocols=['ssh'])
        permission.users.add(self.user)
        permission.assets.add(asset)
        principal = service.introspect(self.node, {'access_token': self.token.token, 'resource': self.resource})
        body = {'context_token': principal['context_token'], 'asset_id': str(asset.id)}
        first = AgentComponentAPI.assets(self.node, body)['results'][0]
        self.assertEqual(len(first['accounts']), 100)
        second = AgentComponentAPI.assets(self.node, {**body, 'account_offset': first['accounts_next_offset']})['results'][0]
        self.assertEqual(len(second['accounts']), 2)
        self.assertIsNone(second['accounts_next_offset'])
        returned = [item['id'] for item in first['accounts'] + second['accounts']]
        self.assertEqual(set(returned), {str(account.id) for account in accounts} | {'@INPUT'})
        self.assertEqual(len(returned), len(set(returned)))
        self.assertEqual(AgentComponentAPI.assets(self.node, {**body, 'asset_id': str(uuid.uuid4())})['results'], [])
