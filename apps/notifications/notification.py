from typing import Iterable
from collections import defaultdict

from celery import shared_task

from .models import Subscription, Backend

BACKEND = Backend.BACKEND


class UserAccountUtils:
    def __init__(self, users):
        self._users = users

    def get_users(self, backend_name):
        method_name = f'get_{backend_name}_accounts'
        method = getattr(self, method_name)
        return method()

    def get_wecom_accounts(self):
        return self.get_accounts_on_model_fields('wecom_id')

    def get_accounts_on_model_fields(self, field_name):
        accounts = []
        unbound_users = []
        account_user_mapper = {}

        for user in self._users:
            account = getattr(user, field_name, None)
            if account:
                account_user_mapper[account] = user
                accounts.append(account)
            else:
                unbound_users.append(user)
        return accounts, unbound_users, account_user_mapper

    def get_email_accounts(self):
        return self.get_accounts_on_model_fields('email')


@shared_task
def publish_task(note, data):
    note.publish(**data)


class NoteBase:
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
            messages__message=cls.message,
        ).distinct().prefetch_related('users', 'groups__users', 'receive_backends')

        for subscription in subscriptions:
            for backend in subscription.receive_backends.all():
                backend_user_mapper[backend.name].extend(subscription.users.all())

                for group in subscription.groups.all():
                    backend_user_mapper[backend.name].extend(group.users.all())

        client = cls()
        for backend, users in backend_user_mapper.items():
            client.send_msg(data, users, [backend])

    def send_msg(self, data: dict, users: Iterable, backends: Iterable = BACKEND):
        user_utils = UserAccountUtils(users)
        failed_users_mapper = defaultdict(list)

        for backend in backends:
            backend = BACKEND(backend)

            user_accounts, invalid_users, account_user_mapper = user_utils.get_users(backend)
            get_msg_method_name = f'get_{backend}_msg'
            get_msg_method = getattr(self, get_msg_method_name)
            msg = get_msg_method(**data)
            client = backend.client()

            if isinstance(msg, dict):
                failed_users = client.send_msg(user_accounts, **msg)
            else:
                failed_users = client.send_msg(user_accounts, msg)

            for u in failed_users:
                invalid_users.append(account_user_mapper[u])

            failed_users_mapper[backend] = invalid_users

        return failed_users_mapper

    def get_common_msg(self, **data):
        raise NotImplementedError

    def get_wecom_msg(self, **data):
        return self.get_common_msg(**data)

    def get_email_msg(self, **data):
        msg = self.get_common_msg(**data)
        return {
            'subject': msg,
            'message': msg
        }
