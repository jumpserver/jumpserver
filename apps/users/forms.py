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
        label=_('Password'), widget=forms.PasswordInput,
        max_length=128, strip=False
    )
    captcha = CaptchaField()


class UserCreateUpdateForm(forms.ModelForm):
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=128, strip=False, required=False,
    )

    class Meta:
        model = User
        fields = [
            'username', 'name', 'email', 'groups', 'wechat',
            'phone', 'role', 'date_expired', 'comment', 'password'
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

    def save(self, commit=True):
        user = super().save(commit=commit)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
            user.save()
        return user


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
    users = forms.MultipleChoiceField(
        required=True,
        help_text='* required',
        label=_('Select users'),
        choices=[(user.id, user.name) for user in User.objects.all()],
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select users')
            }
        )
    )

    class Meta:
        model = User
        fields = ['users', 'role', 'groups', 'date_expired', 'is_active']
        widgets = {
            "groups": forms.SelectMultiple(
                attrs={
                    'class': 'select2',
                    'data-placeholder': _('Select users')
                }
            )
        }

    def save(self, commit=True):
        changed_fields = []
        for field in self._meta.fields:
            if self.data.get(field) is not None:
                changed_fields.append(field)

        cleaned_data = {k: v for k, v in self.cleaned_data.items()
                        if k in changed_fields}
        users_id = cleaned_data.pop('users', '')
        groups = cleaned_data.pop('groups', [])
        users = User.objects.filter(id__in=users_id)
        users.update(**cleaned_data)
        if groups:
            for user in users:
                user.groups.set(groups)
        return users


class UserGroupForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select users')
            }
        )
    )

    def __init__(self, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            initial = kwargs.get('initial', {})
            initial.update({
                'users': instance.users.all(),
            })
            kwargs['initial'] = initial
        super().__init__(**kwargs)

    def save(self, commit=True):
        group = super().save(commit=commit)
        users = self.cleaned_data['users']
        group.users.set(users)
        return group

    class Meta:
        model = UserGroup
        fields = [
            'name', 'users', 'comment'
        ]
        help_texts = {
            'name': '* required'
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
