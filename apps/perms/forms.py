# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

# from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from .models import AssetPermission
from .hands import associate_system_users_with_assets


class AssetPermissionForm(forms.ModelForm):
    def save(self, commit=True):
        instance = super(AssetPermissionForm, self).save(commit=commit)

        assets = instance.assets.all()
        asset_groups = instance.asset_groups.all()
        system_users = instance.system_users.all()
        associate_system_users_with_assets(system_users, assets, asset_groups)
        return instance

    class Meta:
        model = AssetPermission
        fields = [
            'name', 'users', 'user_groups', 'assets', 'asset_groups',
            'system_users', 'is_active', 'date_expired', 'comment',
        ]
        widgets = {
            'users': forms.SelectMultiple(attrs={'class': 'select2',
                                                 'data-placeholder': _('Select users')}),
            'user_groups': forms.SelectMultiple(attrs={'class': 'select2',
                                                       'data-placeholder': _('Select user groups')}),
            'assets': forms.SelectMultiple(attrs={'class': 'select2',
                                                  'data-placeholder': _('Select assets')}),
            'asset_groups': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select asset groups')}),
            'system_users': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select system users')}),
        }
        help_texts = {
            'name': '* required',
            'user_groups': '* User or user group at least one required',
            'asset_groups': '* Asset or Asset group at least one required',
            'system_users': '* required',
        }

