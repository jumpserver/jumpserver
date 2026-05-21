from django import forms
from django.utils.translation import gettext_lazy as _


class CertLoginForm(forms.Form):
    username = forms.CharField(
        label=_('Username'), max_length=100, required=True,
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

