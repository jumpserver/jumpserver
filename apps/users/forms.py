# ~*~ coding: utf-8 ~*~

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from captcha.fields import CaptchaField

from .models import User, UserGroup


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(label=_('Username'), max_length=100)
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput, max_length=100,
        strip=False)
    captcha = CaptchaField()


class UserCreateForm(forms.ModelForm):

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
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Join user groups')}),
        }


class UserUpdateForm(forms.ModelForm):

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
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Join user groups')}),
        }


class UserGroupForm(forms.ModelForm):

    class Meta:
        model = UserGroup

        fields = [
            'name', 'comment',
        ]

        help_texts = {
            'name': '* required'
        }


class UserInfoForm(forms.Form):
    name = forms.CharField(max_length=20, label=_('name'))
    avatar = forms.ImageField(label=_('avatar'), required=False)
    wechat = forms.CharField(max_length=30, label=_('wechat'), required=False)
    phone = forms.CharField(max_length=20, label=_('phone'), required=False)
    enable_otp = forms.BooleanField(required=False, label=_('enable otp'))


class UserKeyForm(forms.Form):
    private_key = forms.CharField(max_length=5000, widget=forms.Textarea, label=_('private key'))

    def clean_private_key(self):
        from users.utils import validate_ssh_pk
        ssh_pk = self.cleaned_data['private_key']
        checked, reason = validate_ssh_pk(ssh_pk)
        if not checked:
            raise forms.ValidationError(_('Not a valid ssh private key.'))
        return ssh_pk
