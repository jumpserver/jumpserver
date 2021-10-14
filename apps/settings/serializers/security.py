from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class SecurityPasswordRuleSerializer(serializers.Serializer):
    SECURITY_PASSWORD_MIN_LENGTH = serializers.IntegerField(
        min_value=6, max_value=30, required=True,
        label=_('Password minimum length')
    )
    SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH = serializers.IntegerField(
        min_value=6, max_value=30, required=True,
        label=_('Admin user password minimum length')
    )
    SECURITY_PASSWORD_UPPER_CASE = serializers.BooleanField(
        required=False, label=_('Must contain capital')
    )
    SECURITY_PASSWORD_LOWER_CASE = serializers.BooleanField(required=False, label=_('Must contain lowercase'))
    SECURITY_PASSWORD_NUMBER = serializers.BooleanField(required=False, label=_('Must contain numeric'))
    SECURITY_PASSWORD_SPECIAL_CHAR = serializers.BooleanField(required=False, label=_('Must contain special'))


class SecurityAuthSerializer(serializers.Serializer):
    SECURITY_MFA_AUTH = serializers.ChoiceField(
        choices=(
            [0, _('Disable')],
            [1, _('All users')],
            [2, _('Only admin users')],
        ),
        required=False, label=_("Global MFA auth")
    )
    SECURITY_LOGIN_LIMIT_COUNT = serializers.IntegerField(
        min_value=3, max_value=99999,
        label=_('Limit the number of login failures')
    )
    SECURITY_LOGIN_LIMIT_TIME = serializers.IntegerField(
        min_value=5, max_value=99999, required=True,
        label=_('Block logon interval'),
        help_text=_(
            'Unit: minute, If the user has failed to log in for a limited number of times, '
            'no login is allowed during this time interval.'
        )
    )
    SECURITY_PASSWORD_EXPIRATION_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=True,
        label=_('User password expiration'),
        help_text=_(
            'Unit: day, If the user does not update the password during the time, '
            'the user password will expire failure;The password expiration reminder mail will be '
            'automatic sent to the user by system within 5 days (daily) before the password expires'
        )
    )
    OLD_PASSWORD_HISTORY_LIMIT_COUNT = serializers.IntegerField(
        min_value=0, max_value=99999, required=True,
        label=_('Number of repeated historical passwords'),
        help_text=_(
            'Tip: When the user resets the password, it cannot be '
            'the previous n historical passwords of the user'
        )
    )
    USER_LOGIN_SINGLE_MACHINE_ENABLED = serializers.BooleanField(
        required=False, default=False, label=_("Only single device login"),
        help_text=_("Next device login, pre login will be logout")
    )
    ONLY_ALLOW_EXIST_USER_AUTH = serializers.BooleanField(
        required=False, default=False, label=_("Only exist user login"),
        help_text=_("If enable, CAS、OIDC auth will be failed, if user not exist yet")
    )
    ONLY_ALLOW_AUTH_FROM_SOURCE = serializers.BooleanField(
        required=False, default=False, label=_("Only from source login"),
        help_text=_("Only log in from the user source property")
    )
    SECURITY_MFA_VERIFY_TTL = serializers.IntegerField(
        min_value=5, max_value=60 * 60 * 10,
        label=_("MFA verify TTL"), help_text=_("Unit: second"),
    )
    SECURITY_LOGIN_CHALLENGE_ENABLED = serializers.BooleanField(
        required=False, default=False,
        label=_("Enable Login dynamic code")
    )
    SECURITY_MFA_IN_LOGIN_PAGE = serializers.BooleanField(
        required=False, default=False,
        label=_("Enable Login MFA")
    )
    SECURITY_LOGIN_CAPTCHA_ENABLED = serializers.BooleanField(
        required=False, default=False,
        label=_("Enable Login captcha")
    )

    def validate(self, attrs):
        if attrs.get('SECURITY_MFA_AUTH') != 1:
            attrs['SECURITY_MFA_IN_LOGIN_PAGE'] = False
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['SECURITY_LOGIN_CHALLENGE_ENABLED']:
            data['SECURITY_MFA_IN_LOGIN_PAGE'] = False
            data['SECURITY_LOGIN_CAPTCHA_ENABLED'] = False
        elif data['SECURITY_MFA_IN_LOGIN_PAGE']:
            data['SECURITY_LOGIN_CAPTCHA_ENABLED'] = False
        return data


class SecuritySettingSerializer(SecurityPasswordRuleSerializer, SecurityAuthSerializer):
    SECURITY_SERVICE_ACCOUNT_REGISTRATION = serializers.BooleanField(
        required=True, label=_('Enable terminal register'),
        help_text=_("Allow terminal register, after all terminal setup, you should disable this for security")
    )
    SECURITY_WATERMARK_ENABLED = serializers.BooleanField(
        required=True, label=_('Replay watermark'),
        help_text=_('Enabled, the session replay contains watermark information')
    )
    SECURITY_MAX_IDLE_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=False,
        label=_('Connection max idle time'),
        help_text=_('If idle time more than it, disconnect connection Unit: minute')
    )
    SECURITY_LUNA_REMEMBER_AUTH = serializers.BooleanField(
        label=_("Remember manual auth")
    )
    CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED = serializers.BooleanField(
        label=_("Enable change auth secure mode")
    )
    SECURITY_INSECURE_COMMAND = serializers.BooleanField(
        required=False, label=_('Insecure command alert')
    )
    SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER = serializers.CharField(
        max_length=8192, required=False, allow_blank=True, label=_('Email recipient'),
        help_text=_('Multiple user using , split')
    )
    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(
        required=False, label=_('Batch command execution'),
        help_text=_('Allow user run batch command or not using ansible')
    )
    SECURITY_SESSION_SHARE = serializers.BooleanField(
        required=True, label=_('Session share'),
        help_text=_("Enabled, Allows user active session to be shared with other users")
    )
    LOGIN_CONFIRM_ENABLE = serializers.BooleanField(
        required=False, label=_('Login Confirm'),
        help_text=_("Enabled, please go to the user detail add approver")
    )
