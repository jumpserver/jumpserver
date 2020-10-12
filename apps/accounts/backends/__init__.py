from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.functional import LazyObject
from .vault import VaultBackend


def get_account_storage():
    config = settings.ACCOUNT_STORAGE_BACKEND
    engine_class = import_string(config['ENGINE'])
    s = engine_class(**config['CONFIG'])
    return s


class Storage(LazyObject):
    def _setup(self):
        self._wrapped = get_account_storage()


storage = Storage()
