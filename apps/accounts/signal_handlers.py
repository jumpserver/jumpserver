from collections import defaultdict

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_noop

from audits.const import ActivityAction
from audits.signal_handlers import create_activities
from common.decorators import merge_delay_run
from common.utils import get_logger, i18n_fmt
from .models import Account
from .tasks.push_account import push_accounts_to_assets_task

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_save(sender, instance, **kwargs):
    if instance.version == 0:
        instance.version = 1
    else:
        instance.version = instance.history.count()


@merge_delay_run(ttl=5)
def push_accounts_if_need(accounts=()):
    from .models import AccountTemplate

    template_accounts = defaultdict(list)
    for ac in accounts:
        # 再强调一次吧
        if ac.source != 'template':
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
        create_activities([str(template.id)], detail, task.id, ActivityAction.task, template.org_id)
        logger.debug("Push accounts to source: %s, task: %s", source_id, task)


@receiver(post_save, sender=Account)
def on_account_create_by_template(sender, instance, created=False, **kwargs):
    if not created or instance.source != 'template':
        return
    push_accounts_if_need(accounts=(instance,))
