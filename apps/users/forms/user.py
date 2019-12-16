
from django import forms
from django.utils.translation import gettext_lazy as _

from common.utils import validate_ssh_public_key
from orgs.mixins.forms import OrgModelForm
from ..models import User
from ..utils import (
    check_password_rules, get_current_org_members, get_source_choices
)


__all__ = [
    'UserCreateForm', 'UserUpdateForm', 'UserBulkUpdateForm',
    'UserCheckOtpCodeForm', 'UserCheckPasswordForm'
]


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
            'comment', 'mfa_level'
        ]
        widgets = {
            'mfa_level': forms.RadioSelect(),
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
        mfa_level = self.cleaned_data.get('mfa_level')
        public_key = self.cleaned_data.get('public_key')
        user = super().save(commit=commit)
        if password:
            user.reset_password(password)
        if mfa_level:
            user.mfa_level = mfa_level
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


class UserCheckPasswordForm(forms.Form):
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=128, strip=False
    )


class UserCheckOtpCodeForm(forms.Form):
    otp_code = forms.CharField(label=_('MFA code'), max_length=6)
