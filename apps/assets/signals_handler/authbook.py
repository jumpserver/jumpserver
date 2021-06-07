from django.dispatch import receiver
from django.apps import apps
from simple_history.signals import pre_create_historical_record

AuthBookHistory = apps.get_model('assets', 'HistoricalAuthBook')


@receiver(pre_create_historical_record, sender=AuthBookHistory)
def pre_create_historical_record_callback(sender, instance=None, history_instance=None, **kwargs):
    attrs_to_copy = ['username', 'password', 'private_key']

    for attr in attrs_to_copy:
        if getattr(history_instance, attr):
            continue
        if not history_instance.system_user:
            continue
        system_user_attr_value = getattr(history_instance.system_user, attr)
        if system_user_attr_value:
            setattr(history_instance, attr, system_user_attr_value)
