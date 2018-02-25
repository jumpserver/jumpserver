# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Asset
from common.utils import get_logger

logger = get_logger(__file__)
__all__ = ['AssetCreateForm', 'AssetUpdateForm', 'AssetBulkUpdateForm']


class AssetCreateForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'public_ip', 'port',  'comment',
            'nodes', 'is_active', 'admin_user', 'labels',

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
            'admin_user': _('Admin user is a privilege user exist on this asset,'
                            'Example: root or other NOPASSWD sudo privilege user'
                            )
        }


class AssetUpdateForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'port', 'nodes',  'is_active',
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

    class Meta:
        model = Asset
        fields = [
            'assets', 'port',  'admin_user', 'nodes',
        ]
        widgets = {
            'admin_user': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Admin user')}
            ),
            'labels': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Labels')}
            ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Nodes')}
            ),
        }

    def save(self, commit=True):
        changed_fields = []
        for field in self._meta.fields:
            if self.data.get(field) is not None:
                changed_fields.append(field)

        cleaned_data = {k: v for k, v in self.cleaned_data.items()
                        if k in changed_fields}
        assets = cleaned_data.pop('assets')
        labels = cleaned_data.pop('labels', [])
        assets = Asset.objects.filter(id__in=[asset.id for asset in assets])
        assets.update(**cleaned_data)

        if labels:
            for asset in assets:
                asset.labels.set(labels)
        return assets
