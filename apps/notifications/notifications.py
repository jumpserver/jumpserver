import textwrap
import traceback
from itertools import chain
from typing import Iterable

from celery import shared_task
from django.utils.translation import gettext_lazy as _
from html2text import HTML2Text

from common.utils import lazyproperty
from common.utils.timezone import local_now
from notifications.backends import BACKEND
from settings.utils import get_login_title
from users.models import User
from .models import SystemMsgSubscription, UserMsgSubscription

__all__ = ('SystemMessage', 'UserMessage', 'system_msgs', 'Message')

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


@shared_task(verbose_name=_('Publish the station message'))
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
    text_msg_ignore_links = True

    @classmethod
    def get_message_type(cls):
        return cls.__name__

    def publish_async(self):
        return publish_task.delay(self)

    @classmethod
    def gen_test_msg(cls):
        raise NotImplementedError

    def publish(self):
        raise NotImplementedError

    def send_msg(self, users: Iterable, backends: Iterable = BACKEND):
        backends = set(backends)
        backends.add(BACKEND.SITE_MSG)  # 站内信必须发

        for backend in backends:
            try:
                backend = BACKEND(backend)
                if not backend.is_enable:
                    continue
                get_msg_method = getattr(self, f'get_{backend}_msg', self.get_common_msg)
                msg = get_msg_method()
                client = backend.client()
                client.send_msg(users, **msg)
            except NotImplementedError:
                continue
            except:
                traceback.print_exc()

    @classmethod
    def send_test_msg(cls, ding=True, wecom=False):
        msg = cls.gen_test_msg()
        if not msg:
            return

        from users.models import User
        users = User.objects.filter(username='admin')
        backends = []
        if ding:
            backends.append(BACKEND.DINGTALK)
        if wecom:
            backends.append(BACKEND.WECOM)
        msg.send_msg(users, backends)

    @staticmethod
    def get_common_msg() -> dict:
        return {'subject': '', 'message': ''}

    def get_html_msg(self) -> dict:
        return self.get_common_msg()

    def get_markdown_msg(self) -> dict:
        h = HTML2Text()
        h.body_width = 300
        msg = self.get_html_msg()
        content = msg['message']
        msg['message'] = h.handle(content)
        return msg

    def get_text_msg(self) -> dict:
        h = HTML2Text()
        h.body_width = 90
        msg = self.get_html_msg()
        content = msg['message']
        h.ignore_links = self.text_msg_ignore_links
        msg['message'] = h.handle(content)
        return msg

    @lazyproperty
    def common_msg(self) -> dict:
        return self.get_common_msg()

    @lazyproperty
    def text_msg(self) -> dict:
        msg = self.get_text_msg()
        return msg

    @lazyproperty
    def markdown_msg(self):
        return self.get_markdown_msg()

    @lazyproperty
    def html_msg(self) -> dict:
        msg = self.get_html_msg()
        return msg

    @lazyproperty
    def html_msg_with_sign(self):
        msg = self.get_html_msg()
        msg['message'] = textwrap.dedent("""
        {}
        <small>
        <br />
        —
        <br />
        {}
        </small>
        """).format(msg['message'], self.signature)
        return msg

    @lazyproperty
    def text_msg_with_sign(self):
        msg = self.get_text_msg()
        msg['message'] = textwrap.dedent("""
        {}
        —
        {}
        """).format(msg['message'], self.signature)
        return msg

    @lazyproperty
    def signature(self):
        return get_login_title()

    # --------------------------------------------------------------
    # 支持不同发送消息的方式定义自己的消息内容，比如有些支持 html 标签
    def get_dingtalk_msg(self) -> dict:
        # 钉钉相同的消息一天只能发一次，所以给所有消息添加基于时间的序号，使他们不相同
        message = self.markdown_msg['message']
        time = local_now().strftime('%Y-%m-%d %H:%M:%S')
        suffix = '\n{}: {}'.format(_('Time'), time)

        return {
            'subject': self.markdown_msg['subject'],
            'message': message + suffix
        }

    def get_wecom_msg(self) -> dict:
        return self.markdown_msg

    def get_feishu_msg(self) -> dict:
        return self.markdown_msg

    def get_email_msg(self) -> dict:
        return self.html_msg_with_sign

    def get_site_msg_msg(self) -> dict:
        return self.html_msg

    def get_slack_msg(self) -> dict:
        return self.markdown_msg

    def get_sms_msg(self) -> dict:
        return self.text_msg_with_sign

    @classmethod
    def get_all_sub_messages(cls):
        def get_subclasses(cls):
            """returns all subclasses of argument, cls"""
            if issubclass(cls, type):
                subclasses = cls.__subclasses__(cls)
            else:
                subclasses = cls.__subclasses__()
            for subclass in subclasses:
                subclasses.extend(get_subclasses(subclass))
            return subclasses

        messages_cls = get_subclasses(cls)
        return messages_cls

    @classmethod
    def test_all_messages(cls, ding=True, wecom=False):
        messages_cls = cls.get_all_sub_messages()

        for _cls in messages_cls:
            try:
                _cls.send_test_msg(ding=ding, wecom=wecom)
            except NotImplementedError:
                continue


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

    @classmethod
    def gen_test_msg(cls):
        raise NotImplementedError


class UserMessage(Message):
    user: User

    def __init__(self, user):
        self.user = user

    def publish(self):
        """
        发送消息到每个用户配置的接收方式上
        """
        sub = UserMsgSubscription.objects.get(user=self.user)
        self.send_msg([self.user], sub.receive_backends)

    @classmethod
    def get_test_user(cls):
        from users.models import User
        return User.objects.all().first()

    @classmethod
    def gen_test_msg(cls):
        raise NotImplementedError
