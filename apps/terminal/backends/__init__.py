from importlib import import_module
from django.conf import settings
from .command.serializers import SessionCommandSerializer


def get_command_store():
    command_engine = import_module(settings.COMMAND_STORE_BACKEND)
    command_store = command_engine.CommandStore()
    return command_store

