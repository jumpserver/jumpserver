# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..models import Platform


__all__ = ['PlatformForm']


class PlatformForm(forms.ModelForm):
    class Meta:
        model = Platform
        fields = [
            'name', 'base', 'comment',
        ]
        labels = {
            'base': _("Base platform")
        }
