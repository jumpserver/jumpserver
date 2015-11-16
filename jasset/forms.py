# coding:utf-8
from django import forms

from jasset.models import IDC, Asset, AssetGroup


class AssetForm(forms.ModelForm):

    class Meta:
        model = Asset

        fields = [
            "ip", "other_ip", "hostname", "port", "group", "username", "password", "use_default_auth",
            "idc", "mac", "remote_ip", "brand", "cpu", "memory", "disk", "system_type", "system_version",
            "cabinet", "position", "number", "status", "asset_type", "env", "sn", "is_active", "comment"
        ]


class AssetGroupForm(forms.ModelForm):
    class Meta:
        model = AssetGroup
        fields = [
            "name", "comment"
        ]


class IdcForm(forms.ModelForm):
    class Meta:
        model = IDC
        fields = ['name', "bandwidth", "operator", 'linkman', 'phone', 'address', 'network', 'comment']


