# ~*~ coding: utf-8 ~*~

from django import forms
from django.utils.translation import gettext_lazy as _

from common.utils import validate_ssh_public_key
from orgs.mixins import OrgModelForm
from orgs.utils import current_org
from .models import User, UserGroup


class UserCheckPasswordForm(forms.Form):
    username = forms.CharField(label=_('Username'), max_length=100)
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=128, strip=False
    )


class UserCheckOtpCodeForm(forms.Form):
    otp_code = forms.CharField(label=_('MFA code'), max_length=6)


class UserCreateUpdateFormMixin(OrgModelForm):
    role_choices = ((i, n) for i, n in User.ROLE_CHOICES if i != User.ROLE_APP)
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=128, strip=False, required=False,
    )
    role = forms.ChoiceField(
        choices=role_choices, required=True,
        initial=User.ROLE_USER, label=_("Role")
    )
    public_key = forms.CharField(
        label=_('ssh public key'), max_length=5000, required=False,
        widget=forms.Textarea(attrs={'placeholder': _('ssh-rsa AAAA...')}),
        help_text=_('Paste user id_rsa.pub here.')
    )

    class Meta:
        model = User
        fields = [
            'username', 'name', 'email', 'groups', 'wechat',
            'phone', 'role', 'date_expired', 'comment', 'otp_level'
        ]
        widgets = {
            'otp_level': forms.RadioSelect(),
            'groups': forms.SelectMultiple(
                attrs={
                    'class': 'select2',
                    'data-placeholder': _('Join user groups')
                }
            )
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(UserCreateUpdateFormMixin, self).__init__(*args, **kwargs)

        roles = []
        # Super admin user
        if self.request.user.is_superuser:
            roles.append((User.ROLE_ADMIN, dict(User.ROLE_CHOICES).get(User.ROLE_ADMIN)))
            roles.append((User.ROLE_USER, dict(User.ROLE_CHOICES).get(User.ROLE_USER)))

        # Org admin user
        else:
            user = kwargs.get('instance')
            # Update
            if user:
                role = kwargs.get('instance').role
                roles.append((role, dict(User.ROLE_CHOICES).get(role)))
            # Create
            else:
                roles.append((User.ROLE_USER, dict(User.ROLE_CHOICES).get(User.ROLE_USER)))

        field = self.fields['role']
        field.choices = set(roles)

    def clean_public_key(self):
        public_key = self.cleaned_data['public_key']
        if not public_key:
            return public_key
        if self.instance.public_key and public_key == self.instance.public_key:
            msg = _('Public key should not be the same as your old one.')
            raise forms.ValidationError(msg)

        if not validate_ssh_public_key(public_key):
            raise forms.ValidationError(_('Not a valid ssh public key'))
        return public_key

    def save(self, commit=True):
        password = self.cleaned_data.get('password')
        otp_level = self.cleaned_data.get('otp_level')
        public_key = self.cleaned_data.get('public_key')
        user = super().save(commit=commit)
        if password:
            user.reset_password(password)
        if otp_level:
            user.otp_level = otp_level
            user.save()
        if public_key:
            user.public_key = public_key
            user.save()
        return user


class UserCreateForm(UserCreateUpdateFormMixin):
    EMAIL_SET_PASSWORD = _('Reset link will be generated and sent to the user')
    CUSTOM_PASSWORD = _('Set password')
    PASSWORD_STRATEGY_CHOICES = (
        (0, EMAIL_SET_PASSWORD),
        (1, CUSTOM_PASSWORD)
    )
    password_strategy = forms.ChoiceField(
        choices=PASSWORD_STRATEGY_CHOICES, required=True, initial=0,
        widget=forms.RadioSelect(), label=_('Password strategy')
    )


class UserUpdateForm(UserCreateUpdateFormMixin):
    pass


class UserProfileForm(forms.ModelForm):
    username = forms.CharField(disabled=True)
    name = forms.CharField(disabled=True)
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
        'Tip: when enabled, '
        'you will enter the MFA binding process the next time you log in. '
        'you can also directly bind in '
        '"personal information -> quick modification -> change MFA Settings"!')

    class Meta:
        model = User
        fields = ['otp_level']
        widgets = {'otp_level': forms.RadioSelect()}
        help_texts = {
            'otp_level': _('* Enable MFA authentication '
                           'to make the account more secure.'),
        }


UserMFAForm.verbose_name = _("MFA")


class UserFirstLoginFinishForm(forms.Form):
    finish_description = _(
        'In order to protect you and your company, '
        'please keep your account, '
        'password and key sensitive information properly. '
        '(for example: setting complex password, enabling MFA authentication)'
    )


UserFirstLoginFinishForm.verbose_name = _("Finish")


class UserPasswordForm(forms.Form):
    old_password = forms.CharField(
        max_length=128, widget=forms.PasswordInput,
        label=_("Old password")
    )
    new_password = forms.CharField(
        min_length=5, max_length=128,
        widget=forms.PasswordInput,
        label=_("New password")
    )
    confirm_password = forms.CharField(
        min_length=5, max_length=128,
        widget=forms.PasswordInput,
        label=_("Confirm password")
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

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


class UserBulkUpdateForm(OrgModelForm):
    users = forms.ModelMultipleChoiceField(
        required=True,
        label=_('Select users'),
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select users')
            }
        )
    )

    class Meta:
        model = User
        fields = ['users', 'groups', 'date_expired']
        widgets = {
            "groups": forms.SelectMultiple(
                attrs={
                    'class': 'select2',
                    'data-placeholder': _('User group')
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
        users = cleaned_data.pop('users', '')
        groups = cleaned_data.pop('groups', [])
        users = User.objects.filter(id__in=[user.id for user in users])
        users.update(**cleaned_data)
        if groups:
            for user in users:
                user.groups.set(groups)
        return users


def user_limit_to():
    return {"orgs": current_org}


class UserGroupForm(OrgModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        label=_("User"),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select users')
            }
        ),
        required=False,
        limit_choices_to=user_limit_to
    )

    def __init__(self, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            initial = kwargs.get('initial', {})
            initial.update({'users': instance.users.all()})
            kwargs['initial'] = initial
        super().__init__(**kwargs)
        if 'initial' not in kwargs:
            return
        users_field = self.fields.get('users')
        if hasattr(users_field, 'queryset'):
            users_field.queryset = current_org.get_org_users()

    def save(self, commit=True):
        group = super().save(commit=commit)
        users = self.cleaned_data['users']
        group.users.set(users)
        return group

    class Meta:
        model = UserGroup
        fields = [
            'name', 'users', 'comment',
        ]


class FileForm(forms.Form):
    file = forms.FileField()
