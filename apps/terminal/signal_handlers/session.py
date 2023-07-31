from django.db.models.signals import pre_save
from django.dispatch import receiver

from terminal.models import Session


@receiver(pre_save, sender=Session)
def on_session_pre_save(sender, instance, **kwargs):
    if instance.is_finished:
        instance.cmd_amount = instance.compute_command_amount()
