# coding: utf-8
# 

from django import forms
from django.utils.translation import ugettext_lazy as _

from terminal.models import ReplayStorage


__all__ = [
    'ReplayStorageAzureForm', 'ReplayStorageOSSForm', 'ReplayStorageS3Form',
]


class BaseReplayStorageForm(forms.ModelForm):
    disable_fields = ['type']

    def __init__(self, *args, **kwargs):
        super(BaseReplayStorageForm, self).__init__(*args, **kwargs)
        for field in self.disable_fields:
            self.fields[field].widget.attrs['disabled'] = True

    class Meta:
        model = ReplayStorage
        fields = ['name', 'type']


class ReplayStorageAzureForm(BaseReplayStorageForm):
    azure_container_name = forms.CharField(
        max_length=128, label=_('Container name'), required=False
    )
    azure_account_name = forms.CharField(
        max_length=128, label=_('Account name'), required=False
    )
    azure_account_key = forms.CharField(
        max_length=128, label=_('Account key'), required=False,
        widget=forms.PasswordInput
    )
    azure_endpoint_suffix = forms.ChoiceField(
        choices=(
            ('core.chinacloudapi.cn', 'core.chinacloudapi.cn'),
            ('core.windows.net', 'core.windows.net')
        ),
        label=_('Endpoint suffix'), required=False,
    )


class ReplayStorageOSSForm(BaseReplayStorageForm):
    oss_bucket = forms.CharField(
        max_length=128, label=_('Bucket'), required=False
    )
    oss_access_key = forms.CharField(
        max_length=128, label=_('Access key'), required=False,
        widget=forms.PasswordInput
    )
    oss_secret_key = forms.CharField(
        max_length=128, label=_('Secret key'), required=False,
        widget=forms.PasswordInput
    )
    oss_endpoint = forms.CharField(
        max_length=128, label=_('Endpoint'), required=False,
        help_text=_(
            """
            OSS: http://{REGION_NAME}.aliyuncs.com <br>
            Example: http://oss-cn-hangzhou.aliyuncs.com
            """
        )
    )


class ReplayStorageS3Form(BaseReplayStorageForm):
    s3_bucket = forms.CharField(
        max_length=128, label=_('Bucket'), required=False
    )
    s3_access_key = forms.CharField(
        max_length=128, label=_('Access key'), required=False,
        widget=forms.PasswordInput
    )
    s3_secret_key = forms.CharField(
        max_length=128, label=_('Secret key'), required=False,
        widget=forms.PasswordInput
    )
    s3_endpoint = forms.CharField(
        max_length=128, label=_('Endpoint'), required=False,
        help_text=_(
            """
            S3: http://s3.{REGION_NAME}.amazonaws.com <br>
            S3(China): http://s3.{REGION_NAME}.amazonaws.com.cn <br>
            Example: http://s3.cn-north-1.amazonaws.com.cn
            """
        )
    )
