from typing import Iterable
from collections import defaultdict
import traceback
from itertools import chain

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from .backends.wecom import WeCom
from .backends.email import Email
from .models import BACKEND, SystemMsgSubscription, UserMsgSubscription


class CATEGORY(TextChoices):
    TERMINAL = 'terminal', _('Terminal')
    OPERATIONS = 'Operations', _('Operations')


system_msgs = {}
user_msgs = {}


class MessageType(type):
    def __new__(cls, name, bases, attrs: dict):
        clz = type.__new__(cls, name, bases, attrs)

        if 'message_type_label' in attrs and 'category' in attrs:
            message_type = clz.get_message_type()

            msg = {
                'message_type': message_type,
                'message_type_label': attrs['message_type_label'],
                'category': attrs['category']
            }
            if issubclass(clz, SystemMsgSubscription):
                system_msgs[message_type] = msg
            elif issubclass(clz, UserMsgSubscription):
                user_msgs[message_type] = msg

        return clz


class Message(metaclass=MessageType):
    """
    这里封装了什么？
        封装不同消息的模板，提供统一的发送消息的接口
        - publish 该方法的实现与消息订阅的表结构有关
        - send_msg
    """

    message_type_label: str
    category: CATEGORY

    @classmethod
    def get_message_type(cls):
        return cls.__name__

    def publish(self):
        raise NotImplementedError

    def send_msg(self, users: Iterable, backends: Iterable = BACKEND):
        for backend in backends:
            try:
                backend = BACKEND(backend)

                get_msg_method = getattr(self, f'get_{backend}_msg', self.get_default_msg)
                msg = get_msg_method()
                client = backend.client()

                if isinstance(msg, dict):
                    client.send_msg(users, **msg)
                else:
                    client.send_msg(users, msg)
            except:
                traceback.print_exc()

    def get_default_msg(self) -> str:
        pass

    def get_wecom_msg(self) -> str:
        raise NotImplementedError

    def get_email_msg(self) -> dict:
        raise NotImplementedError


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


class UserMessage(Message):
    pass
