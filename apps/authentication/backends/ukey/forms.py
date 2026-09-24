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


class CertificateUKeyLoginForm(UKeyLoginForm):
    username = forms.CharField(required=False, max_length=128, label=_('Username'), widget=forms.HiddenInput())
    cert = forms.CharField(required=True, max_length=21848, widget=forms.HiddenInput())
    signature = forms.CharField(required=True, max_length=4096, widget=forms.HiddenInput())
    ukey_sn = forms.CharField(required=True, max_length=128, widget=forms.HiddenInput())
    challenge_id = forms.CharField(required=True, min_length=43, max_length=43, widget=forms.HiddenInput())
