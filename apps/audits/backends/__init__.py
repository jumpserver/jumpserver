from importlib import import_module
from django.conf import settings

command_engine = import_module(settings.COMMAND_STORE_BACKEND)
command_store = command_engine.CommandStore()
record_engine = import_module(settings.RECORD_STORE_BACKEND)
record_store = record_engine.RecordStore()
from .command.serializers import CommandLogSerializer


