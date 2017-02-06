from importlib import import_module
from django.conf import settings

command_engine = import_module(settings.COMMAND_STORE_BACKEND)
command_store = command_engine.CommandStore()
from .command.serializers import CommandLogSerializer
