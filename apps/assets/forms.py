# coding:utf-8
from django import forms

from .models import IDC, Asset, AssetGroup, AdminUser, SystemUser
from django.utils.translation import gettext_lazy as _


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset

        fields = [
            "ip", "other_ip", "remote_card_ip", "hostname", "port", "groups", "username", "password",
            "idc", "mac_address", "brand", "cpu", "memory", "disk", "os", "cabinet_no", "cabinet_pos",
            "number", "status", "type", "env", "sn", "is_active", "comment"
        ]

        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Select asset groups')}),
        }


class AssetGroupForm(forms.ModelForm):
    # See AdminUserForm comment same it
    assets = forms.ModelMultipleChoiceField(queryset=Asset.objects.all(),
                                            label=_('Asset'),
                                            required=False,
                                            widget=forms.SelectMultiple(
                                                attrs={'class': 'select2', 'data-placeholder': _('Select assets')})
                                            )

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance'):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].assets.all()
        super(AssetGroupForm, self).__init__(*args, **kwargs)

    def _save_m2m(self):
        super(AssetGroupForm, self)._save_m2m()
        assets = self.cleaned_data['assets']
        self.instance.assets.clear()
        self.instance.assets.add(*tuple(assets))

    class Meta:
        model = AssetGroup
        fields = [
            "name", "comment"
        ]
        help_texts = {
            'name': '* required',
        }


class IDCForm(forms.ModelForm):
    # See AdminUserForm comment same it
    assets = forms.ModelMultipleChoiceField(queryset=Asset.objects.all(),
                                            label=_('Asset'),
                                            required=False,
                                            widget=forms.SelectMultiple(
                                                attrs={'class': 'select2', 'data-placeholder': _('Select assets')})
                                            )

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance'):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].assets.all()
        super(IDCForm, self).__init__(*args, **kwargs)

    def _save_m2m(self):
        super(IDCForm, self)._save_m2m()
        assets = self.cleaned_data['assets']
        self.instance.assets.clear()
        self.instance.assets.add(*tuple(assets))

    class Meta:
        model = IDC
        fields = ['name', "bandwidth", "operator", 'contact', 'phone', 'address', 'network', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'network': forms.Textarea(
                attrs={'placeholder': '192.168.1.0/24\n192.168.2.0/24'})
        }


class AdminUserForm(forms.ModelForm):
    # Admin user assets define, let user select, save it in form not in view
    assets = forms.ModelMultipleChoiceField(queryset=Asset.objects.all(),
                                            label=_('Asset'),
                                            required=False,
                                            widget=forms.SelectMultiple(
                                                attrs={'class': 'select2', 'data-placeholder': _('Select assets')})
                                            )
    # Form field name can not start with `_`, so redefine it,
    password = forms.CharField(widget=forms.PasswordInput, max_length=100, min_length=8, strip=True,
                               help_text=_('If also set private key, use that first'), required=False)
    # Need use upload private key file except paste private key content
    private_key_file = forms.FileField(required=False)

    def __init__(self, *args, **kwargs):
        # When update a admin user instance, initial it
        if kwargs.get('instance'):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].assets.all()
        super(AdminUserForm, self).__init__(*args, **kwargs)

    def _save_m2m(self):
        # Save assets relation with admin user
        super(AdminUserForm, self)._save_m2m()
        assets = self.cleaned_data['assets']
        self.instance.assets.clear()
        self.instance.assets.add(*tuple(assets))

    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        admin_user = super(AdminUserForm, self).save(commit=commit)
        password = self.cleaned_data['password']
        private_key_file = self.cleaned_data['private_key_file']

        if password:
            admin_user.password = password
            print(password)
        # Todo: Validate private key file, and generate public key
        if private_key_file:
            print(private_key_file)
            admin_user.private_key = private_key_file.read()
        admin_user.save()
        return self.instance

    class Meta:
        model = AdminUser
        fields = ['name', 'username', 'password', 'private_key_file', 'as_default', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'username': forms.TextInput(attrs={'placeholder': _('Username')}),
        }
        help_texts = {
            'name': '* required',
            'username': '* required',
        }

