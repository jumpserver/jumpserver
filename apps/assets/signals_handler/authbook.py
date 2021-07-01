from django.dispatch import receiver
from django.apps import apps
from simple_history.signals import pre_create_historical_record
from django.db.models.signals import post_save, pre_save

from ..models import AuthBook

AuthBookHistory = apps.get_model('assets', 'HistoricalAuthBook')


@receiver(pre_create_historical_record, sender=AuthBookHistory)
def pre_create_historical_record_callback(sender, instance=None, history_instance=None, **kwargs):
    attrs_to_copy = ['username', 'password', 'private_key']

    for attr in attrs_to_copy:
        if getattr(history_instance, attr):
            continue
        if not history_instance.systemuser:
            continue
        system_user_attr_value = getattr(history_instance.systemuser, attr)
        if system_user_attr_value:
            setattr(history_instance, attr, system_user_attr_value)


@receiver(pre_save, sender=AuthBook)
def on_authbook_create_update_version(sender, instance, **kwargs):
    instance.version = instance.history.all().count()
