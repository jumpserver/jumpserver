# ~*~ coding: utf-8 ~*~

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import *


class UserCreateUpdateForm(forms.ModelForm):
    class Meta:
        model = InstallConfig
        fields = [
            'username', 'name', 'email', 'groups', 'wechat',
            'phone', 'enable_otp', 'role', 'date_expired', 'comment',
        ]
        help_texts = {
            'username': '* required',
            'name': '* required',
            'email': '* required',
        }
        widgets = {
            'groups': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Join user groups')}),
        }
