from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from acls.serializers.rules import ip_group_help_text, ip_group_child_validator


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
    SECURITY_PASSWORD_LOWER_CASE = serializers.BooleanField(
        required=False, label=_('Must contain lowercase')
    )
    SECURITY_PASSWORD_NUMBER = serializers.BooleanField(
        required=False, label=_('Must contain numeric')
    )
    SECURITY_PASSWORD_SPECIAL_CHAR = serializers.BooleanField(
        required=False, label=_('Must contain special')
    )


login_ip_limit_time_help_text = _(
    'If the user has failed to log in for a limited number of times, '
    'no login is allowed during this time interval.'
)


class SecurityAuthSerializer(serializers.Serializer):
    SECURITY_MFA_AUTH = serializers.ChoiceField(
        choices=(
            [0, _('Disable')],
            [1, _('All users')],
            [2, _('Only admin users')],
        ),
        required=False, label=_("Global MFA auth")
    )
    SECURITY_MFA_AUTH_ENABLED_FOR_THIRD_PARTY = serializers.BooleanField(
        required=False, default=True,
        label=_('Third-party login users perform MFA authentication'),
        help_text=_('The third-party login modes include OIDC, CAS, and SAML2'),
    )
    SECURITY_LOGIN_LIMIT_COUNT = serializers.IntegerField(
        min_value=3, max_value=99999,
        label=_('Limit the number of user login failures')
    )
    SECURITY_LOGIN_LIMIT_TIME = serializers.IntegerField(
        min_value=5, max_value=99999, required=True,
        label=_('Block user login interval (minute)'),
        help_text=login_ip_limit_time_help_text
    )
    SECURITY_LOGIN_IP_LIMIT_COUNT = serializers.IntegerField(
        min_value=3, max_value=99999,
        label=_('Limit the number of IP login failures')
    )
    SECURITY_LOGIN_IP_LIMIT_TIME = serializers.IntegerField(
        min_value=5, max_value=99999, required=True,
        label=_('Block IP login interval (minute)'),
        help_text=login_ip_limit_time_help_text
    )
    SECURITY_LOGIN_IP_WHITE_LIST = serializers.ListField(
        default=[], label=_('Login IP White List'), allow_empty=True,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator]),
        help_text=ip_group_help_text
    )
    SECURITY_LOGIN_IP_BLACK_LIST = serializers.ListField(
        default=[], label=_('Login IP Black List'), allow_empty=True,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator]),
        help_text=ip_group_help_text
    )
    SECURITY_PASSWORD_EXPIRATION_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=True,
        label=_('User password expiration (day)'),
        help_text=_(
            'If the user does not update the password during the time, '
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
        help_text=_("After the user logs in on the new device, other logged-in devices will automatically log out")
    )
    ONLY_ALLOW_EXIST_USER_AUTH = serializers.BooleanField(
        required=False, default=False, label=_("Only exist user login"),
        help_text=_(
            "If enabled, non-existent users will not be allowed to log in; if disabled, users of other authentication methods except local authentication methods are allowed to log in and automatically create users (if the user does not exist)")
    )
    ONLY_ALLOW_AUTH_FROM_SOURCE = serializers.BooleanField(
        required=False, default=False, label=_("Only from source login"),
        help_text=_(
            "If it is enabled, the user will only authenticate to the source when logging in; if it is disabled, the user will authenticate all the enabled authentication methods in a certain order when logging in, and as long as one of the authentication methods is successful, they can log in directly")
    )
    SECURITY_MFA_VERIFY_TTL = serializers.IntegerField(
        min_value=5, max_value=60 * 60 * 10,
        label=_("MFA verify TTL (secend)"),
        help_text=_(
            "The verification MFA takes effect only when you view the account password"
        )
    )
    VERIFY_CODE_TTL = serializers.IntegerField(
        min_value=5, max_value=60 * 60 * 10,
        label=_("Verify code TTL"),
        help_text=_("Unit: second, reset password and send SMS code expiration time")
    )
    SECURITY_LOGIN_CHALLENGE_ENABLED = serializers.BooleanField(
        required=False, default=False,
        label=_("Enable Login dynamic code"),
        help_text=_("The password and additional code are sent to a third party "
                    "authentication system for verification")
    )
    SECURITY_MFA_IN_LOGIN_PAGE = serializers.BooleanField(
        required=False, default=False,
        label=_("MFA in login page"),
        help_text=_("Eu security regulations(GDPR) require MFA to be on the login page")
    )
    SECURITY_LOGIN_CAPTCHA_ENABLED = serializers.BooleanField(
        required=False, default=False, label=_("Enable Login captcha"),
        help_text=_("Enable captcha to prevent robot authentication")
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
    PREFIX_TITLE = _('Security')

    SECURITY_SERVICE_ACCOUNT_REGISTRATION = serializers.BooleanField(
        required=True, label=_('Enable terminal register'),
        help_text=_(
            "Allow terminal register, after all terminal setup, you should disable this for security"
        )
    )
    SECURITY_WATERMARK_ENABLED = serializers.BooleanField(
        required=True, label=_('Enable watermark'),
        help_text=_('Enabled, the web session and replay contains watermark information')
    )
    SECURITY_MAX_IDLE_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=False,
        label=_('Connection max idle time (minute)'),
        help_text=_('If idle time more than it, disconnect connection.')
    )
    SECURITY_LUNA_REMEMBER_AUTH = serializers.BooleanField(
        label=_("Remember manual auth")
    )
    SECURITY_INSECURE_COMMAND = serializers.BooleanField(
        required=False, label=_('Insecure command alert')
    )
    SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER = serializers.CharField(
        max_length=8192, required=False, allow_blank=True, label=_('Email recipient'),
        help_text=_('Multiple user using , split')
    )
    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(
        required=False, label=_('Operation center'),
        help_text=_('Allow user run batch command or not using ansible')
    )
    SECURITY_COMMAND_BLACKLIST = serializers.ListField(
        child=serializers.CharField(max_length=1024, ),
        label=_('Operation center command blacklist'),
        help_text=_("Commands that are not allowed execute.")
    )
    SECURITY_SESSION_SHARE = serializers.BooleanField(
        required=True, label=_('Session share'),
        help_text=_("Enabled, Allows user active session to be shared with other users")
    )
    SECURITY_CHECK_DIFFERENT_CITY_LOGIN = serializers.BooleanField(
        required=False, label=_('Remote Login Protection'),
        help_text=_(
            'The system determines whether the login IP address belongs to a common login city. '
            'If the account is logged in from a common login city, the system sends a remote login reminder'
        )
    )
