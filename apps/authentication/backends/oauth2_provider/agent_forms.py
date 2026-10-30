from django import forms
from django.utils.translation import gettext_lazy as _
from oauth2_provider.forms import AllowForm

from terminal.agent_service import available_agent_organizations


class AgentAllowForm(AllowForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        data = super().clean()
        if data.get('allow') and not available_agent_organizations(self.user).exists():
            raise forms.ValidationError(_('No authorized organizations are available.'))
        return data
