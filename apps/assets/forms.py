# coding:utf-8
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Cluster, Asset, AssetGroup, AdminUser, SystemUser
from common.utils import validate_ssh_private_key, ssh_pubkey_gen, ssh_key_gen, get_logger


logger = get_logger(__file__)


class AssetCreateForm(forms.ModelForm):

    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'public_ip', 'port', 'type', 'comment',
            'cluster', 'groups', 'status', 'env', 'is_active',
            'admin_user'

        ]
        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Select asset groups')}),
            'cluster': forms.Select(attrs={'class': 'select2', 'data-placeholder': _('Select cluster')}),
            'admin_user': forms.Select(attrs={'class': 'select2', 'data-placeholder': _('Select admin user')}),
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'port': '* required',
            'cluster': '* required',
            'admin_user': _('Host level admin user, If not set using cluster admin user default')
        }


class AssetUpdateForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'port', 'groups', "cluster", 'is_active',
            'type', 'env', 'status', 'public_ip', 'remote_card_ip', 'cabinet_no',
            'cabinet_pos', 'number', 'comment', 'admin_user',
        ]
        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Select asset groups')}),
            'admin_user': forms.Select(attrs={'class': 'select2', 'data-placeholder': _("Default using cluster admin user")})
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'port': '* required',
            'cluster': '* required',
            'admin_user': _('Host level admin user, If not set using cluster admin user default')
        }


class AssetBulkUpdateForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(
        required=True,
        help_text='* required',
        label=_('Select assets'),
        queryset=Asset.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select assets')
            }
        )
    )
    port = forms.IntegerField(
        label=_('Port'),
        required=False,
        min_value=1,
        max_value=65535,
    )

    class Meta:
        model = Asset
        fields = [
            'assets', 'port', 'groups', "cluster",
            'type', 'env', 'status',
        ]
        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Select asset groups')}),
        }

    def save(self, commit=True):
        changed_fields = []
        for field in self._meta.fields:
            if self.data.get(field) is not None:
                changed_fields.append(field)

        cleaned_data = {k: v for k, v in self.cleaned_data.items()
                        if k in changed_fields}
        assets = cleaned_data.pop('assets')
        groups = cleaned_data.pop('groups', [])
        assets = Asset.objects.filter(id__in=[asset.id for asset in assets])
        assets.update(**cleaned_data)
        if groups:
            for asset in assets:
                asset.groups.set(groups)
        return assets


class AssetGroupForm(forms.ModelForm):
    # See AdminUserForm comment same it
    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.all(),
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
            "name", "comment",
        ]
        help_texts = {
            'name': '* required',
        }


class ClusterForm(forms.ModelForm):

    class Meta:
        model = Cluster
        fields = ['name', "bandwidth", "operator", 'contact', 'admin_user',
                  'phone', 'address', 'intranet', 'extranet', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'intranet': forms.Textarea(attrs={'placeholder': 'IP段之间用逗号隔开，如：192.168.1.0/24,192.168.1.0/24'}),
            'extranet': forms.Textarea(attrs={'placeholder': 'IP段之间用逗号隔开，如：201.1.32.1/24,202.2.32.1/24'})
        }
        help_texts = {
            'name': '* required',
            'admin_user': 'The assets of this cluster will use this admin user as his admin user',
        }


class AdminUserForm(forms.ModelForm):
    # Form field name can not start with `_`, so redefine it,
    password = forms.CharField(
        widget=forms.PasswordInput, max_length=128,
        strip=True, required=False,
        help_text=_('If also set private key, use that first'),
    )
    # Need use upload private key file except paste private key content
    private_key_file = forms.FileField(required=False)

    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        admin_user = super().save(commit=commit)
        password = self.cleaned_data['password']
        private_key = self.cleaned_data['private_key_file']
        public_key = None

        if not password:
            password = None

        if private_key:
            public_key = ssh_pubkey_gen(private_key, password=password)

        admin_user.set_auth(password=password, public_key=public_key, private_key=private_key)
        return admin_user

    def clean_private_key_file(self):
        private_key_file = self.cleaned_data['private_key_file']
        password = self.cleaned_data['password']

        if private_key_file:
            private_key = private_key_file.read()
            if not validate_ssh_private_key(private_key, password):
                raise forms.ValidationError(_('Invalid private key'))
            return private_key
        return private_key_file

    def clean(self):
        password = self.cleaned_data['password']
        private_key_file = self.cleaned_data.get('private_key_file', '')

        if not self.instance and not (password or private_key_file):
            raise forms.ValidationError(
                _('Password and private key file must be input one'))

    class Meta:
        model = AdminUser
        fields = ['name', 'username', 'password',
                  'private_key_file', 'comment']
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
    auto_generate_key = forms.BooleanField(initial=True, required=False)
    # Form field name can not start with `_`, so redefine it,
    password = forms.CharField(widget=forms.PasswordInput, required=False, max_length=128, strip=True)
    # Need use upload private key file except paste private key content
    private_key_file = forms.FileField(required=False)

    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        system_user = super().save()
        password = self.cleaned_data.get('password', None)
        private_key_file = self.cleaned_data.get('private_key_file')
        auto_generate_key = self.cleaned_data.get('auto_generate_key')
        private_key = None
        public_key = None

        if auto_generate_key:
            logger.info('Auto set system user auth')
            system_user.auto_gen_auth()
        else:
            if private_key_file:
                private_key = private_key_file.read().strip().decode('utf-8')
                public_key = ssh_pubkey_gen(private_key=private_key)
            system_user.set_auth(password=password, private_key=private_key, public_key=public_key)
        return system_user

    def clean_private_key_file(self):
        if self.cleaned_data.get('private_key_file'):
            key_string = self.cleaned_data['private_key_file'].read()
            self.cleaned_data['private_key_file'].seek(0)
            if not validate_ssh_private_key(key_string):
                raise forms.ValidationError(_('Invalid private key'))
        return self.cleaned_data['private_key_file']

    def clean_password(self):
        if not self.cleaned_data.get('password') and \
                not self.cleaned_data.get('private_key_file') and \
                not self.cleaned_data.get('auto_generate_key'):
            raise forms.ValidationError(_('Auth info required, private_key or password'))
        return self.cleaned_data['password']

    class Meta:
        model = SystemUser
        fields = [
            'name', 'username', 'protocol', 'auto_generate_key',
            'password', 'private_key_file', 'auto_push', 'sudo',
            'comment', 'shell', 'cluster', 'priority',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'username': forms.TextInput(attrs={'placeholder': _('Username')}),
            'cluster': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _(' Select clusters')}),
        }
        help_texts = {
            'name': '* required',
            'username': '* required',
            'cluster': 'If auto push checked, system user will be create at cluster assets',
            'auto_push': 'Auto push system user to asset',
            'priority': 'High level will be using login asset as default, if user was granted more than 2 system user',
        }


class SystemUserUpdateForm(SystemUserForm):
    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        password = self.cleaned_data.get('password', None)
        private_key_file = self.cleaned_data.get('private_key_file')
        system_user = super(forms.ModelForm, self).save()

        if private_key_file:
            print(private_key_file)
            private_key = private_key_file.read().strip().decode('utf-8')
            public_key = ssh_pubkey_gen(private_key=private_key)
        else:
            private_key = public_key = None
        system_user.set_auth(password=password, private_key=private_key, public_key=public_key)
        return system_user

    def clean_password(self):
        return self.cleaned_data['password']


class SystemUserAuthForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, required=False, max_length=128, strip=True)
    private_key_file = forms.FileField(required=False)

    def clean_private_key_file(self):
        if self.cleaned_data.get('private_key_file'):
            key_string = self.cleaned_data['private_key_file'].read()
            self.cleaned_data['private_key_file'].seek(0)
            if not validate_ssh_private_key(key_string):
                raise forms.ValidationError(_('Invalid private key'))
        return self.cleaned_data['private_key_file']

    def clean_password(self):
        if not self.cleaned_data.get('password') and \
                not self.cleaned_data.get('private_key_file'):
            msg = _('Auth info required, private_key or password')
            raise forms.ValidationError(msg)
        return self.cleaned_data['password']

    def update(self, system_user):
        password = self.cleaned_data.get('password')
        private_key_file = self.cleaned_data.get('private_key_file')

        if private_key_file:
            private_key = private_key_file.read().strip()
            public_key = ssh_pubkey_gen(private_key=private_key)
        else:
            private_key = None
            public_key = None
        system_user.set_auth(password=password, private_key=private_key, public_key=public_key)
        return system_user


class FileForm(forms.Form):
    file = forms.FileField()
