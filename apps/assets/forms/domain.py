# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from orgs.mixins import OrgModelForm
from ..models import Domain, Asset, Gateway
from .user import PasswordAndKeyAuthForm

__all__ = ['DomainForm', 'GatewayForm']


class DomainForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.all(), label=_('Asset'), required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select assets')}
        )
    )

    class Meta:
        model = Domain
        fields = ['name', 'comment', 'assets']

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].assets.all()
        super().__init__(*args, **kwargs)

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
            'private_key_file',  'is_active', 'comment',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'username': forms.TextInput(attrs={'placeholder': _('Username')}),
        }
        help_texts = {
            'name': '* required',
            'username': '* required',
        }
