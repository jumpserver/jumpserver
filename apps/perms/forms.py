# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from .models import UserAssetPerm


class UserAssetPermForm(forms.ModelForm):
    class Meta:
        model = UserAssetPerm
        fields = [
            'assets', 'asset_groups', 'system_users', 'date_expired', 'comment'
        ]
