# coding:utf-8
from django import forms

from jasset.models import IDC, Asset, AssetGroup


class AssetForm(forms.ModelForm):
    active_choice = (
        (1, "激活"),
        (0, "禁用")
    )
    is_active = forms.ChoiceField(
        label=u"是否激活", required=True, initial = 1,
        widget=forms.RadioSelect, choices=active_choice
    )

    class Meta:
        model = Asset
        fields = [
            "ip", "second_ip", "hostname", "port", "group", "username", "password", "use_default_auth",
            "idc", "mac", "remote_ip", "brand", "cpu", "memory", "disk", "system_type", "system_version",
            "cabinet", "position", "number", "status", "asset_type", "env", "sn", "is_active", "comment"
        ]


class AssetGroupForm(forms.ModelForm):
    class Meta:
        model = AssetGroup
        fields = [
            "name", "comment"
        ]
