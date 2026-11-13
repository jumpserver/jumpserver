from django import forms
from django.utils.translation import gettext_lazy as _
from oauth2_provider.forms import AllowForm
from oauth2_provider.models import get_application_model

from terminal.agent_service import available_agent_organizations
from authentication.services.agent_clients import (
    agent_authorization_conflict_message, has_other_agent_authorizations,
    user_agent_client_limit_reached, user_agent_client_limit_message,
)


class AgentAllowForm(AllowForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        data = super().clean()
        if data.get('allow') and not available_agent_organizations(self.user).exists():
            raise forms.ValidationError(_('No authorized organizations are available.'))
        if data.get('allow'):
            application_id = get_application_model().objects.filter(
                client_id=data.get('client_id'),
            ).values_list('pk', flat=True).first()
            if application_id and has_other_agent_authorizations(self.user.pk, application_id):
                raise forms.ValidationError(agent_authorization_conflict_message(), code='mcp_client_in_use')
        if data.get('allow') and user_agent_client_limit_reached(self.user, data.get('client_id')):
            raise forms.ValidationError(user_agent_client_limit_message(), code='mcp_client_limit')
        return data
