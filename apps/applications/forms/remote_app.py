#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django import forms

from orgs.mixins.forms import OrgModelForm

from ..models import RemoteApp


__all__ = [
    'RemoteAppChromeForm', 'RemoteAppMySQLWorkbenchForm',
    'RemoteAppVMwareForm', 'RemoteAppCustomForm'
]


class BaseRemoteAppForm(OrgModelForm):
    default_initial_data = {}

    def __init__(self, *args, **kwargs):
        # 过滤RDP资产和系统用户
        super().__init__(*args, **kwargs)
        field_asset = self.fields['asset']
        field_asset.queryset = field_asset.queryset.has_protocol('rdp')
        self.fields['type'].widget.attrs['disabled'] = True
        self.fields.move_to_end('comment')
        self.initial_default()

    def initial_default(self):
        for name, value in self.default_initial_data.items():
            field = self.fields.get(name)
            if not field:
                continue
            field.initial = value

    class Meta:
        model = RemoteApp
        fields = [
            'name', 'asset', 'type', 'path', 'comment'
        ]
        widgets = {
            'asset': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Asset')
            }),
        }


class RemoteAppChromeForm(BaseRemoteAppForm):
    default_initial_data = {
        'path': r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    }

    chrome_target = forms.CharField(
        max_length=128, label=_('Target URL'), required=False
    )
    chrome_username = forms.CharField(
        max_length=128, label=_('Login username'), required=False
    )
    chrome_password = forms.CharField(
        widget=forms.PasswordInput, strip=True,
        max_length=128, label=_('Login password'), required=False
    )


class RemoteAppMySQLWorkbenchForm(BaseRemoteAppForm):
    default_initial_data = {
        'path': r'C:\Program Files\MySQL\MySQL Workbench 8.0 CE'
                r'\MySQLWorkbench.exe'
    }

    mysql_workbench_ip = forms.CharField(
        max_length=128, label=_('Database IP'), required=False
    )
    mysql_workbench_name = forms.CharField(
        max_length=128, label=_('Database name'), required=False
    )
    mysql_workbench_username = forms.CharField(
        max_length=128, label=_('Database username'), required=False
    )
    mysql_workbench_password = forms.CharField(
        widget=forms.PasswordInput, strip=True,
        max_length=128, label=_('Database password'), required=False
    )


class RemoteAppVMwareForm(BaseRemoteAppForm):
    default_initial_data = {
        'path': r'C:\Program Files (x86)\VMware\Infrastructure'
                r'\Virtual Infrastructure Client\Launcher\VpxClient.exe'
    }

    vmware_target = forms.CharField(
        max_length=128, label=_('Target address'), required=False
    )
    vmware_username = forms.CharField(
        max_length=128, label=_('Login username'), required=False
    )
    vmware_password = forms.CharField(
        widget=forms.PasswordInput, strip=True,
        max_length=128, label=_('Login password'), required=False
    )


class RemoteAppCustomForm(BaseRemoteAppForm):

    custom_cmdline = forms.CharField(
        max_length=128, label=_('Operating parameter'), required=False
    )
    custom_target = forms.CharField(
        max_length=128, label=_('Target address'), required=False
    )
    custom_username = forms.CharField(
        max_length=128, label=_('Login username'), required=False
    )
    custom_password = forms.CharField(
        widget=forms.PasswordInput, strip=True,
        max_length=128, label=_('Login password'), required=False
    )

