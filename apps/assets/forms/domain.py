# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from orgs.mixins.forms import OrgModelForm
from ..models import Domain, Asset, Gateway
from .user import PasswordAndKeyAuthForm

__all__ = ['DomainForm', 'GatewayForm']


class DomainForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects, label=_('Asset'), required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select assets')}
        )
    )

    class Meta:
        model = Domain
        fields = ['name', 'comment', 'assets']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        assets_field = self.fields.get('assets')

        # 没有data代表是渲染表单, 有data代表是提交创建/更新表单
        if not self.data:
            # 有instance 代表渲染更新表单, 否则是创建表单
            # 前端渲染优化, 防止过多资产, 设置assets queryset为none
            if self.instance:
                assets_field.initial = self.instance.assets.all()
                assets_field.queryset = self.instance.assets.all()
            else:
                assets_field.queryset = Asset.objects.none()
        else:
            assets_field.queryset = Asset.objects.all()

    def save(self, commit=True):
        instance = super().save(commit=commit)
        assets = self.cleaned_data['assets']
        instance.assets.set(assets)
        return instance


class GatewayForm(PasswordAndKeyAuthForm, OrgModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password_field = self.fields.get('password')
        password_field.help_text = _('Password should not contain special characters')
        protocol_field = self.fields.get('protocol')
        protocol_field.choices = [Gateway.PROTOCOL_CHOICES[0]]

    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        instance = super().save()
        password = self.cleaned_data.get('password')
        private_key, public_key = super().gen_keys()
        instance.set_auth(password=password, private_key=private_key)
        return instance

    class Meta:
        model = Gateway
        fields = [
            'name', 'ip', 'port', 'username', 'protocol', 'domain', 'password',
            'private_key',  'is_active', 'comment',
        ]
        help_texts = {
            'protocol': _("SSH gateway support proxy SSH,RDP,VNC")
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'username': forms.TextInput(attrs={'placeholder': _('Username')}),
        }
