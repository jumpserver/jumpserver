from importlib import import_module
from django.conf import settings
from .command.serializers import SessionCommandSerializer

from common import utils

TYPE_ENGINE_MAPPING = {
    'elasticsearch': 'terminal.backends.command.es',
}


def get_command_storage():
    config = settings.COMMAND_STORAGE
    engine_class = import_module(config['ENGINE'])
    storage = engine_class.CommandStore(config)
    return storage


def get_terminal_command_storages():
    storage_list = {}
    command_storage = utils.get_command_storage_setting()

    for name, params in command_storage.items():
        tp = params['TYPE']
        if tp == 'server':
            storage = get_command_storage()
        else:
            if not TYPE_ENGINE_MAPPING.get(tp):
                continue
            engine_class = import_module(TYPE_ENGINE_MAPPING[tp])
            storage = engine_class.CommandStore(params)
        storage_list[name] = storage
    return storage_list


def get_multi_command_storage():
    from .command.multi import CommandStore
    storage_list = get_terminal_command_storages().values()
    storage = CommandStore(storage_list)
    return storage


