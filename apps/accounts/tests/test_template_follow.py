from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework import serializers

from accounts.exceptions import TemplateFollowingConflict
from accounts.models import Account
from accounts.serializers.account.account import AccountCreateUpdateSerializerMixin, AccountSerializer
from accounts.serializers.account.template import AccountTemplateSerializer
from accounts.tasks.template import template_sync_related_accounts


class FollowSerializer(AccountCreateUpdateSerializerMixin, serializers.Serializer):
    def set_initial_value(self):
        pass


class TemplateFollowTests(SimpleTestCase):
    def setUp(self):
        self.account = SimpleNamespace(
            source='template', source_id='template-id', org_id='org',
            follow_template=True, name='old', privileged=False, secret_type='password',
        )
        self.template = SimpleNamespace(
            id='template-id', org_id='org', name='new', privileged=True, secret_type='password',
        )

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter')
    def test_non_template_cannot_follow(self, query):
        self.account.source = 'local'
        with self.assertRaises(serializers.ValidationError):
            FollowSerializer(instance=self.account).validate({'follow_template': True})
        query.assert_not_called()

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter')
    def test_missing_or_cross_org_template_cannot_follow(self, query):
        for template in (None, SimpleNamespace(org_id='another-org')):
            query.return_value.first.return_value = template
            with self.assertRaises(serializers.ValidationError):
                FollowSerializer(instance=self.account).validate({'follow_template': True})

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter')
    def test_independent_fields_can_change_while_following(self, query):
        query.return_value.first.return_value = self.template
        attrs = {'comment': 'note', 'name': 'custom', 'privileged': True}
        self.assertEqual(FollowSerializer(instance=self.account).validate(attrs), attrs)

    @patch('accounts.serializers.account.account.AccountTemplate.objects.filter')
    def test_managed_fields_require_opt_out(self, query):
        query.return_value.first.return_value = self.template
        serializer = FollowSerializer(instance=self.account)
        with self.assertRaises(TemplateFollowingConflict) as error:
            serializer.validate({'secret': 'custom-password'})
        self.assertEqual(error.exception.get_codes(), 'account_template_following')
        attrs = {'secret': 'custom-password', 'follow_template': False}
        self.assertEqual(serializer.validate(attrs), attrs)

    def run_sync(self, account):
        with patch('accounts.models.AccountTemplate.objects.filter') as templates, \
                patch('accounts.models.Account.objects.filter') as accounts, \
                patch('accounts.models.Account.objects.select_for_update') as locked, \
                patch('accounts.tasks.template.tmp_to_root_org', return_value=nullcontext()), \
                patch('accounts.tasks.template.tmp_to_org', return_value=nullcontext()), \
                patch('accounts.tasks.template.transaction.atomic', return_value=nullcontext()):
            templates.return_value.first.return_value = self.template
            accounts.return_value.values_list.return_value = ['account-id']
            locked.return_value.filter.return_value.first.return_value = account
            template_sync_related_accounts.run('template-id')
            accounts.assert_called_once_with(
                source='template', source_id='template-id', follow_template=True,
            )
            locked.return_value.filter.assert_called_once_with(
                id='account-id', source='template', source_id='template-id', follow_template=True,
            )

    def test_sync_preserves_credentials_and_authentication_identity(self):
        account = Account(name='old', username='original', secret_type='ssh_key',
                          privileged=False, is_active=False, source='template',
                          source_id='template-id', follow_template=True)
        account._secret = 'external-vault-marker'
        account.save = Mock()
        self.run_sync(account)
        account.save.assert_not_called()
        self.assertFalse(account.privileged)
        self.assertEqual(account._secret, 'external-vault-marker')
        self.assertEqual(account.name, 'old')
        self.assertEqual(account.username, 'original')
        self.assertEqual(account.secret_type, 'ssh_key')
        self.assertFalse(account.is_active)

    def test_sync_preserves_source_and_following(self):
        self.account.save = Mock(side_effect=ValueError('name conflict'))
        with patch('accounts.tasks.template.logger.exception'):
            self.run_sync(self.account)
        self.assertEqual(self.account.source_id, 'template-id')
        self.assertTrue(self.account.follow_template)

    def test_queued_sync_respects_opt_out(self):
        self.run_sync(None)

    @patch('accounts.serializers.account.template.BaseAccountSerializer.update')
    @patch('accounts.serializers.account.template.transaction.on_commit')
    @patch('accounts.serializers.account.template.template_sync_related_accounts.delay')
    def test_template_privilege_change_does_not_schedule_sync(self, delay, on_commit, update):
        update.return_value = self.template
        serializer = AccountTemplateSerializer()
        serializer.update(self.template, {'privileged': False})
        delay.assert_not_called()
        on_commit.assert_not_called()

    @patch('accounts.serializers.account.template.BaseAccountSerializer.update')
    @patch('accounts.serializers.account.template.transaction.on_commit')
    def test_template_name_and_secret_changes_do_not_schedule_sync(self, on_commit, update):
        update.return_value = self.template
        AccountTemplateSerializer().update(self.template, {'name': 'changed', 'secret': 'new-secret'})
        on_commit.assert_not_called()

    @patch('accounts.serializers.account.account.Account.objects.filter')
    def test_account_creation_rejects_following_for_local_source(self, query):
        query.return_value.exists.return_value = False
        with self.assertRaises(serializers.ValidationError) as error:
            AccountSerializer().validate({'source': 'local', 'follow_template': True})
        self.assertIn('follow_template', error.exception.detail)

    @patch('accounts.serializers.account.account.BaseAccountSerializer.update')
    def test_editing_account_preserves_template_provenance(self, update):
        update.return_value = self.account
        serializer = AccountSerializer(instance=self.account)
        attrs = {'comment': 'updated note'}
        serializer.update(self.account, attrs)
        self.assertNotIn('source_id', update.call_args.args[1])
        self.assertEqual(self.account.source_id, 'template-id')

    @patch.object(FollowSerializer, 'get_template_attr_for_account', return_value={})
    def test_template_creation_defaults_to_following_and_respects_opt_out(self, attrs):
        for explicit in (None, False):
            data = {'template': self.template}
            if explicit is not None:
                data['follow_template'] = explicit
            FollowSerializer().from_template_if_need(data)
            self.assertEqual(data['source'], 'template')
            self.assertEqual(data['source_id'], 'template-id')
            self.assertIs(data['follow_template'], explicit is None)


class TemplateCredentialTests(SimpleTestCase):
    def make_account(self, **kwargs):
        values = dict(source='template', source_id='template-id', follow_template=True,
                      org_id='org', secret_type='password')
        values.update(kwargs)
        return Account(**values)

    def test_reads_current_template_without_using_account_secret_cache(self):
        account = self.make_account(follow_template=False)
        account.secret = 'stale-account-secret'
        account.follow_template = True
        template = SimpleNamespace(secret='first', secret_has_save_to_vault=False)
        with patch.object(Account, 'get_source_template', return_value=template):
            self.assertEqual(account.secret, 'first')
            template.secret = 'second'
            self.assertEqual(account.secret, 'second')
        self.assertEqual(account._secret, 'stale-account-secret')

    def test_independent_account_reads_own_secret(self):
        account = self.make_account(follow_template=False)
        account.secret = 'own-secret'
        with patch.object(Account, 'get_source_template') as lookup:
            self.assertEqual(account.secret, 'own-secret')
            lookup.assert_not_called()

    def test_following_secret_setter_rejects_write(self):
        account = self.make_account()
        with self.assertRaises(serializers.ValidationError):
            account.secret = 'replacement'
        self.assertIsNone(account._secret)

    def test_template_lookup_failure_never_falls_back(self):
        account = self.make_account()
        account._secret = 'old-secret'
        with patch.object(Account, 'get_source_template', side_effect=serializers.ValidationError('missing')):
            with self.assertRaises(serializers.ValidationError):
                _ = account.secret

    def test_missing_vault_secret_never_falls_back(self):
        from accounts.exceptions import VaultSecretNotFoundException
        account = self.make_account()
        account._secret = 'old-secret'
        template = SimpleNamespace(secret=None, secret_has_save_to_vault=True)
        with patch.object(Account, 'get_source_template', return_value=template):
            with self.assertRaises(VaultSecretNotFoundException):
                _ = account.secret

    @patch('accounts.signal_handlers.vault_client')
    def test_following_account_save_does_not_write_vault(self, vault):
        from accounts.signal_handlers import VaultSignalHandler
        for created in (True, False):
            VaultSignalHandler.save_to_vault(Account, self.make_account(), created)
        vault.create.assert_not_called()
        vault.update.assert_not_called()

    def test_following_creation_does_not_generate_or_copy_secret(self):
        template = SimpleNamespace(name='name', username='user', secret_type='password',
                                   privileged=False, is_active=True, get_secret=Mock())
        attrs = AccountCreateUpdateSerializerMixin.get_template_attr_for_account(template, True)
        self.assertNotIn('secret', attrs)
        template.get_secret.assert_not_called()
        AccountCreateUpdateSerializerMixin.get_template_attr_for_account(template, False)
        template.get_secret.assert_called_once()

    @patch('accounts.models.account.transaction.atomic', return_value=nullcontext())
    @patch('accounts.models.account.BaseAccount.save')
    def test_detach_snapshots_current_credential_before_saving(self, save, atomic):
        from accounts.models import Account
        previous = self.make_account()
        account = self.make_account(follow_template=False)
        account._state.adding = False
        template = SimpleNamespace(secret='current-template-secret', secret_has_save_to_vault=False)
        with patch.object(Account._base_manager, 'using') as manager, \
                patch.object(Account, 'get_source_template', return_value=template):
            manager.return_value.select_for_update.return_value.filter.return_value.first.return_value = previous
            account.save(update_fields=['follow_template'])
        self.assertEqual(account._secret, 'current-template-secret')
        self.assertEqual(set(save.call_args.kwargs['update_fields']), {'follow_template', '_secret'})

    @patch('accounts.models.account.transaction.atomic', return_value=nullcontext())
    @patch('accounts.models.account.BaseAccount.save')
    def test_failed_detach_read_does_not_save(self, save, atomic):
        from accounts.exceptions import VaultUnavailableException
        previous = self.make_account()
        account = self.make_account(follow_template=False)
        account._state.adding = False
        with patch.object(Account._base_manager, 'using') as manager, \
                patch.object(Account, 'get_source_template', side_effect=VaultUnavailableException()):
            manager.return_value.select_for_update.return_value.filter.return_value.first.return_value = previous
            with self.assertRaises(VaultUnavailableException):
                account.save()
        save.assert_not_called()

    @patch('accounts.models.Account.objects.filter')
    def test_followed_template_cannot_be_deleted(self, query):
        from django.db.models.deletion import ProtectedError
        from accounts.signal_handlers import protect_followed_account_template
        template = SimpleNamespace(id='template-id', org_id='org')
        query.return_value.exists.return_value = True
        with patch('orgs.utils.tmp_to_org', return_value=nullcontext()):
            with self.assertRaises(ProtectedError):
                protect_followed_account_template(None, template)

    @patch('accounts.models.template.BaseAccount.save')
    @patch('accounts.models.AccountTemplate.objects.filter')
    def test_random_template_metadata_save_does_not_regenerate(self, query, save):
        from accounts.models import AccountTemplate
        template = AccountTemplate(secret_strategy='random', name='new-name')
        template._state.adding = False
        query.return_value.first.return_value = AccountTemplate(secret_strategy='random')
        with patch.object(template, 'get_secret') as generate:
            template.save()
        generate.assert_not_called()
        save.assert_called_once()

    def test_history_records_snapshot_without_overwriting_current_field(self):
        from accounts.models.account import AccountHistoricalRecords
        from simple_history.models import HistoricalRecords
        account = self.make_account()
        template = SimpleNamespace(secret='snapshot-value', secret_has_save_to_vault=False)
        captured = []
        history = AccountHistoricalRecords()
        with patch.object(Account, 'get_source_template', return_value=template), \
                patch.object(HistoricalRecords, 'create_historical_record',
                             side_effect=lambda obj, *a, **kw: captured.append(obj._secret)):
            history.create_historical_record(account, '+')
        self.assertEqual(captured, ['snapshot-value'])
        self.assertIsNone(account._secret)

    def test_serializer_allows_credentials_when_detaching_in_same_request(self):
        account = self.make_account()
        attrs = {'follow_template': False, 'secret': 'new-user-password', 'name': 'custom'}
        self.assertEqual(FollowSerializer(instance=account).validate(attrs), attrs)

    @patch('accounts.models.account.transaction.atomic', return_value=nullcontext())
    @patch('accounts.models.account.BaseAccount.save')
    def test_detach_preserves_explicit_new_credential(self, save, atomic):
        previous = self.make_account()
        account = self.make_account(follow_template=False)
        account._state.adding = False
        account.secret = 'new-user-password'
        with patch.object(Account._base_manager, 'using') as manager, \
                patch.object(Account, 'get_source_template') as lookup:
            manager.return_value.select_for_update.return_value.filter.return_value.first.return_value = previous
            account.save(update_fields=['follow_template'])
        lookup.assert_not_called()
        self.assertEqual(account._secret, 'new-user-password')
        self.assertIn('_secret', save.call_args.kwargs['update_fields'])

    @patch('accounts.serializers.account.account.BaseAccountSerializer.update')
    def test_serializer_detaches_before_assigning_new_secret(self, update):
        account = self.make_account()
        def apply_fields(instance, attrs):
            for key, value in attrs.items():
                setattr(instance, key, value)
            return instance
        update.side_effect = apply_fields
        AccountSerializer(instance=account).update(account, {
            'secret': 'new-user-password', 'follow_template': False,
        })
        self.assertFalse(account.follow_template)
        self.assertEqual(account.secret, 'new-user-password')
