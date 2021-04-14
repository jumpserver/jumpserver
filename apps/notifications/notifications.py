from typing import Iterable
from collections import defaultdict

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from .backends.wecom import WeCom
from .backends.email import Email
from .models import Subscription


class Backends(TextChoices):
    WECOM = 'wecom', _('WeCom')
    EMAIL = 'email', _('Email')

    client_mapper = {
        WECOM: WeCom,
        EMAIL: Email
    }

    @property
    def client(self):
        client = self.client_mapper[self]
        return client


class UserUtils:
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


messages = defaultdict(list)


class MessageType(type):
    def __new__(cls, name, bases, attrs: dict):
        if 'app_name' in attrs and 'message' in attrs:
            app_name = attrs['app_name']
            message = attrs['message']
            messages[app_name].append(message)
        clz = type.__new__(cls, name, bases, attrs)
        return clz


class Message(metaclass=MessageType):

    app_name: str
    message: str

    def publish(self, data: dict):
        backend_user_mapper = defaultdict(list)
        subscriptions = Subscription.objects.filter(
            app_name=self.app_name,
            message=self.message
        ).prefetch_related('users', 'groups__users')

        for subscription in subscriptions:
            for backend in subscription.receive_backends:
                backend_user_mapper[backend].extend(subscription.users.all())
                backend_user_mapper[backend].extend(subscription.groups.all())

        for backend, users in backend_user_mapper.items():
            self.send_msg(data, users, [backend])

    def send_msg(self, data: dict, users: Iterable, backends: Iterable = Backends):
        user_utils = UserUtils(users)
        failed_users_mapper = defaultdict(list)

        for backend in backends:
            backend = Backends(backend)

            user_accounts, invalid_users, account_user_mapper = user_utils.get_users(backend)
            get_msg_method_name = f'get_{backend}_msg'
            get_msg_method = getattr(self, get_msg_method_name, self.get_default_msg)
            msg = get_msg_method(data)
            client = backend.client()
            failed_users = client.send_msg(user_accounts, **msg)

            for u in failed_users:
                invalid_users.append(account_user_mapper[u])

            failed_users_mapper[backend] = invalid_users

        return failed_users_mapper

    def get_default_msg(self, data):
        pass

    def get_wecom_msg(self, data):
        raise NotImplementedError

    def get_email_msg(self, data):
        raise NotImplementedError
