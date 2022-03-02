from django.db.models.signals import pre_save
from django.dispatch import receiver

from ..models import Comment


@receiver(pre_save, sender=Comment)
def on_comment_pre_save(sender, instance, **kwargs):
    instance.set_display_fields()
