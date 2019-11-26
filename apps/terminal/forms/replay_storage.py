# coding: utf-8
# 

from django import forms
from django.utils.translation import ugettext_lazy as _

from terminal.models import ReplayStorage


__all__ = ['ReplayStorageCreateUpdateForm']


class ReplayStorageTypeAzureForm(forms.ModelForm):
    azure_container_name = forms.CharField(
        max_length=128, label=_('Container name'), required=False
    )
    azure_account_name = forms.CharField(
        max_length=128, label=_('Account name'), required=False
    )
    azure_account_key = forms.CharField(
        max_length=128, label=_('Account key'), required=False
    )
    azure_endpoint_suffix = forms.CharField(
        max_length=128, label=_('Endpoint suffix'), required=False
    )


class ReplayStorageTypeOSSForm(forms.ModelForm):
    oss_bucket = forms.CharField(
        max_length=128, label=_('Bucket'), required=False
    )
    oss_access_key = forms.CharField(
        max_length=128, label=_('Access key'), required=False
    )
    oss_secret_key = forms.CharField(
        max_length=128, label=_('Secret key'), required=False
    )
    oss_endpoint = forms.CharField(
        max_length=128, label=_('Endpoint'), required=False
    )


class ReplayStorageTypeS3Form(forms.ModelForm):
    s3_bucket = forms.CharField(
        max_length=128, label=_('Bucket'), required=False
    )
    s3_access_key = forms.CharField(
        max_length=128, label=_('Access key'), required=False
    )
    s3_secret_key = forms.CharField(
        max_length=128, label=_('Secret key'), required=False
    )
    s3_endpoint = forms.CharField(
        max_length=128, label=_('Endpoint'), required=False
    )


class ReplayStorageTypeForms(
    ReplayStorageTypeS3Form,
    ReplayStorageTypeOSSForm,
    ReplayStorageTypeAzureForm,
):
    pass


class ReplayStorageCreateUpdateForm(ReplayStorageTypeForms, forms.ModelForm):

    class Meta:
        model = ReplayStorage
        fields = ['name', 'type']
