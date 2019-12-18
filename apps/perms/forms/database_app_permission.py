#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django import forms
from orgs.mixins.forms import OrgModelForm
from assets.models import SystemUser

from ..models import DatabaseAppPermission


__all__ = ['DatabaseAppPermissionCreateUpdateForm']


class DatabaseAppPermissionCreateUpdateForm(OrgModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        users_field = self.fields.get('users')
        if self.instance:
            users_field.queryset = self.instance.users.all()
        else:
            users_field.queryset = []

        # 过滤系统用户
        system_users_field = self.fields.get('system_users')
        system_users_field.queryset = SystemUser.objects.filter(
            protocol=SystemUser.PROTOCOL_MYSQL
        )

    class Meta:
        model = DatabaseAppPermission
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
            'database_apps': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('DatabaseApp')}
            ),
            'system_users': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('System users')}
            ),
        }
