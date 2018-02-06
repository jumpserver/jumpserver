# coding:utf-8
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Cluster, Asset, AssetGroup, AdminUser, SystemUser, Label
from common.utils import validate_ssh_private_key, ssh_pubkey_gen, ssh_key_gen, get_logger

logger = get_logger(__file__)


class AssetCreateForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'public_ip', 'port',  'comment', 'cluster',
            'nodes', 'is_active', 'admin_user', 'labels',

        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Select nodes')
            }),
            'cluster': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Select cluster')
            }),
            'admin_user': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Select admin user')
            }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Select labels')
            }),
            'port': forms.TextInput(),
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'port': '* required',
            'cluster': '* required',
            'admin_user': _('Host level admin user, If not set using cluster admin user default')
        }

    def clean_admin_user(self):
        cluster = self.cleaned_data.get('cluster')
        admin_user = self.cleaned_data.get('admin_user')
        if not admin_user and (cluster and not cluster.admin_user):
            raise forms.ValidationError(_("You need set a admin user if cluster not have"))
        return self.cleaned_data['admin_user']

    def is_valid(self):
        print(self.data)
        result = super().is_valid()
        if not result:
            print(self.errors)
            print(self.cleaned_data)
        return result


class AssetUpdateForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'port', 'nodes', "cluster", 'is_active',
            'public_ip', 'number', 'comment', 'admin_user', 'labels',
        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Select nodes')
            }),
            'cluster': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Select cluster')
            }),
            'admin_user': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Select admin user')
            }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Select labels')
            }),
            'port': forms.TextInput(),
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'port': '* required',
            'cluster': '* required',
            'admin_user': _('Host level admin user, If not set using cluster admin user default')
        }

    def clean_admin_user(self):
        cluster = self.cleaned_data.get('cluster')
        admin_user = self.cleaned_data.get('admin_user')
        if not admin_user and (cluster and not cluster.admin_user):
            raise forms.ValidationError(_("You need set a admin user if cluster not have"))
        return self.cleaned_data['admin_user']


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
    cluster = forms.ModelChoiceField(
        required=False, label=_("Cluster"), queryset=Cluster.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select cluster')
            }
        )
    )

    class Meta:
        model = Asset
        fields = [
            'assets', 'port', 'groups', "cluster", 'labels'
        ]
        widgets = {
            'groups': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Select asset groups')}
            ),
            'labels': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Select labels')}
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
        groups = cleaned_data.pop('groups', [])
        labels = cleaned_data.pop('labels', [])
        assets = Asset.objects.filter(id__in=[asset.id for asset in assets])
        assets.update(**cleaned_data)
        if groups:
            for asset in assets:
                asset.groups.set(groups)
        if labels:
            for asset in assets:
                asset.labels.set(labels)
        return assets


class AssetGroupForm(forms.ModelForm):
    # See AdminUserForm comment same it
    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.all(),
        label=_('Asset'),
        required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select assets')}
        )
    )

    def __init__(self, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            initial = kwargs.get('initial', {})
            initial.update({
                'assets': instance.assets.all(),
            })
            kwargs['initial'] = initial
        super().__init__(**kwargs)

    def save(self, commit=True):
        group = super().save(commit=commit)
        assets = self.cleaned_data['assets']
        group.assets.set(assets)
        return group

    class Meta:
        model = AssetGroup
        fields = [
            "name", "comment",
        ]
        help_texts = {
            'name': '* required',
        }


class ClusterForm(forms.ModelForm):
    system_users = forms.ModelMultipleChoiceField(
        queryset=SystemUser.objects.all(),
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select system users')}
        ),
        label=_('System users'),
        required=False,
        help_text=_("Selected system users will be create at cluster assets"),
    )

    class Meta:
        model = Cluster
        fields = ['name', "bandwidth", "operator", 'contact', 'admin_user', 'system_users',
                  'phone', 'address', 'intranet', 'extranet', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Name')}),
            'intranet': forms.Textarea(attrs={'placeholder': 'IP段之间用逗号隔开，如：192.168.1.0/24,192.168.1.0/24'}),
            'extranet': forms.Textarea(attrs={'placeholder': 'IP段之间用逗号隔开，如：201.1.32.1/24,202.2.32.1/24'})
        }
        help_texts = {
            'name': '* required',
            'admin_user': _("Cluster level admin user"),
        }

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            initial = kwargs.get('initial', {})
            initial['system_users'] = kwargs['instance'].systemuser_set.all()
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=commit)
        system_users = self.cleaned_data['system_users']
        instance.systemuser_set.set(system_users)
        return instance


class PasswordAndKeyAuthForm(forms.ModelForm):
    # Form field name can not start with `_`, so redefine it,
    password = forms.CharField(
        widget=forms.PasswordInput, max_length=128,
        strip=True, required=False,
        help_text=_('Password or private key passphrase'),
        label=_("Password"),
    )
    # Need use upload private key file except paste private key content
    private_key_file = forms.FileField(required=False, label=_("Private key"))

    def clean_private_key_file(self):
        private_key_file = self.cleaned_data['private_key_file']
        password = self.cleaned_data['password']

        if private_key_file:
            key_string = private_key_file.read()
            private_key_file.seek(0)
            if not validate_ssh_private_key(key_string, password):
                raise forms.ValidationError(_('Invalid private key'))
        return private_key_file

    def validate_password_key(self):
        password = self.cleaned_data['password']
        private_key_file = self.cleaned_data.get('private_key_file', '')

        if not password and not private_key_file:
            raise forms.ValidationError(_(
                'Password and private key file must be input one'
            ))

    def gen_keys(self):
        password = self.cleaned_data.get('password', '') or None
        private_key_file = self.cleaned_data['private_key_file']
        public_key = private_key = None

        if private_key_file:
            private_key = private_key_file.read().strip().decode('utf-8')
            public_key = ssh_pubkey_gen(private_key=private_key, password=password)
        return private_key, public_key


class AdminUserForm(PasswordAndKeyAuthForm):
    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        admin_user = super().save(commit=commit)
        password = self.cleaned_data.get('password', '') or None
        private_key, public_key = super().gen_keys()
        admin_user.set_auth(password=password, public_key=public_key, private_key=private_key)
        return admin_user

    def clean(self):
        super().clean()
        if not self.instance:
            super().validate_password_key()

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


class SystemUserForm(PasswordAndKeyAuthForm):
    # Admin user assets define, let user select, save it in form not in view
    auto_generate_key = forms.BooleanField(initial=True, required=False)

    def save(self, commit=True):
        # Because we define custom field, so we need rewrite :method: `save`
        system_user = super().save()
        password = self.cleaned_data.get('password', '') or None
        auto_generate_key = self.cleaned_data.get('auto_generate_key', False)
        private_key, public_key = super().gen_keys()

        if auto_generate_key:
            logger.info('Auto generate key and set system user auth')
            system_user.auto_gen_auth()
        else:
            system_user.set_auth(password=password, private_key=private_key, public_key=public_key)
        return system_user

    def clean(self):
        super().clean()
        auto_generate = self.cleaned_data.get('auto_generate_key')
        if not self.instance and not auto_generate:
            super().validate_password_key()

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
                attrs={
                    'class': 'select2',
                    'data-placeholder': _(' Select clusters')
                }
            ),
        }
        help_texts = {
            'name': '* required',
            'username': '* required',
            'cluster': _('If auto push checked, system user will be create at cluster assets'),
            'auto_push': _('Auto push system user to asset'),
            'priority': _('High level will be using login asset as default, if user was granted more than 2 system user'),
        }


class FileForm(forms.Form):
    file = forms.FileField()


class LabelForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.all(), label=_('Asset'), required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select assets')}
        )
    )

    class Meta:
        model = Label
        fields = ['name', 'value', 'assets']

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].assets.all()
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        label = super().save(commit=commit)
        assets = self.cleaned_data['assets']
        label.assets.set(assets)
        return label
