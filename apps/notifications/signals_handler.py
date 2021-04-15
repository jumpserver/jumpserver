from importlib import import_module

from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .notification import MessageBase
from .models import Message, Backend


@receiver(post_migrate, dispatch_uid='notifications.signals_handler.create_notifications_type')
def create_notifications_type(app_config, **kwargs):
    package = app_config.module.__package__
    notifications_module_name = '.notifications'

    try:
        notifications_module = import_module(notifications_module_name, package)
        app_label = app_config.label

        searched_msgs = set()
        all_msgs = set(Message.objects.filter(app=app_label).values_list('message', flat=True))

        for attr in dir(notifications_module):
            if attr.startswith('_'):
                continue

            obj = getattr(notifications_module, attr)

            if obj is MessageBase:
                continue

            if issubclass(obj, MessageBase):
                searched_msgs.add(obj.__name__)

        msgs = searched_msgs - all_msgs
        msgs = [Message(app=app_label, message=m) for m in msgs]
        Message.objects.bulk_create(msgs)

    except ModuleNotFoundError:
        return


@receiver(post_migrate, dispatch_uid='notifications.signals_handler.create_notifications_backend')
def create_notifications_backend(app_config, **kwargs):
    app_label = app_config.label

    if app_label != 'notifications':
        return

    searched_backends = [b for b in Backend.BACKEND]
    all_backends = set(Backend.objects.all().values_list('name', flat=True))

    backends = set(searched_backends) - all_backends

    to_create = []
    for b in searched_backends:
        if b in backends:
            to_create.append(Backend(name=b))
    Backend.objects.bulk_create(to_create)
