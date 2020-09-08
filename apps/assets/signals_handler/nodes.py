from django.db.models.signals import post_delete
from django.dispatch import receiver

from ..models import Node


@receiver(post_delete, sender=Node)
def on_node_delete(sender, instance):
    # Todo: 修正资产数量和用户树
    raise NotImplementedError
