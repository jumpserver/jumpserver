# ~*~ coding: utf-8 ~*~

from django.forms import ModelForm
from django import forms
from captcha.fields import CaptchaField
from django.utils.translation import gettext_lazy as _

from .models import User, UserGroup


class UserLoginForm(forms.Form):
    username = forms.CharField(label=_('Username'), max_length=100)
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput, max_length=100)
    captcha = CaptchaField()


class UserAddForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'name', 'email', 'groups', 'wechat',
            'phone', 'enable_otp', 'role', 'date_expired', 'comment',
        ]

        help_texts = {
            'username': '* required',
            'email': '* required',
        }

        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Join usergroups')}),
        }


class UserUpdateForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'name', 'email', 'groups', 'wechat',
            'phone', 'enable_otp', 'role', 'date_expired', 'comment',
        ]

        help_texts = {
            'username': '* required',
            'email': '* required',
            'groups': '* required'
        }

        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Join usergroups')}),
        }


class UserGroupForm(ModelForm):
    class Meta:
        model = UserGroup

        fields = [
            'name', 'comment',
        ]

        help_texts = {
            'name': '* required'
        }
