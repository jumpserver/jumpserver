from django.db.models.signals import pre_save
from django.dispatch import receiver

from terminal.models import Session


@receiver(pre_save, sender=Session)
def on_session_pre_save(sender, instance, update_fields, **kwargs):
    update_fields = update_fields or []
    if instance.is_finished or 'cmd_amount' in update_fields:
        instance.cmd_amount = instance.compute_command_amount()
