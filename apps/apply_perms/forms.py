# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

# from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from .models import ApplyPermission
from assets.models import Asset, AssetGroup, SystemUser
from users.models import UserGroup, User
import json

class ApplyPermissionForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        help_text=_('* required'),
        label=_('Name')
    )

    assets = forms.ModelMultipleChoiceField(
        queryset = Asset.objects.none(),
        required=False,
        label=_('Select assets'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )

    asset_groups = forms.ModelMultipleChoiceField(
        queryset = AssetGroup.objects.none(),
        required=False,
        help_text=_('* Asset or Asset group at least one required'),
        label=_('Select asset groups'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )

    user_groups = forms.ModelMultipleChoiceField(
        queryset = UserGroup.objects.none(),
        required=False,
        disabled=True,
        label=_('Select user groups'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )

    system_users = forms.ModelMultipleChoiceField(
        queryset = SystemUser.objects.none(),
        required=True,
        help_text=_('* required'),
        label=_('Select system users'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )

    approver = forms.ModelChoiceField(
        queryset = User.objects.none(),
        required=True,
        help_text=_('* required'),
        label=_('Select approver'),
        widget=forms.Select(
            attrs={
                'class': 'select2',
            }
        )
    )

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('user', None)
        instance = kwargs.get('instance', None)
        initial = kwargs.pop('initial', {})
        if instance:
            initial['assets'] = json.loads(instance.assets)
            initial['asset_groups'] = json.loads(instance.asset_groups)
            initial['system_users'] = json.loads(instance.system_users)
        kwargs['initial'] = initial
        super(ApplyPermissionForm, self).__init__(*args, **kwargs)
        if current_user:
            self.fields['assets'].queryset = current_user.can_apply_assets
            self.fields['asset_groups'].queryset = current_user.can_apply_asset_groups
            self.fields['system_users'].queryset = current_user.can_apply_system_users
            self.fields['approver'].queryset = current_user.group_managers

    class Meta:
        model = ApplyPermission
        fields = [
            'name', 'user_groups', 'assets', 'asset_groups', 'system_users', 'approver',
        ]
