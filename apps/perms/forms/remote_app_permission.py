#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django import forms
from orgs.mixins.forms import OrgModelForm
from orgs.utils import current_org

from ..models import RemoteAppPermission


__all__ = [
    'RemoteAppPermissionCreateUpdateForm',
]


class RemoteAppPermissionCreateUpdateForm(OrgModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        users_field = self.fields.get('users')
        if self.instance:
            users_field.queryset = self.instance.users.all()
        else:
            users_field.queryset = []

    class Meta:
        model = RemoteAppPermission
        exclude = (
            'id', 'date_created', 'created_by', 'org_id'
        )
        widgets = {
            'users': forms.SelectMultiple(
                attrs={'class': 'users-select2', 'data-placeholder': _('User')}
            ),
            'user_groups': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('User group')}
            ),
            'remote_apps': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('RemoteApp')}
            ),
            'system_users': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('System user')}
            )
        }

    def clean_user_groups(self):
        users = self.cleaned_data.get('users')
        user_groups = self.cleaned_data.get('user_groups')

        if not users and not user_groups:
            raise forms.ValidationError(
                _("User or group at least one required")
            )
        return self.cleaned_data['user_groups']
