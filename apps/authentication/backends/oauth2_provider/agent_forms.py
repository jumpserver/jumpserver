from django import forms
from django.utils.translation import gettext_lazy as _
from oauth2_provider.forms import AllowForm

from terminal.agent_service import available_agent_organizations
from authentication.services.agent_clients import user_agent_client_limit_reached, user_agent_client_limit_message


class AgentAllowForm(AllowForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        data = super().clean()
        if data.get('allow') and not available_agent_organizations(self.user).exists():
            raise forms.ValidationError(_('No authorized organizations are available.'))
        if data.get('allow') and user_agent_client_limit_reached(self.user, data.get('client_id')):
            raise forms.ValidationError(user_agent_client_limit_message(), code='mcp_client_limit')
        return data
