from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from terminal.models import Session


@receiver(post_save, sender=Session)
def on_session_finished(sender, instance: Session, created, **kwargs):
    if not instance.is_finished:
        return
    # 清理一次可能因 task 未执行的缓存数据
    Session.unlock_session(instance.id)
