# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

# from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from .models import AssetPermission


class AssetPermissionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('user', None)
        super(AssetPermissionForm, self).__init__(*args, **kwargs)
        self.fields['user_groups'].required = False
        self.fields['user_groups'].widget.attrs['disabled'] = True

        if not self.current_user.is_superuser:
            self.fields['users'].queryset = self.current_user.managed_users.exclude(id=self.current_user.id)
            self.fields['system_users'].queryset =  self.current_user.system_users
            self.fields['asset_groups'].queryset = self.current_user.asset_groups

    def clean_users(self):
        users = self.cleaned_data['users']
        for user in users:
            if not user in self.current_user.managed_users.exclude(id=self.current_user.id):
                raise forms.ValidationError(
                                _('Invalid value: %(name)s'),
                                code='Invalid',
                                params={'name': user.name}
                            )
        return users

    def clean_asset_groups(self):
        asset_groups = self.cleaned_data['asset_groups']
        for asset_group in asset_groups:
            if not asset_group in self.current_user.asset_groups:
                raise forms.ValidationError(
                          _('Invalid value: %(name)s'),
                          code='Invalid',
                          params={'name': asset_group.name}
                      )
        return asset_groups

    def clean_system_users(self):
        system_users = self.cleaned_data['system_users']
        for system_user in system_users:
            if not system_user in self.current_user.system_users:
                raise forms.ValidationError(
                          _('Invalid value: %(name)s'),
                          code='Invalid',
                          params={'name': system_user.name}
                      )
        return system_users

    class Meta:
        model = AssetPermission
        fields = [
            'name', 'users', 'user_groups', 'assets', 'asset_groups',
            'system_users', 'is_active', 'date_expired', 'comment',
        ]
        widgets = {
            'users': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select users')}),
            'user_groups': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select user groups')}),
            'assets': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select assets')}),
            'asset_groups': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select asset groups')}),
            'system_users': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select system users')}),
        }
        help_texts = {
            'name': '* required',
            'user_groups': '* User or user group at least one required',
            'asset_groups': '* Asset or Asset group at least one required',
            'system_users': '* required',
        }
