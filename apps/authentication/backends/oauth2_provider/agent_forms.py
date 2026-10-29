from django import forms
from django.utils.translation import gettext_lazy as _
from oauth2_provider.forms import AllowForm

from orgs.models import Organization
from terminal.agent_service import available_agent_organizations


class AgentAllowForm(AllowForm):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(), required=False, label=_('Organization'),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        organizations = available_agent_organizations(user)
        self.fields['organization'].queryset = organizations
        choices = list(organizations[:2])
        self.single_organization = choices[0] if len(choices) == 1 else None
        if self.single_organization:
            self.fields['organization'].initial = self.single_organization.pk
            self.fields['organization'].empty_label = None

    def clean(self):
        data = super().clean()
        if data.get('allow') and 'organization' not in self.errors:
            organization = data.get('organization') or self.single_organization
            if organization is None:
                self.add_error('organization', _('Select an organization to authorize.'))
            data['organization'] = organization
        return data
