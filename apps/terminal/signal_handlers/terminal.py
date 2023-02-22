from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import LazyObject

from common.decorators import on_transaction_commit
from common.utils import get_logger
from common.utils.connection import RedisPubSub
from ..models import Task
from ..utils import DBPortManager

db_port_manager: DBPortManager

logger = get_logger(__file__)


class ComponentEventChan(LazyObject):
    def _setup(self):
        self._wrapped = RedisPubSub('fm.component_event_chan')


component_event_chan = ComponentEventChan()


@receiver(post_save, sender=Task)
@on_transaction_commit
def on_task_created(sender, instance: Task, created, **kwargs):
    if not created:
        return
    event = {
        "type": instance.name,
        "payload": {
            "id": str(instance.id),
        },
    }
    component_event_chan.publish(event)
