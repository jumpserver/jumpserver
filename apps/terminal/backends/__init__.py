from importlib import import_module

from django.conf import settings

from .command.serializers import SessionCommandSerializer


def get_command_store():
    command_engine = import_module(settings.COMMAND_STORE_BACKEND)
    command_store = command_engine.CommandStore()
    return command_store


def get_replay_store():
    replay_engine = import_module(settings.REPLAY_STORE_BACKEND)
    replay_store = replay_engine.ReplayStore()
    return replay_store
