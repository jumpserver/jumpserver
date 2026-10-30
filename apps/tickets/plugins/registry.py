from django.utils.translation import gettext
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
        if plugin.execution_mode not in ('automatic', 'external', 'approval_only'):
            raise ImproperlyConfigured(f'Invalid execution mode for ticket plugin: {plugin.type}')
        if plugin.self_service and not (plugin.request_serializer or plugin.apply_serializer):
            raise ImproperlyConfigured(f'Self-service ticket plugin {plugin.type} requires a serializer.')
        if plugin.apply_serializer and not plugin.custom_form:
            raise ImproperlyConfigured(f'Legacy apply serializer {plugin.type} requires a custom form.')
        if plugin.creation_modes is not None and (
                not plugin.creation_modes or set(plugin.creation_modes) - {'manual', 'operation', 'system'}):
            raise ImproperlyConfigured(f'Invalid creation modes for ticket plugin: {plugin.type}')
        if not isinstance(plugin.actions, dict) or any(
                not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', name)
                or not isinstance(handler, str) for name, handler in plugin.actions.items()):
            raise ImproperlyConfigured(f'Invalid actions for ticket plugin: {plugin.type}')
        self._plugins[plugin.type] = plugin

    def validate(self):
        """Resolve definitions once models are loaded, before serving requests."""
        from django.utils.module_loading import import_string
        from rest_framework.serializers import BaseSerializer
        from rest_framework.permissions import BasePermission
        from rest_framework.throttling import BaseThrottle
        from .actions import TicketAction
        for plugin in self._plugins.values():
            try:
                for path in (plugin.request_serializer, plugin.apply_serializer, plugin.resource_serializer):
                    if path and not issubclass(import_string(path), BaseSerializer):
                        raise ValueError(f'Invalid serializer: {path}')
                plugin.metadata()
                for path in plugin.actions.values():
                    handler = import_string(path)
                    if (not issubclass(handler, TicketAction) or handler.execute is TicketAction.execute
                            or handler.method not in ('GET', 'POST')):
                        raise ValueError(f'Invalid action handler: {path}')
                    for cls in handler.permission_classes:
                        if not issubclass(cls, BasePermission):
                            raise ValueError(f'Invalid permission in {path}')
                    for cls in handler.throttle_classes:
                        if not issubclass(cls, BaseThrottle):
                            raise ValueError(f'Invalid throttle in {path}')
            except (ImportError, AttributeError, TypeError, ValueError, ImproperlyConfigured) as exc:
                raise ImproperlyConfigured(f'Invalid ticket plugin {plugin.type}: {exc}') from exc

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
            raise WorkflowConfigurationError(gettext('Unknown ticket type: {ticket_type}').format(ticket_type=ticket_type))

    def all(self, *, visible=False):
        self.discover()
        return [plugin for plugin in self._plugins.values() if not visible or plugin.visible]


ticket_plugins = TicketPluginRegistry()


def get_ticket_plugin(ticket_type):
    return ticket_plugins.get(ticket_type)


def ticket_type_choices():
    # Django callable choices keep adding a plugin from requiring a migration.
    return [(plugin.type, plugin.label) for plugin in ticket_plugins.all()]
