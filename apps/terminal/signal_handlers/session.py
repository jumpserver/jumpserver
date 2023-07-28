from django.db.models.signals import pre_save
from django.dispatch import receiver

from terminal.models import Session, Command


@receiver(pre_save, sender=Session)
def on_session_pre_save(sender, instance, **kwargs):
    if instance.is_finished:
        cmd_amount = Command.objects.filter(session=instance.id).count()
        instance.cmd_amount = cmd_amount
