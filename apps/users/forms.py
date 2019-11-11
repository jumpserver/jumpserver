# ~*~ coding: utf-8 ~*~

from django import forms
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from common.utils import validate_ssh_public_key
from orgs.mixins.forms import OrgModelForm
from .models import User, UserGroup
from .utils import check_password_rules, get_current_org_members


class UserCheckPasswordForm(forms.Form):
    username = forms.CharField(label=_('Username'), max_length=100)
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=128, strip=False
    )


class UserCheckOtpCodeForm(forms.Form):
    otp_code = forms.CharField(label=_('MFA code'), max_length=6)


def get_source_choices():
    choices_all = dict(User.SOURCE_CHOICES)
    choices = [
        (User.SOURCE_LOCAL, choices_all[User.SOURCE_LOCAL]),
    ]
    if settings.AUTH_LDAP:
        choices.append((User.SOURCE_LDAP, choices_all[User.SOURCE_LDAP]))
    if settings.AUTH_OPENID:
        choices.append((User.SOURCE_OPENID, choices_all[User.SOURCE_OPENID]))
    if settings.AUTH_RADIUS:
        choices.append((User.SOURCE_RADIUS, choices_all[User.SOURCE_RADIUS]))
    return choices


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
    source = forms.ChoiceField(
        choices=get_source_choices, required=True,
        initial=User.SOURCE_LOCAL, label=_("Source")
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
            'source', 'phone', 'role', 'date_expired',
            'comment', 'otp_level'
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
            roles.append((User.ROLE_AUDITOR, dict(User.ROLE_CHOICES).get(User.ROLE_AUDITOR)))

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

    def clean_password(self):
        password_strategy = self.data.get('password_strategy')
        # 创建-不设置密码
        if password_strategy == '0':
            return
        password = self.data.get('password')
        # 更新-密码为空
        if password_strategy is None and not password:
            return
        if not check_password_rules(password):
            msg = _('* Your password does not meet the requirements')
            raise forms.ValidationError(msg)
        return password

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
        'When enabled, '
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
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'users-select2',
                'data-placeholder': _('Select users')
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        users_field = self.fields['users']
        users_field.queryset = get_current_org_members()

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


class UserGroupForm(OrgModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label=_("User"),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'users-select2',
                'data-placeholder': _('Select users')
            }
        ),
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        users_field = self.fields.get('users')
        if self.instance:
            users_field.initial = self.instance.users.all()
            users_field.queryset = self.instance.users.all()
        else:
            users_field.queryset = User.objects.none()

    def save(self, commit=True):
        raise Exception("Save by restful api")

    class Meta:
        model = UserGroup
        fields = [
            'name', 'users', 'comment',
        ]


class FileForm(forms.Form):
    file = forms.FileField()
