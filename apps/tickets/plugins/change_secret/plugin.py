from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'change_secret'
    label = _('Change account password')
    self_service = True
    execution_mode = 'automatic'
    request_serializer = 'tickets.plugins.change_secret.serializer.RequestSerializer'

    def get_execution_mode(self, ticket):
        instance = getattr(ticket, 'workflow_instance', None)
        return self.execution_mode if instance and instance.context.get('change_secret_version') == 1 else 'approval_only'

    def build_context(self, ticket):
        from ..resources import account_context
        from .execution import validate_context
        context = account_context(ticket)
        context['accounts'] = [a for a in context['accounts'] if a['secret_type'] == 'password']
        validate_context(ticket, context)
        return {**context, 'actions': ['change_secret'], 'change_secret_version': 1}

    def on_approved(self, instance, ticket):
        from .execution import create_execution
        return create_execution(instance, ticket)

    def get_result(self, ticket, user):
        from .execution import get_result
        if self.get_execution_mode(ticket) == 'approval_only':
            return {'state': 'approval_only', 'actions': []}
        return get_result(ticket, user)
