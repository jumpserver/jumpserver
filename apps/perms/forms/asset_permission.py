# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from functools import reduce
from django import forms
from django.utils.translation import ugettext_lazy as _

from orgs.mixins import OrgModelForm
from orgs.utils import current_org
from perms.models import AssetPermission
from assets.models import Asset, Node

__all__ = [
    'AssetPermissionForm',
]


class AssetPermissionForm(OrgModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users_field = self.fields.get('users')
        users_field.queryset = current_org.get_org_users()

        # 前端渲染优化, 防止过多资产
        if not self.data:
            instance = kwargs.get('instance')
            assets_field = self.fields['assets']
            if instance:
                assets_field.queryset = instance.assets.all()
            else:
                assets_field.queryset = Asset.objects.none()
            nodes_field = self.fields['nodes']
            nodes_field._queryset = Node.get_queryset()

    def clean_action(self):
        actions = self.cleaned_data.get("action")
        return reduce(lambda x, y: x | y, actions)

    class Meta:
        model = AssetPermission
        exclude = (
            'id', 'date_created', 'created_by', 'org_id'
        )
        widgets = {
            'users': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("User")}
            ),
            'user_groups': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("User group")}
            ),
            'assets': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("Asset")}
            ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("Node")}
            ),
            'system_users': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('System user')}
            ),
            'action': forms.CheckboxSelectMultiple()
        }
        labels = {
            'nodes': _("Node"),
        }
        help_texts = {
            'action': _('Tips: The RDP protocol does not support separate '
                        'controls for uploading or downloading files')
        }

    def clean_user_groups(self):
        users = self.cleaned_data.get('users')
        user_groups = self.cleaned_data.get('user_groups')

        if not users and not user_groups:
            raise forms.ValidationError(
                _("User or group at least one required"))
        return self.cleaned_data["user_groups"]

    def clean_asset_groups(self):
        assets = self.cleaned_data.get('assets')
        asset_groups = self.cleaned_data.get('asset_groups')

        if not assets and not asset_groups:
            raise forms.ValidationError(
                _("Asset or group at least one required"))

        return self.cleaned_data["asset_groups"]
