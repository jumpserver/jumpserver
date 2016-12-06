# ~*~ coding: utf-8 ~*~

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from captcha.fields import CaptchaField

from common.utils import validate_ssh_public_key
from perms.models import AssetPermission
from .models import User, UserGroup


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(label=_('Username'), max_length=100)
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput, max_length=100,
        strip=False)
    captcha = CaptchaField()


class UserCreateUpdateForm(forms.ModelForm):
    class Meta:
        model = User
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
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Join user groups')}),
        }


class UserBulkImportForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'enable_otp', 'role']


# class UserUpdateForm(forms.ModelForm):
#
#     class Meta:
#         model = User
#         fields = [
#             'name', 'email', 'groups', 'wechat',
#             'phone', 'enable_otp', 'role', 'date_expired', 'comment',
#         ]
#         help_texts = {
#             'username': '* required',
#             'email': '* required',
#             'groups': '* required'
#         }
#         widgets = {
#             'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': _('Join user groups')}),
#         }


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
    public_key = forms.CharField(
        label=_('ssh public key'), max_length=5000,
        widget=forms.Textarea(attrs={'placeholder': _('ssh-rsa AAAA...')}),
        help_text=_('Paste your id_rsa.pub here.'))

    def clean_public_key(self):
        public_key = self.cleaned_data['public_key']
        if self.user.public_key and public_key == self.user.public_key:
            raise forms.ValidationError(_('Public key should not be the same as your old one.'))

        if not validate_ssh_public_key(public_key):
            raise forms.ValidationError(_('Not a valid ssh public key'))
        return public_key


class UserPrivateAssetPermissionForm(forms.ModelForm):

    def save(self, commit=True):
        self.instance = super(UserPrivateAssetPermissionForm, self).save(commit=commit)
        self.instance.users = [self.user]
        self.instance.save()
        return self.instance

    class Meta:
        model = AssetPermission
        fields = [
            'assets', 'asset_groups', 'system_users', 'name',
        ]
        widgets = {
            'assets': forms.SelectMultiple(attrs={'class': 'select2',
                                                  'data-placeholder': _('Select assets')}),
            'asset_groups': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select asset groups')}),
            'system_users': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select system users')}),
        }


class UserGroupPrivateAssetPermissionForm(forms.ModelForm):

    def save(self, commit=True):
        self.instance = super(UserGroupPrivateAssetPermissionForm, self).save(commit=commit)
        self.instance.user_groups = [self.user_group]
        self.instance.save()
        return self.instance

    class Meta:
        model = AssetPermission
        fields = [
            'assets', 'asset_groups', 'system_users', 'name',
        ]
        widgets = {
            'assets': forms.SelectMultiple(attrs={'class': 'select2',
                                                  'data-placeholder': _('Select assets')}),
            'asset_groups': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select asset groups')}),
            'system_users': forms.SelectMultiple(attrs={'class': 'select2',
                                                        'data-placeholder': _('Select system users')}),
        }


class FileForm(forms.Form):
    file = forms.FileField()
