from common.utils.common import singleton
from django.utils.module_loading import import_string
from django.conf import settings
from django.utils.functional import LazyObject


def get_storage_backend():
    """ 获取账号存储 backend """
    config = settings.ACCOUNT_STORAGE_BACKEND
    engine_module = config.get('ENGINE')
    engine_config = config.get('CONFIG')
    engine_class = import_string(engine_module)
    backend = engine_class(**engine_config)
    return backend


@singleton
class StorageBackend(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_backend()


storage = StorageBackend()
