from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
import time

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase, override_settings

from accounts.const import AliasAccount
from acls.api.login_asset_check import LoginAssetCheckAPI
from acls.models import LoginAssetACL
from acls.models.login_asset_acl import LoginAssetPolicy
from acls.serializers.login_asset_acl import LoginAssetACLSerializer
from authentication.api.connection_token import ConnectionTokenViewSet
from common.exceptions import JMSException
from tickets.const import TicketState
from tickets.models import Ticket
from tickets.serializers.ticket import TicketSerializer
from rest_framework.exceptions import PermissionDenied


@override_settings(CACHES={'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
}})
class AssetReviewExemptionTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.acl = LoginAssetACL(action='accept', review_enabled=True, review_duration=2, org_id=str(uuid4()))
        self.policy = LoginAssetPolicy((self.acl,))
        self.user = SimpleNamespace(id=uuid4())
        asset_id = uuid4()
        self.asset = SimpleNamespace(
            id=asset_id, pk=asset_id, org_id=self.acl.org_id,
            name='asset', address='192.0.2.10',
        )
        self.key = self.acl.get_review_cache_key(self.user.id, self.asset.id, 'root')
        self.user.pk = self.user.id
        self.asset.pk = self.asset.id
        self.ticket = Ticket(
            state=TicketState.approved, org_id=self.acl.org_id,
            applicant_id=self.user.id,
            request_data={'apply_login_asset': str(self.asset.id), 'apply_login_account': 'root'},
            meta={'login_asset_reviews': [{'acl_id': str(self.acl.id), 'cache_key': self.key}]},
        )
        self.instance = SimpleNamespace(state='approved', applicant_id=self.user.id, context={
            'assets': [{'id': str(self.asset.id)}], 'accounts': [{'username': 'root'}],
        })
        self.query = patch.object(LoginAssetACL.objects, 'filter').start()
        self.query.return_value.first.return_value = self.acl
        patch('acls.models.login_asset_acl.tmp_to_org', side_effect=lambda org: nullcontext()).start()
        patch.object(LoginAssetACL, 'get_review_assignees', return_value=[Mock()]).start()
        patch('authentication.api.connection_token.get_request_os', return_value='linux').start()
        patch('authentication.api.connection_token.ConnectMethodUtil.get_connect_method', return_value=None).start()
        self.addCleanup(patch.stopall)

    def test_commit_rollback_and_fixed_expiry(self):
        # A private SQLite connection exercises real on_commit/rollback without app tables.
        config = {**settings.DATABASES['default'], 'NAME': ':memory:', 'OPTIONS': {}}
        connection = DatabaseWrapper(config, alias='asset-review-test')
        self.addCleanup(connection.close)
        with patch('django.db.transaction.get_connection', return_value=connection):
            with transaction.atomic():
                LoginAssetACL.cache_approved_review(self.ticket, self.instance)
                self.assertIsNone(cache.get(self.key))
            self.assertEqual(cache.get(self.key), str(self.ticket.id))
            cache.clear()
            with self.assertRaises(ValueError):
                with transaction.atomic():
                    LoginAssetACL.cache_approved_review(self.ticket, self.instance)
                    raise ValueError('rollback')
            self.assertIsNone(cache.get(self.key))

            started = time.time()
            with patch('time.time', return_value=started):
                with transaction.atomic():
                    LoginAssetACL.cache_approved_review(self.ticket, self.instance)
            with patch('time.time', return_value=started + 7199):
                self.assertTrue(self.acl.is_review_exempt(self.user, self.asset, 'root'))
                self.acl.review_duration = 0
                self.assertEqual(cache.get(self.key), str(self.ticket.id))
                self.assertFalse(self.acl.is_review_exempt(self.user, self.asset, 'root'))
            with patch('time.time', return_value=started + 7200):
                self.assertIsNone(cache.get(self.key))
                self.assertFalse(self.acl.is_review_exempt(self.user, self.asset, 'root'))

    def test_cache_is_scoped_to_org_acl_user_asset_and_actual_username(self):
        cache.set(self.key, str(self.ticket.id), 7200)
        self.assertTrue(self.acl.is_review_exempt(self.user, self.asset, 'root'))
        for user, asset, username in [
            (SimpleNamespace(id=uuid4()), self.asset, 'root'),
            (self.user, SimpleNamespace(id=uuid4()), 'root'),
            (self.user, self.asset, 'admin'),
        ]:
            self.assertFalse(self.acl.is_review_exempt(user, asset, username))
        other_acl = LoginAssetACL(action='accept', review_enabled=True, org_id=self.acl.org_id)
        self.assertFalse(other_acl.is_review_exempt(self.user, self.asset, 'root'))
        self.acl.org_id = str(uuid4())
        self.assertFalse(self.acl.is_review_exempt(self.user, self.asset, 'root'))

    def test_unapproved_legacy_changed_and_disabled_reviews_do_not_grant_exemption(self):
        with patch('acls.models.login_asset_acl.transaction.on_commit') as on_commit:
            for state in [TicketState.pending, TicketState.rejected, TicketState.closed]:
                self.instance.state = state
                LoginAssetACL.cache_approved_review(self.ticket, self.instance)
            self.instance.state = TicketState.approved
            self.ticket.meta = {}
            LoginAssetACL.cache_approved_review(self.ticket, self.instance)
            self.ticket.meta = {'login_asset_review': {'acl_id': str(self.acl.id), 'cache_key': self.key}}
            self.instance.context['accounts'][0]['username'] = 'admin'
            LoginAssetACL.cache_approved_review(self.ticket, self.instance)
            self.instance.context['accounts'][0]['username'] = 'root'
            self.acl.review_duration = 0
            LoginAssetACL.cache_approved_review(self.ticket, self.instance)
            self.query.return_value.first.return_value = None
            LoginAssetACL.cache_approved_review(self.ticket, self.instance)
            on_commit.assert_not_called()
        self.query.assert_called_with(id=str(self.acl.id), is_active=True, review_enabled=True)

    def test_cache_failures_are_safe(self):
        with patch('acls.models.login_asset_acl.cache.get', side_effect=RuntimeError('offline')), \
                patch('acls.models.login_asset_acl.logger.exception') as log:
            self.assertFalse(self.acl.is_review_exempt(self.user, self.asset, 'root'))
            log.assert_called_once()
        with patch('acls.models.login_asset_acl.cache.set', side_effect=RuntimeError('offline')), \
                patch('acls.models.login_asset_acl.logger.exception') as log:
            LoginAssetACL._cache_review(self.key, str(self.ticket.id), 7200)
            log.assert_called_once()

    def test_ticket_creation_saves_server_generated_match(self):
        with patch.object(Ticket.objects, 'create') as create, patch.object(LoginAssetACL, 'review_configuration', return_value={}):
            reviewers = [Mock()]
            workflow = Mock()
            ticket = LoginAssetACL.create_login_asset_review_ticket.__wrapped__(
                self.acl, self.user, self.asset, 'root', reviewers, self.acl.org_id, workflow=workflow,
            )
            self.assertEqual(create.call_args.kwargs['meta'], {
                **self.ticket.meta, 'login_asset_review_config': {},
                'login_asset_connections': [{
                    'asset_id': str(self.asset.id), 'asset_name': self.asset.name,
                    'asset_address': self.asset.address, 'account': 'root', 'reason': '',
                    'reviews': self.ticket.meta['login_asset_reviews'],
                }],
            })
            self.assertEqual(create.call_args.kwargs['request_data']['apply_login_account'], 'root')
            ticket.open_by_system.assert_called_once_with(reviewers, workflow=workflow)

    def test_duration_validation_and_private_ticket_metadata(self):
        field = LoginAssetACLSerializer().fields['review_duration']
        self.assertEqual(field.run_validation(0), 0)
        self.assertEqual(field.run_validation(2), 2)
        from rest_framework.exceptions import ValidationError
        for value in [-1, 1.5, None, 'invalid']:
            with self.assertRaises(ValidationError):
                field.run_validation(value)
        self.assertNotIn('meta', TicketSerializer().fields)

    def test_token_entry_uses_resolved_account_and_still_requires_acl_match(self):
        view = ConnectionTokenViewSet()
        view.request = SimpleNamespace(query_params={}, META={}, user=self.user)
        view.input_username = 'account-display-name'
        view._record_operate_log = Mock()
        account = SimpleNamespace(username='root')
        with patch.object(LoginAssetACL, 'filter_queryset'), \
                patch.object(LoginAssetACL, 'get_match_rule_acls', return_value=self.policy) as match, \
                patch('authentication.api.connection_token.get_request_ip_or_data', return_value='127.0.0.1'):
            context = view._validate_acl(self.user, self.asset, account, 'web_cli', 'ssh')
            self.assertEqual(context['requirements'], {'review': 'pending'})
            self.assertEqual(context['review_acls'], [str(self.acl.pk)])
            cache.set(self.key, str(self.ticket.id), 7200)
            self.assertEqual(view._validate_acl(self.user, self.asset, account, 'web_cli', 'ssh')['requirements'], {})
            view._record_operate_log.assert_called_with(self.acl, self.asset)
            account.username = AliasAccount.INPUT
            view.input_username = 'admin'
            self.assertEqual(view._validate_acl(self.user, self.asset, account, 'web_cli', 'ssh')['requirements'], {'review': 'pending'})
            view.input_username = 'root'
            self.assertEqual(view._validate_acl(self.user, self.asset, account, 'web_cli', 'ssh')['requirements'], {})
            self.acl.action = 'reject'
            with self.assertRaises(JMSException):
                view._validate_acl(self.user, self.asset, account, 'web_cli', 'ssh')
            self.assertEqual(match.call_count, 5)

    def test_cached_review_does_not_skip_current_ip_or_time_matching(self):
        self.acl.rules = {
            'ip_group': ['192.0.2.10'],
            'time_period': [{'id': i, 'value': '09:00~10:00'} for i in range(7)],
        }
        reject = LoginAssetACL(action='reject', priority=100)
        cache.set(self.key, str(self.ticket.id), 7200)
        view = ConnectionTokenViewSet()
        view.request = SimpleNamespace(query_params={}, META={}, user=self.user)
        view._record_operate_log = Mock()
        with patch.object(LoginAssetACL, 'filter_queryset', return_value=[self.acl, reject]), \
                patch('authentication.api.connection_token.get_request_ip_or_data') as request_ip, \
                patch('common.utils.timezone.local_now') as now:
            for ip, hour, allowed in [('192.0.2.10', 9, True), ('192.0.2.11', 9, False), ('192.0.2.10', 12, False)]:
                request_ip.return_value = ip
                now.return_value = datetime(2026, 9, 23, hour, 30)
                with self.subTest(ip=ip, hour=hour):
                    if allowed:
                        self.assertEqual(view._validate_acl(
                            self.user, self.asset, SimpleNamespace(username='root'), 'web_cli', 'ssh',
                        )['requirements'], {})
                    else:
                        with self.assertRaises(JMSException):
                            view._validate_acl(
                                self.user, self.asset, SimpleNamespace(username='root'), 'web_cli', 'ssh',
                            )

    def test_jobs_do_not_use_interactive_review_exemption(self):
        from ops.api.job import LoginAssetACLCheckMixin

        cache.set(self.key, str(self.ticket.id), 7200)
        self.asset.name = 'asset'
        self.asset.address = '192.0.2.10'
        with patch.object(LoginAssetACL, 'filter_queryset'), \
                patch.object(LoginAssetACL, 'get_match_rule_acls', return_value=self.policy):
            with self.assertRaises(PermissionDenied):
                LoginAssetACLCheckMixin().check_login_asset_acls(
                    self.user, [self.asset], 'root', '127.0.0.1',
                )

    def test_check_entry_miss_hit_and_rejection(self):
        view = LoginAssetCheckAPI()
        view.request = Mock()
        view.__dict__['serializer'] = SimpleNamespace(
            user=self.user, asset=self.asset, validated_data={'account_username': 'root'},
        )
        with patch.object(LoginAssetACL, 'filter_queryset'), \
                patch.object(LoginAssetACL, 'get_match_rule_acls', return_value=self.policy), \
                patch('acls.api.login_asset_check.get_request_ip_or_data', return_value='127.0.0.1'):
            self.assertTrue(view.check_review()['need_review'])
            cache.set(self.key, str(self.ticket.id), 7200)
            self.assertEqual(view.check_review(), {'need_review': False, 'requirements': ['review']})
            self.acl.action = 'reject'
            with self.assertRaises(JMSException):
                view.check_review()
