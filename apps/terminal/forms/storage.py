# coding: utf-8
# 

from django import forms
from django.utils.translation import ugettext_lazy as _

from terminal.models import ReplayStorage, CommandStorage


__all__ = [
    'ReplayStorageAzureForm', 'ReplayStorageOSSForm', 'ReplayStorageS3Form',
    'ReplayStorageCephForm', 'ReplayStorageSwiftForm',
    'CommandStorageTypeESForm',
]


class BaseStorageForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(BaseStorageForm, self).__init__(*args, **kwargs)
        self.fields['type'].widget.attrs['disabled'] = True
        self.fields.move_to_end('comment')


class BaseReplayStorageForm(BaseStorageForm, forms.ModelForm):

    class Meta:
        model = ReplayStorage
        fields = ['name', 'type', 'comment']


class BaseCommandStorageForm(BaseStorageForm, forms.ModelForm):

    class Meta:
        model = CommandStorage
        fields = ['name', 'type', 'comment']


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


class ReplayStorageCephForm(BaseReplayStorageForm):
    ceph_bucket = forms.CharField(
        max_length=128, label=_('Bucket'), required=False
    )
    ceph_access_key = forms.CharField(
        max_length=128, label=_('Access key'), required=False,
        widget=forms.PasswordInput
    )
    ceph_secret_key = forms.CharField(
        max_length=128, label=_('Secret key'), required=False,
        widget=forms.PasswordInput
    )
    ceph_endpoint = forms.CharField(
        max_length=128, label=_('Endpoint'), required=False,
        help_text=_(
            """
            S3: http://s3.{REGION_NAME}.amazonaws.com <br>
            S3(China): http://s3.{REGION_NAME}.amazonaws.com.cn <br>
            Example: http://s3.cn-north-1.amazonaws.com.cn
            """
        )
    )


class ReplayStorageSwiftForm(BaseReplayStorageForm):
    swift_bucket = forms.CharField(
        max_length=128, label=_('Bucket'), required=False
    )
    swift_access_key = forms.CharField(
        max_length=128, label=_('Access key'), required=False,
        widget=forms.PasswordInput
    )
    swift_secret_key = forms.CharField(
        max_length=128, label=_('Secret key'), required=False,
        widget=forms.PasswordInput
    )
    swift_region = forms.CharField(
        max_length=128, label=_('Region'), required=False,
    )
    swift_endpoint = forms.CharField(
        max_length=128, label=_('Endpoint'), required=False,
    )


class CommandStorageTypeESForm(BaseCommandStorageForm):
    es_hosts = forms.CharField(
        max_length=128, label=_('Hosts'), required=False,
        help_text=_(
            """
            Tips: If there are multiple hosts, separate them with a comma (,) 
            <br>
            eg: http://www.jumpserver.a.com,http://www.jumpserver.b.com
            """
        )
    )
    es_index = forms.CharField(
        max_length=128, label=_('Index'), required=False
    )
    es_doc_type = forms.CharField(
        max_length=128, label=_('Doc type'), required=False
    )
