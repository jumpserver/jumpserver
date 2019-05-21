#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django import forms
from orgs.mixins import OrgModelForm
from orgs.utils import current_org

from ..models import RemoteAppPermission


__all__ = [
    'RemoteAppPermissionCreateUpdateForm',
]


class RemoteAppPermissionCreateUpdateForm(OrgModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users_field = self.fields.get('users')
        if hasattr(users_field, 'queryset'):
            users_field.queryset = current_org.get_org_users()

    class Meta:
        model = RemoteAppPermission
        exclude = (
            'id', 'date_created', 'created_by', 'org_id'
        )
        widgets = {
            'users': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('User')}
            ),
            'user_groups': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('User group')}
            ),
            'remote_apps': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('RemoteApp')}
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
