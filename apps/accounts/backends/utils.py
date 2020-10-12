from django.conf import settings
from django.utils.module_loading import import_string


def get_account_storage():
    config = settings.ACCOUNT_STORAGE_BACKEND
    engine_class = import_string(config['ENGINE'])
    storage = engine_class(**config['CONFIG'])
    return storage
