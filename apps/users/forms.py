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
            'groups': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Join user groups')}),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'name', 'email',
            'wechat', 'phone',
        ]
        help_texts = {
            'username': '* required',
            'name': '* required',
            'email': '* required',
        }


class UserPasswordForm(forms.Form):
    old_password = forms.CharField(
        max_length=128, widget=forms.PasswordInput)
    new_password = forms.CharField(
        min_length=5, max_length=128, widget=forms.PasswordInput)
    confirm_password = forms.CharField(
        min_length=5, max_length=128, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super(UserPasswordForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data['old_password']
        if not self.instance.check_password(old_password):
            raise forms.ValidationError(_('Old password error'))
        return old_password

    def clean_confirm_password(self):
        new_password = self.cleaned_data['new_password']
        confirm_password = self.cleaned_data['confirm_password']

        if new_password != confirm_password:
            raise forms.ValidationError(_('Password does not match'))
        return confirm_password

    def save(self):
        password = self.cleaned_data['new_password']
        self.instance.set_password(password)
        self.instance.save()
        return self.instance


class UserPublicKeyForm(forms.Form):
    public_key = forms.CharField(
        label=_('ssh public key'), max_length=5000,
        widget=forms.Textarea(attrs={'placeholder': _('ssh-rsa AAAA...')}),
        help_text=_('Paste your id_rsa.pub here.'))

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            self.instance = kwargs.pop('instance')
        else:
            self.instance = None
        super(UserPublicKeyForm, self).__init__(*args, **kwargs)

    def clean_public_key(self):
        public_key = self.cleaned_data['public_key']
        if self.instance.public_key and public_key == self.instance.public_key:
            raise forms.ValidationError(_('Public key should not be the '
                                          'same as your old one.'))

        if not validate_ssh_public_key(public_key):
            raise forms.ValidationError(_('Not a valid ssh public key'))
        return public_key

    def save(self):
        public_key = self.cleaned_data['public_key']
        self.instance.public_key = public_key
        self.instance.save()
        return self.instance


class UserBulkUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(
        label=_('Role'),
        choices=[('Admin', 'Administrator'), ('User', 'User')],
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        label=_('Select users'),
        required=False,
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select users')
            }
        )
    )

    class Meta:
        model = User
        fields = ['users', 'role', 'groups', 'date_expired', 'is_active', 'enable_otp']
        widgets = {
            'groups': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select user groups')}),
        }

    def save(self, commit=True):
        cleaned_data = {k: v for k, v in self.cleaned_data.items() if
                        v is not None}
        users = cleaned_data.pop('users')
        groups = cleaned_data.pop('groups')
        users.update(**cleaned_data)
        if groups:
            for user in users:
                user.groups.set(groups)
        return users


class UserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = [
            'name', 'comment'
        ]
        help_texts = {
            'name': '* required'
        }


class UserPrivateAssetPermissionForm(forms.ModelForm):
    def save(self, commit=True):
        self.instance = super(UserPrivateAssetPermissionForm, self)\
            .save(commit=commit)
        self.instance.users = [self.user]
        self.instance.save()
        return self.instance

    class Meta:
        model = AssetPermission
        fields = [
            'assets', 'asset_groups', 'system_users', 'name',
        ]
        widgets = {
            'assets': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select assets')}),
            'asset_groups': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select asset groups')}),
            'system_users': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select system users')}),
        }


class UserGroupPrivateAssetPermissionForm(forms.ModelForm):
    def save(self, commit=True):
        self.instance = super(UserGroupPrivateAssetPermissionForm, self)\
            .save(commit=commit)
        self.instance.user_groups = [self.user_group]
        self.instance.save()
        return self.instance

    class Meta:
        model = AssetPermission
        fields = [
            'assets', 'asset_groups', 'system_users', 'name',
        ]
        widgets = {
            'assets': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select assets')}),
            'asset_groups': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select asset groups')}),
            'system_users': forms.SelectMultiple(
                attrs={'class': 'select2',
                       'data-placeholder': _('Select system users')}),
        }


class FileForm(forms.Form):
    file = forms.FileField()
