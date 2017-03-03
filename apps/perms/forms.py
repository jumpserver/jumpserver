# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

# from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from .models import AssetPermission


class AssetPermissionForm(forms.ModelForm):
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
