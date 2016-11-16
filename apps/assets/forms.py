# coding:utf-8
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import IDC, Asset, AssetGroup, AdminUser, SystemUser, Tag
from common.utils import validate_ssh_private_key, ssh_pubkey_gen


# class AssetForm(forms.ModelForm):
#     class Meta:
#         model = Asset
#
#         fields = [
#             'ip', 'other_ip', 'remote_card_ip', 'hostname', 'port', 'groups', 'username', 'password',
#             'idc', 'mac_address', 'brand', 'cpu', 'memory', 'disk', 'os', 'cabinet_no', 'cabinet_pos',
#             'number', 'status', 'type', 'env', 'sn', 'is_active', 'comment', 'admin_user', 'system_users'
#         ]
#
#         widgets = {
#             'groups': forms.SelectMultiple(attrs={'class': 'select2-groups', 'data-placeholder': _('Select asset groups')}),
#             'system_user': forms.SelectMultiple(attrs={'class': 'select2-system-user', 'data-placeholder': _('Select asset system user')}),
#             'admin_user': forms.SelectMultiple(attrs={'class': 'select2-admin-user', 'data-placeholder': _('Select asset admin user')}),
        # }
#

class AssetCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        if instance:
            initial = kwargs.get('initial', {})
            initial['tags'] = [t.pk for t in kwargs['instance'].tags.all()]
        super(AssetCreateForm, self).__init__(*args, **kwargs)

    def _save_m2m(self):
        super(AssetCreateForm, self)._save_m2m()
        tags = self.cleaned_data['tags']
        self.instance.tags.clear()
        self.instance.tags.add(*tuple(tags))

    class Meta:
        model = Asset
        tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all())
        fields = [
            'hostname', 'ip', 'port', 'type', 'comment', 'admin_user', 'system_users', 'idc', 'groups',
            'other_ip', 'remote_card_ip', 'mac_address', 'brand', 'cpu', 'memory', 'disk', 'os', 'cabinet_no',
            'cabinet_pos', 'number', 'status', 'env', 'sn', 'tags',
        ]
        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2',
                                                  'data-placeholder': _('Select asset groups')}),
            'tags': forms.SelectMultiple(attrs={'class': 'select2',
                                                'data-placeholder': _('Select asset tags')}),
            'system_users': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select asset system users')}),
            'admin_user': forms.Select(attrs={'class': 'select2', 'data-placeholder': _('Select asset admin user')}),
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'system_users': _('System user will be granted for user to login assets (using ansible create automatic)'),
            'admin_user': _('Admin user should be exist on asset already, And have sudo ALL permission'),
            'tags': '最多5个标签，单个标签最长8个汉字，按回车确认'
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
        if kwargs.get('instance', None):
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
            "name", "comment","system_users",
        ]
        widgets = {
            'name' : forms.TextInput(attrs={}),
            'system_users': forms.SelectMultiple(attrs={'class': 'select2-system-user', 'data-placeholder': _('Select asset system user')}),

        }
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
        fields = ['name', "bandwidth", "operator", 'contact', 'phone', 'address', 'intranet', 'extranet','comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'intranet': forms.Textarea(
                attrs={'placeholder': 'IP段之间用逗号隔开，如：192.168.1.0/24,192.168.1.0/24'}),
            'extranet': forms.Textarea(
                attrs={'placeholder': 'IP段之间用逗号隔开，如：201.1.32.1/24,202.2.32.1/24'})
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
        private_key = self.cleaned_data['private_key_file']
        public_key = ssh_pubkey_gen(private_key)

        if password:
            admin_user.password = password
        if private_key:
            admin_user.private_key = private_key
            admin_user.public_key = public_key
        admin_user.save()
        return admin_user

    def clean_private_key_file(self):
        private_key_file = self.cleaned_data['private_key_file']
        if private_key_file:
            private_key = private_key_file.read()
            if not validate_ssh_private_key(private_key):
                raise forms.ValidationError(_('Invalid private key'))
            return private_key
        return private_key_file

    def clean(self):
        password = self.cleaned_data['password']
        private_key_file = self.cleaned_data.get('private_key_file', '')

        if not (password or private_key_file):
            raise forms.ValidationError(_('Password and private key file must be input one'))

    class Meta:
        model = AdminUser
        fields = ['name', 'username', 'password', 'private_key_file', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'username': forms.TextInput(attrs={'placeholder': _('Username')}),
        }
        help_texts = {
            'name': '* required',
            'username': '* required',
        }


class SystemUserForm(forms.ModelForm):
    # Admin user assets define, let user select, save it in form not in view
    assets = forms.ModelMultipleChoiceField(queryset=Asset.objects.all(),
                                            label=_('Asset'),
                                            required=False,
                                            widget=forms.SelectMultiple(
                                                attrs={'class': 'select2', 'data-placeholder': _('Select assets')})
                                            )
    asset_groups = forms.ModelMultipleChoiceField(queryset=AssetGroup.objects.all(),
                                                  label=_('Asset group'),
                                                  required=False,
                                                  widget=forms.SelectMultiple(
                                                      attrs={'class': 'select2',
                                                             'data-placeholder': _('Select asset groups')})
                                                  )
    auto_generate_key = forms.BooleanField(initial=True)
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
            initial['asset_groups'] = kwargs['instance'].asset_groups.all()
        super(SystemUserForm, self).__init__(*args, **kwargs)

    def _save_m2m(self):
        # Save assets relation with admin user
        super(SystemUserForm, self)._save_m2m()
        assets = self.cleaned_data['assets']
        asset_groups = self.cleaned_data['asset_groups']
        self.instance.assets.clear()
        self.instance.assets.add(*tuple(assets))
        self.instance.asset_groups.clear()
        self.instance.asset_groups.add(*tuple(asset_groups))

    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        system_user = super(SystemUserForm, self).save(commit=commit)
        password = self.cleaned_data['password']
        private_key_file = self.cleaned_data['private_key_file']

        if password:
            system_user.password = password
            print(password)
        # Todo: Validate private key file, and generate public key
        # Todo: Auto generate private key and public key
        if private_key_file:
            system_user.private_key = private_key_file.read().strip()
        system_user.save()
        return self.instance

    class Meta:
        model = SystemUser
        fields = [
            'name', 'username', 'protocol', 'auto_generate_key', 'password', 'private_key_file', 'as_default',
            'auto_push', 'auto_update', 'sudo', 'comment', 'shell', 'home', 'uid',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'username': forms.TextInput(attrs={'placeholder': _('Username')}),
        }
        help_texts = {
            'name': '* required',
            'username': '* required',
            'auth_push': 'Auto push system user to asset',
            'auth_update': 'Auto update system user ssh key',
        }


class AssetTagForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(queryset=Asset.objects.all(),
                                            label=_('Asset'),
                                            required=False,
                                            widget=forms.SelectMultiple(
                                                attrs={'class': 'select2', 'data-placeholder': _('Select assets')})
                                            )

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].asset_set.all()
        super(AssetTagForm, self).__init__(*args, **kwargs)

    def _save_m2m(self):
        super(AssetTagForm, self)._save_m2m()
        assets = self.cleaned_data['assets']
        self.instance.asset_set.clear()
        self.instance.asset_set.add(*tuple(assets))

    class Meta:
        model = Tag
        fields = [
            "name",
        ]
        widgets = {
            'name' : forms.TextInput(attrs={}),

        }
        help_texts = {
            'name': '* required',
        }