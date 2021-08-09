from itertools import chain
from typing import Iterable
from collections import defaultdict
import traceback

from celery import shared_task

from .models import Backend, Message

BACKEND = Backend.BACKEND


@shared_task
def publish_task(note, data):
    note.publish(**data)


class MessageBase:
    message_label: str

    @property
    def message(self):
        return self.__class__.__name__

    @classmethod
    def publish_async(cls, **data):
        publish_task.delay(cls, data)

    @classmethod
    def publish(cls, **data):
        msg = Message.objects.get(message=cls.__name__)

        if not msg:
            return

        backend_names = [b.name for b in msg.receive_backends.all()]
        users = [
            *msg.users.all(),
            *chain(*[g.users.all() for g in msg.groups.all()])
        ]

        client = cls()
        client.send_msg(data, users, backend_names)

    def send_msg(self, data: dict, users: Iterable, backends: Iterable = BACKEND):
        for backend in backends:
            try:
                backend = BACKEND(backend)

                get_msg_method_name = f'get_{backend}_msg'
                get_msg_method = getattr(self, get_msg_method_name)
                msg = get_msg_method(**data)
                client = backend.client()

                if isinstance(msg, dict):
                    client.send_msg(users, **msg)
                else:
                    client.send_msg(users, msg)
            except:
                traceback.print_exc()

    def get_common_msg(self, **data):
        raise NotImplementedError

    def get_wecom_msg(self, **data):
        return self.get_common_msg(**data)

    def get_dingtalk_msg(self, **data):
        return self.get_common_msg(**data)

    def get_email_msg(self, **data):
        msg = self.get_common_msg(**data)
        return {
            'subject': msg,
            'message': msg
        }
