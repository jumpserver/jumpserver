from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from common.utils.verify_hmac import hmac_handler
from terminal.models import Session


@receiver(pre_save, sender=Session)
def on_session_pre_save(sender, instance, **kwargs):
    if instance.need_update_cmd_amount:
        instance.cmd_amount = instance.compute_command_amount()
    if instance.account_obj:
        instance.account_obj.update_last_login_date()


@receiver(post_save, sender=Session)
def on_session_finished(sender, instance: Session, created, **kwargs):
    if not instance.is_finished:
        return
    # 清理一次可能因 task 未执行的缓存数据
    Session.unlock_session(instance.id)


@receiver(post_save, sender=Session)
def on_session_created_hmac(sender, instance: Session, created, **kwargs):
    if not created or not hmac_handler.enable:
        return
    from terminal.models import SessionHmac
    hmac_handler.create_hmac_record(SessionHmac, instance.id, instance)
