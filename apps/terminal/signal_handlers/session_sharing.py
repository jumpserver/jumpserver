from django.db.models.signals import post_save
from django.dispatch import receiver

from terminal.models import SessionSharing
from terminal.notifications import SessionSharingMessage
from terminal.session_lifecycle import UserCreateShareLink


@receiver(post_save, sender=SessionSharing)
def on_session_sharing_created(sender, instance: SessionSharing, created, **kwargs):
    if not created:
        return
    for user in instance.users_queryset:
        SessionSharingMessage(user, instance).publish_async()

    # 创建会话分享活动日志
    session = instance.session
    UserCreateShareLink(session, None).create_activity_log()
