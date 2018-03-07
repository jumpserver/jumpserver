# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Asset, AdminUser
from common.utils import get_logger

logger = get_logger(__file__)
__all__ = ['AssetCreateForm', 'AssetUpdateForm', 'AssetBulkUpdateForm']


class AssetCreateForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'public_ip', 'port',  'comment',
            'nodes', 'is_active', 'admin_user', 'labels', 'platform',

        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Nodes')
            }),
            'admin_user': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Admin user')
            }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Labels')
            }),
            'port': forms.TextInput(),
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'port': '* required',
            'admin_user': _(
                'Admin user is a privilege user exist on this asset,'
                'Example: root or other NOPASSWD sudo privilege user'
                'If asset not support ansible, set any one'
            )
        }


class AssetUpdateForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'port', 'nodes',  'is_active', 'platform',
            'public_ip', 'number', 'comment', 'admin_user', 'labels',
        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Nodes')
            }),
            'admin_user': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Admin user')
            }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Labels')
            }),
            'port': forms.TextInput(),
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'port': '* required',
            'cluster': '* required',
            'admin_user': _(
                'Admin user is a privilege user exist on this asset,'
                'Example: root or other NOPASSWD sudo privilege user'
                'If asset not support ansible, set any one'
            )
        }


class AssetBulkUpdateForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(
        required=True, help_text='* required',
        label=_('Select assets'), queryset=Asset.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select assets')
            }
        )
    )
    port = forms.IntegerField(
        label=_('Port'), required=False, min_value=1, max_value=65535,
    )
    admin_user = forms.ModelChoiceField(
        required=False, queryset=AdminUser.objects.all(),
        label=_("Admin user"),
        widget=forms.Select(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Admin user')
            }
        )
    )

    class Meta:
        model = Asset
        fields = [
            'assets', 'port',  'admin_user', 'labels', 'nodes',
        ]
        widgets = {
            'labels': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Select labels')}
            ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Select nodes')}
            ),
        }

    def save(self, commit=True):
        changed_fields = []
        for field in self._meta.fields:
            if self.data.get(field) not in [None, '']:
                changed_fields.append(field)

        cleaned_data = {k: v for k, v in self.cleaned_data.items()
                        if k in changed_fields}
        assets = cleaned_data.pop('assets')
        labels = cleaned_data.pop('labels', [])
        nodes = cleaned_data.pop('nodes')
        assets = Asset.objects.filter(id__in=[asset.id for asset in assets])
        assets.update(**cleaned_data)

        if labels:
            for label in labels:
                label.assets.add(*tuple(assets))
        if nodes:
            for node in nodes:
                node.assets.add(*tuple(assets))
        return assets
