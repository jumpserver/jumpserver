from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import LazyObject

from common.decorators import on_transaction_commit
from common.utils import get_logger
from common.utils.connection import RedisPubSub
from ..const import TaskNameType
from ..models import Task, Session
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
    if not created and instance.is_finished:
        # 当组件完成 task 时，修改 session 的 lock 状态
        session_id = instance.args
        name = instance.name
        if name == TaskNameType.lock_session:
            Session.lock_session(session_id)
        elif name == TaskNameType.unlock_session:
            Session.unlock_session(session_id)
        logger.debug(f"signal task post save: {instance.name}, "
                     f"session: {session_id}, "
                     f"is_finished: {instance.is_finished}")
        return
    event = {
        "type": instance.name,
        "payload": {
            "id": str(instance.id),
        },
    }
    component_event_chan.publish(event)
