from django import forms
from django.utils.translation import gettext_lazy as _


class UKeyLoginForm(forms.Form):
    username = forms.CharField(
        required=True,
        label=_('Username'), 
        widget=forms.HiddenInput(),
    )
    cert = forms.CharField(
        required=True,
        widget=forms.HiddenInput(),
    )
    signature = forms.CharField(
        required=True,
        widget=forms.HiddenInput(),
    )
    ukey_sn = forms.CharField(
        required=True,
        widget=forms.HiddenInput(),
    )

