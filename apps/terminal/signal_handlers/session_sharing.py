from django.db.models.signals import post_save
from django.dispatch import receiver

from terminal.models import SessionSharing
from terminal.notifications import SessionSharingMessage


@receiver(post_save, sender=SessionSharing)
def on_session_sharing_created(sender, instance: SessionSharing, created, **kwargs):
    if not created:
        return
    for user in instance.users_queryset:
        SessionSharingMessage(user, instance).publish_async()
