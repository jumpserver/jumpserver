# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

# from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from .models import AssetPermission
from users.models import User


class AssetPermissionForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.exclude(role=User.ROLE_APP),
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select users')},
        ),
        label=_("User"),
        required=False,
    )

    class Meta:
        model = AssetPermission
        fields = [
            'name', 'users', 'user_groups', 'assets', 'asset_groups',
            'system_users', 'is_active', 'date_expired', 'comment',
        ]
        widgets = {
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
        }

    def clean_user_groups(self):
        users = self.cleaned_data.get('users')
        user_groups = self.cleaned_data.get('user_groups')

        if not users and not user_groups:
            raise forms.ValidationError(_("User or group at least one required"))
        return self.cleaned_data["user_groups"]

    def clean_asset_groups(self):
        assets = self.cleaned_data.get('assets')
        asset_groups = self.cleaned_data.get('asset_groups')

        if not assets and not asset_groups:
            raise forms.ValidationError(_("Asset or group at least one required"))

        return self.cleaned_data["asset_groups"]

    def clean_system_users(self):
        from assets.utils import check_assets_have_system_user

        errors = []
        assets = self.cleaned_data['assets']
        asset_groups = self.cleaned_data.get('asset_groups')
        system_users = self.cleaned_data.get('system_users')

        if not asset_groups and not assets:
            return self.cleaned_data.get("system_users")

        error_data = check_assets_have_system_user(assets, system_users)
        if error_data:
            for asset, system_users in error_data.items():
                msg = _("Asset {} of cluster {} not have [{}] system users, please check \n")
                error = forms.ValidationError(msg.format(
                        asset.hostname,
                        asset.cluster.name,
                        ", ".join(system_user.name for system_user in system_users)
                ))
                errors.append(error)

        for group in asset_groups:
            msg = _("Asset {}(group {}) of cluster {} not have [{}] system users, please check \n")
            assets = group.assets.all()
            error_data = check_assets_have_system_user(assets, system_users)
            for asset, system_users in error_data.items():
                errors.append(msg.format(
                    asset.hostname, group.name, asset.cluster.name,
                    ", ".join(system_user.name for system_user in system_users)
                ))
        if errors:
            raise forms.ValidationError(errors)
        return self.cleaned_data['system_users']
