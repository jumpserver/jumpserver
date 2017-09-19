# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

# from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from .models import ApplyPermission
from assets.models import Asset, AssetGroup, SystemUser
from users.models import UserGroup, User

class ApplyPermissionForm(forms.ModelForm):
    name = forms.CharField(
        required=False,
        help_text=_('* required'),
        label=_('Name')
    )
    assets = forms.ModelMultipleChoiceField(
        queryset = Asset.objects.all(),
        required=False,
        help_text=_('* required'),
        label=_('Select assets'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )
    asset_groups = forms.ModelMultipleChoiceField(
        queryset = AssetGroup.objects.all(),
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
        queryset = UserGroup.objects.all(),
        required=False,
        label=_('Select user groups'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )
    system_users = forms.ModelMultipleChoiceField(
        queryset = SystemUser.objects.all(),
        required=True,
        help_text=_('* required'),
        label=_('Select system users'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )
    approver = forms.ModelMultipleChoiceField(
        queryset = User.objects.filter(role__in=['Admin', 'GroupAdmin']),
        required=True,
        help_text=_('* required'),
        label=_('Select approver'),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
            }
        )
    )
    class Meta:
        model = ApplyPermission
        fields = [
            'name', 'user_groups', 'assets', 'asset_groups', 'system_users', 'approver',
        ]