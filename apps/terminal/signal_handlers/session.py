from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import Account
from assets.models import Asset
from common.decorators import merge_delay_run
from terminal.models import Session


@merge_delay_run(ttl=5)
def update_session_last_login_date(login_infos=()):
    account_ids = set()
    asset_ids = set()

    for account_id, asset_id in login_infos:
        if account_id:
            account_ids.add(account_id)
        if asset_id:
            asset_ids.add(asset_id)

    now = timezone.now()
    if account_ids:
        Account.objects.filter(pk__in=account_ids).update(date_last_login=now)
    if asset_ids:
        Asset.objects.filter(pk__in=asset_ids).update(date_last_login=now)


@receiver(pre_save, sender=Session)
def on_session_pre_save(sender, instance, **kwargs):
    if instance.need_update_cmd_amount:
        instance.cmd_amount = instance.compute_command_amount()

    account = instance.account_obj
    account_id = account.pk if account else None
    asset_id = instance.asset_id if instance.asset_id and instance.is_success else None
    if account_id or asset_id:
        update_session_last_login_date.delay(
            login_infos=((account_id, asset_id),)
        )


@receiver(post_save, sender=Session)
def on_session_finished(sender, instance: Session, created, **kwargs):
    if not instance.is_finished:
        return
    # 清理一次可能因 task 未执行的缓存数据
    Session.unlock_session(instance.id)
