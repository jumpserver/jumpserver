from importlib import import_module
from django.conf import settings
from .command.serializers import SessionCommandSerializer

TYPE_ENGINE_MAPPING = {
    'elasticsearch': 'terminal.backends.command.es',
}


def get_command_store():
    params = settings.COMMAND_STORAGE
    engine_class = import_module(params['ENGINE'])
    storage = engine_class.CommandStore(params)
    return storage


def get_terminal_command_store():
    storage_list = {}
    for name, params in settings.TERMINAL_COMMAND_STORAGE.items():
        tp = params['TYPE']
        if tp == 'server':
            storage = get_command_store()
        else:
            if not TYPE_ENGINE_MAPPING.get(tp):
                raise AssertionError("Command storage type should in {}".format(
                    ', '.join(TYPE_ENGINE_MAPPING.keys()))
                )
            engine_class = import_module(TYPE_ENGINE_MAPPING[tp])
            storage = engine_class.CommandStore(params)
        storage_list[name] = storage
    return storage_list


def get_multi_command_store():
    from .command.multi import CommandStore
    storage_list = get_terminal_command_store().values()
    storage = CommandStore(storage_list)
    return storage


