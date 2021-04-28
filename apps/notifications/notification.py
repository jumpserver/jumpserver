from typing import Iterable
from collections import defaultdict
import traceback

from celery import shared_task

from .models import Subscription, Backend

BACKEND = Backend.BACKEND


@shared_task
def publish_task(note, data):
    note.publish(**data)


class MessageBase:
    app_label: str
    message_label: str

    @property
    def message(self):
        return self.__class__.__name__

    @classmethod
    def publish_async(cls, **data):
        publish_task.delay(cls, data)

    @classmethod
    def publish(cls, **data):
        backend_user_mapper = defaultdict(list)
        subscriptions = Subscription.objects.filter(
            messages__app=cls.app_label,
            messages__message=cls.__name__,
        ).distinct().prefetch_related('users', 'groups__users', 'receive_backends')

        for subscription in subscriptions:
            for backend in subscription.receive_backends.all():
                backend_user_mapper[backend.name].extend(subscription.users.all())

                for group in subscription.groups.all():
                    backend_user_mapper[backend.name].extend(group.users.all())

        client = cls()
        for backend, users in backend_user_mapper.items():
            try:
                client.send_msg(data, users, [backend])
            except Exception:
                traceback.print_exc()

    def send_msg(self, data: dict, users: Iterable, backends: Iterable = BACKEND):
        for backend in backends:
            backend = BACKEND(backend)

            get_msg_method_name = f'get_{backend}_msg'
            get_msg_method = getattr(self, get_msg_method_name)
            msg = get_msg_method(**data)
            client = backend.client()

            if isinstance(msg, dict):
                client.send_msg(users, **msg)
            else:
                client.send_msg(users, msg)

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
