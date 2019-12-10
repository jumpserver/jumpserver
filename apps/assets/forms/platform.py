# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..models import Platform


__all__ = ['PlatformForm', 'PlatformMetaForm']


class PlatformMetaForm(forms.Form):
    SECURITY_CHOICES = (
        ('rdp', "RDP"),
        ('nla', "NLA"),
        ('tls', 'TLS'),
        ('any', "Any"),
    )
    CONSOLE_CHOICES = (
        (True, _('Yes')),
        (False, _('No')),
    )
    security = forms.ChoiceField(
        choices=SECURITY_CHOICES, initial='any', label=_("RDP security"),
        required=False,
    )
    console = forms.ChoiceField(
        choices=CONSOLE_CHOICES, initial=False, label=_("RDP console"),
        required=False,
    )


class PlatformForm(forms.ModelForm):
    class Meta:
        model = Platform
        fields = [
            'name', 'base', 'comment',
        ]
        labels = {
            'base': _("Base platform")
        }

