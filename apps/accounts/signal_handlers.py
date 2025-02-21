from collections import defaultdict

from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import LazyObject
from django.utils.translation import gettext_noop

from accounts.backends import vault_client, refresh_vault_client
from accounts.const import Source
from audits.const import ActivityChoices
from audits.signal_handlers import create_activities
from common.decorators import merge_delay_run
from common.signals import django_ready
from common.utils import get_logger, i18n_fmt
from common.utils.connection import RedisPubSub
from .exceptions import VaultException
from .models import Account, AccountTemplate
from .tasks.push_account import push_accounts_to_assets_task

logger = get_logger(__name__)


<<<<<<< HEAD
@receiver(pre_save, sender=Account)
def on_account_pre_save(sender, instance, **kwargs):
    if getattr(instance, 'skip_history_when_saving', False):
        return

    if instance.version == 0:
        instance.version = 1
    else:
        history_account = instance.history.first()
        instance.version = history_account.version + 1 if history_account else 0


=======
>>>>>>> pam
@merge_delay_run(ttl=5)
def push_accounts_if_need(accounts=()):
    from .models import AccountTemplate

    template_accounts = defaultdict(list)
    for ac in accounts:
        # 再强调一次吧
        if ac.source != Source.TEMPLATE:
            continue
        template_accounts[ac.source_id].append(ac)

    for source_id, accounts in template_accounts.items():
        template = AccountTemplate.objects.filter(id=source_id).first()
        if not template or not template.auto_push:
            continue
        logger.debug("Push accounts to source: %s", source_id)
        account_ids = [str(ac.id) for ac in accounts]
        task = push_accounts_to_assets_task.delay(account_ids, params=template.push_params)
        detail = i18n_fmt(
            gettext_noop('Push related accounts to assets: %s, by system'),
            len(account_ids)
        )
        create_activities([str(template.id)], detail, task.id, ActivityChoices.task, template.org_id)
        logger.debug("Push accounts to source: %s, task: %s", source_id, task)


def create_accounts_activities(account, action='create'):
    if action == 'create':
        detail = i18n_fmt(gettext_noop('Add account: %s'), str(account))
    else:
        detail = i18n_fmt(gettext_noop('Delete account: %s'), str(account))
    create_activities([account.asset_id], detail, None, ActivityChoices.operate_log, account.org_id)


@receiver(post_save, sender=Account)
def on_account_create_by_template(sender, instance, created=False, **kwargs):
    if not created:
        return
    push_accounts_if_need.delay(accounts=(instance,))
    create_accounts_activities(instance, action='create')


@receiver(post_delete, sender=Account)
def on_account_delete(sender, instance, **kwargs):
    create_accounts_activities(instance, action='delete')


class VaultSignalHandler(object):
    """ 处理 Vault 相关的信号 """

    @staticmethod
    def save_to_vault(sender, instance, created, **kwargs):
        try:
            if created:
                vault_client.create(instance)
            else:
                vault_client.update(instance)
        except Exception as e:
            logger.error('Vault save failed: {}'.format(e))
            raise VaultException()

    @staticmethod
    def delete_to_vault(sender, instance, **kwargs):
        try:
            vault_client.delete(instance)
        except Exception as e:
            logger.error('Vault delete failed: {}'.format(e))
            raise VaultException()


for model in (Account, AccountTemplate, Account.history.model):
    post_save.connect(VaultSignalHandler.save_to_vault, sender=model)
    post_delete.connect(VaultSignalHandler.delete_to_vault, sender=model)


class VaultPubSub(LazyObject):
    def _setup(self):
        self._wrapped = RedisPubSub('refresh_vault')


vault_pub_sub = VaultPubSub()


@receiver(django_ready)
def subscribe_vault_change(sender, **kwargs):
    logger.debug("Start subscribe vault change")

    vault_pub_sub.subscribe(lambda name: refresh_vault_client())
