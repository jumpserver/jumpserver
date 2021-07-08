from typing import Iterable
import traceback
from itertools import chain

from django.db.utils import ProgrammingError
from celery import shared_task

from notifications.backends import BACKEND
from .models import SystemMsgSubscription

__all__ = ('SystemMessage', 'UserMessage')


system_msgs = []
user_msgs = []


class MessageType(type):
    def __new__(cls, name, bases, attrs: dict):
        clz = type.__new__(cls, name, bases, attrs)

        if 'message_type_label' in attrs \
                and 'category' in attrs \
                and 'category_label' in attrs:
            message_type = clz.get_message_type()

            msg = {
                'message_type': message_type,
                'message_type_label': attrs['message_type_label'],
                'category': attrs['category'],
                'category_label': attrs['category_label'],
            }
            if issubclass(clz, SystemMessage):
                system_msgs.append(msg)
            elif issubclass(clz, UserMessage):
                user_msgs.append(msg)

        return clz


@shared_task
def publish_task(msg):
    msg.publish()


class Message(metaclass=MessageType):
    """
    这里封装了什么？
        封装不同消息的模板，提供统一的发送消息的接口
        - publish 该方法的实现与消息订阅的表结构有关
        - send_msg
    """

    message_type_label: str
    category: str
    category_label: str

    @classmethod
    def get_message_type(cls):
        return cls.__name__

    def publish_async(self):
        return publish_task.delay(self)

    def publish(self):
        raise NotImplementedError

    def send_msg(self, users: Iterable, backends: Iterable = BACKEND):
        for backend in backends:
            try:
                backend = BACKEND(backend)

                get_msg_method = getattr(self, f'get_{backend}_msg', self.get_common_msg)
                msg = get_msg_method()
                client = backend.client()

                if isinstance(msg, dict):
                    client.send_msg(users, **msg)
                else:
                    client.send_msg(users, msg)
            except:
                traceback.print_exc()

    def get_common_msg(self) -> str:
        raise NotImplementedError

    def get_dingtalk_msg(self) -> str:
        return self.get_common_msg()

    def get_wecom_msg(self) -> str:
        return self.get_common_msg()

    def get_email_msg(self) -> dict:
        msg = self.get_common_msg()
        return {
            'subject': msg,
            'message': msg
        }

    def get_site_msg_msg(self) -> dict:
        return self.get_email_msg()


class SystemMessage(Message):
    def publish(self):
        subscription = SystemMsgSubscription.objects.get(
            message_type=self.get_message_type()
        )

        # 只发送当前有效后端
        receive_backends = subscription.receive_backends
        receive_backends = BACKEND.filter_enable_backends(receive_backends)

        users = [
            *subscription.users.all(),
            *chain(*[g.users.all() for g in subscription.groups.all()])
        ]

        self.send_msg(users, receive_backends)

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        pass


class UserMessage(Message):
    pass
