from importlib import import_module
import inspect

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.db.transaction import atomic

from .notification import MessageBase
from .models import Subscription
from common.utils import get_logger

logger = get_logger(__file__)


@receiver(post_migrate, dispatch_uid='notifications.signals_handler.create_notifications_type')
def create_notifications_type(app_config, **kwargs):
    package = app_config.module.__package__
    notifications_module_name = '.notifications'

    try:
        with atomic():
            notifications_module = import_module(notifications_module_name, package)
            app_label = app_config.label

            searched_msgs = set()

            # 禁用所有
            Subscription.objects.filter(app=app_label).update(is_valid=False)
            all_msgs_category_pairs = Subscription.objects.filter(app=app_label).values_list(
                'message_type', 'message_category'
            )
            all_msgs_category_mapper = dict(all_msgs_category_pairs)

            for attr in dir(notifications_module):
                if attr.startswith('_'):
                    continue

                MsgClass = getattr(notifications_module, attr)
                if not inspect.isclass(MsgClass):
                    continue

                if MsgClass is MessageBase:
                    continue

                if issubclass(MsgClass, MessageBase):
                    msg_type = MsgClass.get_message_type()
                    msg_category = MsgClass.category
                    searched_msgs.add(msg_type)

                    if msg_type not in all_msgs_category_mapper:
                        sub = Subscription.objects.create(
                            app=app_label, message_type=msg_type, message_category=msg_category
                        )
                        logger.debug(f'Create messages {sub}')
                        MsgClass.post_insert_to_db(sub)
                    elif all_msgs_category_mapper[msg_type] != MsgClass.category:
                        # 修改了消息的类别，更新数据库
                        Subscription.objects.filter(
                            message_type=msg_type
                        ).update(
                            message_category=MsgClass.category
                        )

            # 启用当前定义的
            Subscription.objects.filter(app=app_label, message_type__in=searched_msgs).update(is_valid=True)
    except ModuleNotFoundError:
        return
