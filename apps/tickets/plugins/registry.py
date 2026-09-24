import re
from importlib import import_module
from pkgutil import iter_modules

from django.core.exceptions import ImproperlyConfigured


class TicketPluginRegistry:
    def __init__(self):
        self._plugins = {}
        self._discovered = False

    def register(self, plugin):
        from .base import TicketPlugin
        if not isinstance(plugin, TicketPlugin) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', plugin.type):
            raise ImproperlyConfigured('Ticket plugins require a stable lowercase type identifier.')
        if plugin.type in self._plugins:
            raise ImproperlyConfigured(f'Duplicate ticket plugin: {plugin.type}')
        self._plugins[plugin.type] = plugin

    def discover(self):
        if self._discovered:
            return
        from . import __path__
        # Only trusted packages shipped with this application are imported.
        # Plugins must defer model/serializer imports until their hooks run.
        for item in sorted(iter_modules(__path__), key=lambda item: item.name):
            if item.ispkg and not item.name.startswith('_'):
                module = import_module(f'{__package__}.{item.name}.plugin')
                self.register(module.Plugin())
        self._discovered = True

    def get(self, ticket_type):
        self.discover()
        try:
            return self._plugins[ticket_type]
        except (KeyError, TypeError):
            from tickets.workflow.errors import WorkflowConfigurationError
            raise WorkflowConfigurationError(f'Unknown ticket type: {ticket_type}')

    def all(self, *, visible=False):
        self.discover()
        return [plugin for plugin in self._plugins.values() if not visible or plugin.visible]


ticket_plugins = TicketPluginRegistry()


def get_ticket_plugin(ticket_type):
    return ticket_plugins.get(ticket_type)


def ticket_type_choices():
    # Django callable choices keep adding a plugin from requiring a migration.
    return [(plugin.type, plugin.label) for plugin in ticket_plugins.all()]
