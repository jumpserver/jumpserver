from importlib import import_module
from django.conf import settings
from django.utils.functional import LazyObject

from common.utils import get_logger

logger = get_logger(__file__)

TYPE_ENGINE_MAPPING = {
    'elasticsearch': 'terminal.backends.command.es',
    'es': 'terminal.backends.command.es',
}


def get_command_storage():
    config = settings.COMMAND_STORAGE
    engine_class = import_module(config['ENGINE'])
    storage = engine_class.CommandStore(config)
    return storage


def get_server_replay_storage():
    from jms_storage import get_object_storage
    config = settings.SERVER_REPLAY_STORAGE
    storage = get_object_storage(config)
    return storage


def get_terminal_command_storages():
    from ..models import CommandStorage
    storage_list = {}
    for s in CommandStorage.objects.all():
        if not s.is_valid():
            logger.warn(f'Command storage invalid: storage={s}')
            continue

        if s.type_server:
            storage = get_command_storage()
        else:
            if not TYPE_ENGINE_MAPPING.get(s.type):
                continue
            engine_class = import_module(TYPE_ENGINE_MAPPING[s.type])
            storage = engine_class.CommandStore(s.config)
        storage_list[s.name] = storage
    return storage_list


def get_multi_command_storage():
    from .command.multi import CommandStore
    storage_list = get_terminal_command_storages().values()
    storage = CommandStore(storage_list)
    return storage


class ServerReplayStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_server_replay_storage()


class ServerCommandStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_command_storage()


server_command_storage = ServerCommandStorage()
server_replay_storage = ServerReplayStorage()
