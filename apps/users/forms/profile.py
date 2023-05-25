# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from common.utils import validate_ssh_public_key
from authentication.forms import EncryptedField, CaptchaMixin
from ..models import User


__all__ = [
    'UserProfileForm', 'UserMFAForm', 'UserFirstLoginFinishForm',
    'UserPasswordForm', 'UserPublicKeyForm', 'FileForm',
    'UserTokenResetPasswordForm', 'UserForgotPasswordForm',
    'UserCheckPasswordForm', 'UserCheckOtpCodeForm',
    'UserForgotPasswordPreviewingForm'
]


class UserCheckPasswordForm(forms.Form):
    password = EncryptedField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=1024, strip=False
    )


class UserCheckOtpCodeForm(forms.Form):
    otp_code = forms.CharField(label=_('MFA code'), max_length=6)


class UserProfileForm(forms.ModelForm):
    username = forms.CharField(disabled=True, label=_("Username"))
    name = forms.CharField(disabled=True, label=_("Name"))
    email = forms.CharField(disabled=True)

    class Meta:
        model = User
        fields = [
            'username', 'name', 'email',
            'wechat', 'phone',
        ]


UserProfileForm.verbose_name = _("Profile")


class UserMFAForm(forms.ModelForm):

    mfa_description = _(
        'When enabled, '
        'you will enter the MFA binding process the next time you log in. '
        'you can also directly bind in '
        '"personal information -> quick modification -> change MFA Settings"!'
    )

    class Meta:
        model = User
        fields = ['mfa_level']
        widgets = {'mfa_level': forms.RadioSelect()}
        help_texts = {
            'mfa_level': _('* Enable MFA to make the account more secure.'),
        }


UserMFAForm.verbose_name = _("MFA")


class UserFirstLoginFinishForm(forms.Form):
    finish_description = _(
        'In order to protect you and your company, '
        'please keep your account, '
        'password and key sensitive information properly. '
        '(for example: setting complex password, enabling MFA)'
    )


UserFirstLoginFinishForm.verbose_name = _("Finish")


class UserTokenResetPasswordForm(forms.Form):
    new_password = EncryptedField(
        min_length=5, max_length=128,
        widget=forms.PasswordInput,
        label=_("New password")
    )
    confirm_password = EncryptedField(
        min_length=5, max_length=128,
        widget=forms.PasswordInput,
        label=_("Confirm password")
    )

    def clean_confirm_password(self):
        new_password = self.cleaned_data['new_password']
        confirm_password = self.cleaned_data['confirm_password']

        if new_password != confirm_password:
            raise forms.ValidationError(_('Password does not match'))
        return confirm_password


class UserForgotPasswordForm(forms.Form):
    email = forms.CharField(label=_("Email"), required=False)
    sms = forms.CharField(
        label=_('SMS'), required=False,
        help_text=_('The phone number must contain an area code, for example, +86')
    )
    code = forms.CharField(label=_('Verify code'), max_length=6, required=False)
    form_type = forms.ChoiceField(
        choices=[('sms', _('SMS')), ('email', _('Email'))],
        widget=forms.HiddenInput({'value': 'email'})
    )


class UserForgotPasswordPreviewingForm(CaptchaMixin):
    username = forms.CharField(label=_("Username"))


class UserPasswordForm(UserTokenResetPasswordForm):
    old_password = EncryptedField(
        max_length=128, widget=forms.PasswordInput,
        label=_("Old password")
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data['old_password']
        if not self.instance.check_password(old_password):
            raise forms.ValidationError(_('Old password error'))
        return old_password

    def save(self):
        password = self.cleaned_data['new_password']
        self.instance.reset_password(new_password=password)
        return self.instance


class UserPublicKeyForm(forms.Form):
    pubkey_description = _('Automatically configure and download the SSH key')
    public_key = forms.CharField(
        label=_('ssh public key'), max_length=5000, required=False,
        widget=forms.Textarea(attrs={'placeholder': _('ssh-rsa AAAA...')}),
        help_text=_('Paste your id_rsa.pub here.')
    )

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            self.instance = kwargs.pop('instance')
        else:
            self.instance = None
        super().__init__(*args, **kwargs)

    def clean_public_key(self):
        public_key = self.cleaned_data['public_key']
        if self.instance.public_key and public_key == self.instance.public_key:
            msg = _('Public key should not be the same as your old one.')
            raise forms.ValidationError(msg)

        if public_key and not validate_ssh_public_key(public_key):
            raise forms.ValidationError(_('Not a valid ssh public key'))
        return public_key

    def save(self):
        public_key = self.cleaned_data['public_key']
        if public_key:
            self.instance.public_key = public_key
            self.instance.save()
        return self.instance


UserPublicKeyForm.verbose_name = _("Public key")


class FileForm(forms.Form):
    file = forms.FileField()
