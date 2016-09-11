# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from .models import PermUserAsset


class PermUserAssetForm(forms.ModelForm):
    class Meta:
        model = PermUserAsset
        fields = [
            'user', 'action', 'assets', 'asset_groups', 'system_users', 'date_expired', 'comment'
        ]
        widgets = {
            'user': forms.HiddenInput(attrs={'style': 'display: none'}),
            'assets': forms.SelectMultiple(attrs={'class': 'select2',
                                                  'data-placeholder': _('Select assets')}),
            'asset_groups': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select asset groups')}),
            'system_users': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select system users')}),

        }
