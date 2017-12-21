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
            'system_users': '* required',
            'user_groups': _('User or user group at least one required'),
            'asset_groups': _('Asset or Asset group at least one required'),
        }

    def clean_system_users(self):
        from assets.utils import check_assets_have_system_user

        errors = []
        assets = self.cleaned_data['assets']
        asset_groups = self.cleaned_data['asset_groups']
        system_users = self.cleaned_data['system_users']

        error_data = check_assets_have_system_user(assets, system_users)
        if error_data:
            for asset, system_users in error_data.items():
                msg = _("Asset {} not have [{}] system users, please check \n")
                error = forms.ValidationError(msg.format(
                        asset.hostname,
                        ", ".join(system_user.name for system_user in system_users)
                ))
                errors.append(error)

        for group in asset_groups:
            msg = _("Asset {}: {} not have [{}] system users, please check")
            assets = group.assets.all()
            error_data = check_assets_have_system_user(assets, system_users)
            for asset, system_users in error_data.items():
                errors.append(msg.format(
                    group.name, asset.hostname,
                    ", ".join(system_user.name for system_user in system_users)
                ))
        if errors:
            raise forms.ValidationError(errors)
        return self.cleaned_data['system_users']
