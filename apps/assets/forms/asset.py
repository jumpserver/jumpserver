# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from orgs.mixins import OrgModelForm

from ..models import Asset, Node


logger = get_logger(__file__)
__all__ = [
    'AssetCreateForm', 'AssetUpdateForm', 'AssetBulkUpdateForm', 'ProtocolForm',
]


class ProtocolForm(forms.Form):
    name = forms.ChoiceField(
        choices=Asset.PROTOCOL_CHOICES, label=_("Name"), initial='ssh',
        widget=forms.Select(attrs={'class': 'form-control protocol-name'})
    )
    port = forms.IntegerField(
        max_value=65534, min_value=1, label=_("Port"), initial=22,
        widget=forms.TextInput(attrs={'class': 'form-control protocol-port'})
    )


class AssetCreateForm(OrgModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nodes_field = self.fields['nodes']
        nodes_field.choices = ((n.id, n.full_value) for n in
                               Node.get_queryset())

    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'public_ip', 'protocols', 'comment',
            'nodes', 'is_active', 'admin_user', 'labels', 'platform',
            'domain',
        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Nodes')
            }),
            'admin_user': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Admin user')
            }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Label')
            }),
            'domain': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Domain')
            }),
        }
        labels = {
            'nodes': _("Node"),
        }
        help_texts = {
            'admin_user': _(
                'root or other NOPASSWD sudo privilege user existed in asset,'
                'If asset is windows or other set any one, more see admin user left menu'
            ),
            'platform': _("Windows 2016 RDP protocol is different, If is window 2016, set it"),
            'domain': _("If your have some network not connect with each other, you can set domain")
        }


class AssetUpdateForm(OrgModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'protocols', 'nodes',  'is_active', 'platform',
            'public_ip', 'number', 'comment', 'admin_user', 'labels',
            'domain',
        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Node')
            }),
            'admin_user': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Admin user')
            }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Label')
            }),
            'domain': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Domain')
            }),
        }
        labels = {
            'nodes': _("Node"),
        }
        help_texts = {
            'admin_user': _(
                'root or other NOPASSWD sudo privilege user existed in asset,'
                'If asset is windows or other set any one, more see admin user left menu'
            ),
            'platform': _("Windows 2016 RDP protocol is different, If is window 2016, set it"),
            'domain': _("If your have some network not connect with each other, you can set domain")
        }


class AssetBulkUpdateForm(OrgModelForm):
    assets = forms.ModelMultipleChoiceField(
        required=True,
        label=_('Select assets'), queryset=Asset.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select assets')
            }
        )
    )

    class Meta:
        model = Asset
        fields = [
            'assets', 'admin_user', 'labels', 'platform',
            'domain',
        ]
        widgets = {
            'labels': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Label')}
            ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Node')}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 重写其他字段为不再required
        for name, field in self.fields.items():
            if name != 'assets':
                field.required = False

    def save(self, commit=True):
        changed_fields = []
        for field in self._meta.fields:
            if self.data.get(field) not in [None, '']:
                changed_fields.append(field)

        cleaned_data = {k: v for k, v in self.cleaned_data.items()
                        if k in changed_fields}
        assets = cleaned_data.pop('assets')
        labels = cleaned_data.pop('labels', [])
        nodes = cleaned_data.pop('nodes', None)
        assets = Asset.objects.filter(id__in=[asset.id for asset in assets])
        assets.update(**cleaned_data)

        if labels:
            for asset in assets:
                asset.labels.set(labels)
        if nodes:
            for asset in assets:
                asset.nodes.set(nodes)
        return assets
