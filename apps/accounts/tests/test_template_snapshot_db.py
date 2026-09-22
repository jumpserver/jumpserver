"""Stored-template credential lifecycle against an isolated in-memory database."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from django.db import connections
from django.test import override_settings

from accounts.models import Account, AccountTemplate
from accounts.tasks.template import template_sync_related_accounts, TemplateCredentialSyncError
from orgs.utils import tmp_to_root_org


ALIAS = 'template_snapshot_tests'


class SnapshotRouter:
    def db_for_read(self, model, **hints):
        return ALIAS if model._meta.app_label == 'accounts' else None

    db_for_write = db_for_read

    def allow_relation(self, obj1, obj2, **hints):
        return True


class MemoryVault:
    def __init__(self):
        self.entries = {}
        self.fail_ids = set()

    def key(self, obj):
        return obj._meta.model_name, str(obj.pk)

    def get(self, obj):
        return self.entries.get(self.key(obj))

    def get_for_restore(self, obj):
        if self.key(obj) not in self.entries:
            from accounts.exceptions import VaultSecretNotFoundException
            raise VaultSecretNotFoundException()
        return self.get(obj)

    def write(self, obj):
        if obj.secret_has_save_to_vault:
            return
        if str(obj.pk) in self.fail_ids:
            raise RuntimeError('simulated vault write failure')
        self.entries[self.key(obj)] = obj._secret
        obj.mark_secret_save_to_vault()

    create = update = write

    def delete(self, obj):
        self.entries.pop(self.key(obj), None)


class TemplateSnapshotDatabaseTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        config = deepcopy(connections.databases['default'])
        config.update(ENGINE='django.db.backends.sqlite3', NAME=':memory:', OPTIONS={}, ATOMIC_REQUESTS=False)
        connections.databases[ALIAS] = config
        cls.settings = override_settings(DATABASE_ROUTERS=[SnapshotRouter()])
        cls.settings.enable()
        conn = connections[ALIAS]
        conn.disable_constraint_checking()
        with conn.schema_editor() as editor:
            for model in (AccountTemplate, Account, Account.history.model):
                editor.create_model(model)
        conn.disable_constraint_checking()

    @classmethod
    def tearDownClass(cls):
        connections[ALIAS].close()
        cls.settings.disable()
        del connections[ALIAS]
        del connections.databases[ALIAS]
        super().tearDownClass()

    def setUp(self):
        self.org = tmp_to_root_org()
        self.org.__enter__()
        self.addCleanup(self.org.__exit__, None, None, None)
        self.vault = MemoryVault()
        self.patches = [
            patch('accounts.backends.vault_client', self.vault),
            patch('accounts.signal_handlers.vault_client', self.vault),
            patch('accounts.signal_handlers.push_accounts_if_need.delay'),
            patch('accounts.signal_handlers.create_accounts_activities'),
            patch('accounts.tasks.template.template_sync_related_accounts.delay'),
        ]
        for patcher in self.patches:
            started = patcher.start()
            self.addCleanup(patcher.stop)
        self.enqueue = started
        import uuid
        self.template = AccountTemplate.objects.create(name=str(uuid.uuid4()), username='user', secret='first', org_id='00000000-0000-0000-0000-000000000002')
        self.account = Account.objects.create(
            name=str(uuid.uuid4()), username='user', asset_id=uuid.uuid4(),
            source='template', source_id=str(self.template.pk), follow_template=True, org_id=self.template.org_id,
        )

    def fresh(self):
        return Account.objects.get(pk=self.account.pk)

    def test_template_changes_are_eventually_copied_with_history(self):
        self.assertEqual(self.fresh().secret, 'first')
        self.assertTrue(self.fresh().secret_has_save_to_vault)
        self.template.secret = 'second'
        self.template.save()
        self.enqueue.assert_called_once_with(str(self.template.pk))
        self.assertEqual(self.fresh().secret, 'first')
        template_sync_related_accounts.run(str(self.template.pk))
        self.assertEqual(self.fresh().secret, 'second')
        self.assertTrue(self.fresh().follow_template)
        history_count = self.fresh().history.count()
        self.assertGreaterEqual(history_count, 2)
        template_sync_related_accounts.run(str(self.template.pk))
        self.assertEqual(self.fresh().history.count(), history_count)

    def test_detach_keeps_account_copy_and_opt_in_replaces_it(self):
        self.template.secret = 'second'
        self.template.save()
        account = self.fresh()
        account.follow_template = False
        account.save(update_fields=['follow_template'])
        self.assertEqual(self.fresh().secret, 'first')
        template_sync_related_accounts.run(str(self.template.pk))
        self.assertEqual(self.fresh().secret, 'first')
        account = self.fresh()
        account.follow_template = True
        account.save(update_fields=['follow_template'])
        self.assertEqual(self.fresh().secret, 'second')

    def test_filtered_queryset_clear_updates_vault_and_follow_state(self):
        Account.objects.filter(pk=self.account.pk, follow_template=True).update(secret=None, follow_template=False)
        self.assertFalse(self.fresh().follow_template)
        self.assertIsNone(self.fresh().secret)
        self.assertIsNone(self.vault.entries[self.vault.key(self.account)])

    def test_sync_failure_keeps_old_copy_and_can_retry(self):
        self.template.secret = 'second'
        self.template.save()
        self.vault.fail_ids.add(str(self.account.pk))
        with self.assertRaises(TemplateCredentialSyncError):
            template_sync_related_accounts.run(str(self.template.pk))
        self.assertEqual(self.fresh().secret, 'first')
        self.assertTrue(self.fresh().follow_template)
        self.vault.fail_ids.clear()
        template_sync_related_accounts.run(str(self.template.pk))
        self.assertEqual(self.fresh().secret, 'second')

    def test_opt_in_vault_failure_rolls_back_follow_state(self):
        Account.objects.filter(pk=self.account.pk).update(follow_template=False)
        self.template.secret = 'second'
        self.template.save()
        account = self.fresh()
        account.follow_template = True
        self.vault.fail_ids.add(str(account.pk))
        from accounts.exceptions import VaultException
        with self.assertRaises(VaultException):
            account.save(update_fields=['follow_template'])
        self.assertFalse(self.fresh().follow_template)
        self.assertEqual(self.fresh().secret, 'first')

    def test_metadata_edits_do_not_schedule_credential_sync(self):
        self.template.name += '-renamed'
        self.template.privileged = True
        self.template.save()
        self.enqueue.assert_not_called()

    def test_legacy_followers_can_initialize_missing_vault_entries(self):
        with connections[ALIAS].cursor() as cursor:
            cursor.execute('UPDATE accounts_account SET _secret = NULL WHERE id = %s', [self.account.pk.hex])
        self.vault.entries.pop(self.vault.key(self.account))
        template_sync_related_accounts.run(str(self.template.pk), initialize=True)
        self.assertEqual(self.fresh().secret, 'first')
        self.assertTrue(self.fresh().secret_has_save_to_vault)

    def test_bulk_update_cannot_enable_following_without_copying(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            Account.objects.filter(pk=self.account.pk).update(follow_template=True)

    def test_opt_in_requires_saving_follow_state_with_the_copy(self):
        Account.objects.filter(pk=self.account.pk).update(follow_template=False)
        account = self.fresh()
        account.follow_template = True
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            account.save(update_fields=['name'])
        self.assertFalse(self.fresh().follow_template)

    def test_template_sync_is_not_enqueued_when_transaction_rolls_back(self):
        from django.db import transaction
        with self.assertRaises(RuntimeError):
            with transaction.atomic(using=ALIAS):
                self.template.secret = 'second'
                self.template.save()
                raise RuntimeError('abort transaction')
        self.enqueue.assert_not_called()
