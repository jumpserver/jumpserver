from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from terminal.models import SessionSharing
from users.models import User
from orgs.utils import tmp_to_root_org
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


@receiver(pre_delete, sender=User)
def disable_deleted_user_shares(sender, instance, using, **kwargs):
    # Include shares in every organization, also for queryset/bulk user deletion.
    with tmp_to_root_org():
        SessionSharing.objects.using(using).filter(creator_id=instance.pk).update(is_active=False)
