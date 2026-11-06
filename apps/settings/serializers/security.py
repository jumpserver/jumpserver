from cryptography.hazmat.primitives import hashes
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from acls.serializers.rules import ip_group_help_text, ip_group_child_validator
from common.utils.rdp_signing import (
    get_rdp_signing_config, load_rdp_signing_material, RDPSigningMaterialError, RDP_SIGN_SETTING_NAMES,
    RDP_SIGN_UPLOAD_NAMES, validate_rdp_signing_material,
)

__all__ = [
    'SecurityPasswordRuleSerializer', 'SecuritySessionSerializer',
    'SecurityAuthSerializer', 'SecuritySettingSerializer',
    'SecurityLoginLimitSerializer', 'SecurityBasicSerializer',
    'SecurityBlockIPSerializer', 'LeakPasswordPSerializer'
]

from settings.models import LeakPasswords


def validate_sangfor_login_lifetime(value):
    if str(settings.VENDOR).strip().lower() == 'sangfor' and not 300 <= value <= 86400:
        raise serializers.ValidationError(_(
            'Enter an integer from 300 to 86400 seconds (5 minutes to 24 hours).'
        ))


class SecurityPasswordRuleSerializer(serializers.Serializer):
    CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED = serializers.BooleanField(
        required=False, label=_('Change secret plan secure mode'),
        help_text=_(
            'Change secret plans use privileged accounts. When enabled, privileged accounts, root, administrator, '
            'and accounts with the same username as the privileged account are excluded. When disabled, '
            'an account may change its own password, subject to asset and account permissions.'
        )
    )
    CHANGE_SECRET_AFTER_SESSION_END = serializers.BooleanField(
        required=False, label=_('Secret rotation'),
        help_text=_(
            'When enabled, eligible accounts used in sessions matching a secret rotation login rule are changed '
            'after the session ends. To rotate privileged accounts, disable change secret plan secure mode.'
        )
    )
    SECURITY_ACCOUNT_SECRET_READ = serializers.BooleanField(
        required=False, label=_('Allow viewing asset account passwords'),
        help_text=_(
            'When disabled, asset account passwords cannot be viewed. Asset connections are not affected. '
            'Enabling this still requires the appropriate permissions.'
        )
    )
    SECURITY_PASSWORD_EXPIRATION_TIME_ADMIN = serializers.IntegerField(
        min_value=1, max_value=99999, required=True,
        label=_('Admin password expiration (day)'),
        help_text=_(
            'If the admin does not update the password during the time, '
            'the admin password will expire failure;The password expiration reminder mail will be '
            'automatic sent to the admin by system within 5 days (daily) before the password expires'
        )
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
    SECURITY_EXPIRED_TOKEN_RECORD_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=99999, required=True,
        label=_('User expired tokens record keep days'),
        help_text=_("Retention period (in days) for expired user tokens before automatic cleanup.")
    )
    OLD_PASSWORD_HISTORY_LIMIT_COUNT = serializers.IntegerField(
        min_value=0, max_value=99999, required=True,
        label=_('Recent password count'),
        help_text=_(
            'Tip: When the user resets the password, it cannot be '
            'the previous n historical passwords of the user'
        )
    )
    SECURITY_PASSWORD_MIN_LENGTH = serializers.IntegerField(
        min_value=6, max_value=30, required=True,
        label=_("Minimum length (User)")
    )
    SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH = serializers.IntegerField(
        min_value=6, max_value=30, required=True,
        label=_('Minimum length (Admin)')
    )
    SECURITY_PASSWORD_UPPER_CASE = serializers.BooleanField(
        required=False, label=_('Uppercase')
    )
    SECURITY_PASSWORD_LOWER_CASE = serializers.BooleanField(
        required=False, label=_('Lowercase')
    )
    SECURITY_PASSWORD_NUMBER = serializers.BooleanField(
        required=False, label=_('Digits')
    )
    SECURITY_PASSWORD_SPECIAL_CHAR = serializers.BooleanField(
        required=False, label=_('Special characters')
    )


login_ip_limit_time_help_text = _(
    'If the user has failed to log in for a limited number of times, '
    'no login is allowed during this time interval. '
    'Each login attempt refreshes this time interval.'
)


class SecurityLoginLimitSerializer(serializers.Serializer):
    SECURITY_LOGIN_LIMIT_COUNT = serializers.IntegerField(
        min_value=3, max_value=99999,
        label=_('Login failures count')
    )
    SECURITY_LOGIN_LIMIT_TIME = serializers.IntegerField(
        min_value=5, max_value=99999, required=True,
        label=_('Login failure period (minute)'),
        help_text=login_ip_limit_time_help_text
    )

    SECURITY_LOGIN_IP_LIMIT_COUNT = serializers.IntegerField(
        min_value=3, max_value=99999,
        label=_('Login failures count')
    )
    SECURITY_LOGIN_IP_LIMIT_TIME = serializers.IntegerField(
        min_value=5, max_value=99999, required=True,
        label=_('Login failure period (minute)'),
        help_text=login_ip_limit_time_help_text
    )
    SECURITY_LOGIN_IP_WHITE_LIST = serializers.ListField(
        default=[], label=_('Login IP whitelist'), allow_empty=True,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator]),
        help_text=ip_group_help_text
    )
    SECURITY_LOGIN_IP_BLACK_LIST = serializers.ListField(
        default=[], label=_('Login IP blacklist'), allow_empty=True,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator]),
        help_text=ip_group_help_text
    )
    USER_LOGIN_SINGLE_MACHINE_ENABLED = serializers.BooleanField(
        required=False, default=False, label=_("Only single device login"),
        help_text=_("After the user logs in on the new device, other logged-in devices will automatically log out")
    )
    ONLY_ALLOW_EXIST_USER_AUTH = serializers.BooleanField(
        required=False, default=False, label=_("Only exist user login"),
        help_text=_(
            "If enabled, non-existent users will not be allowed to log in; if disabled, "
            "users of other authentication methods except local authentication methods are allowed "
            "to log in and automatically create users (if the user does not exist)"
        )
    )
    ONLY_ALLOW_AUTH_FROM_SOURCE = serializers.BooleanField(
        required=False, default=False, label=_("Only from source login"),
        help_text=_(
            "If it is enabled, the user will only authenticate to the source when logging in; "
            "if it is disabled, the user will authenticate all the enabled authentication methods "
            "in a certain order when logging in, and as long as one of the authentication methods is successful, "
            "they can log in directly"
        )
    )


class SecurityAuthSerializer(serializers.Serializer):
    SECURITY_MFA_AUTH = serializers.ChoiceField(
        choices=(
            [0, _('Not enabled')],
            [1, _('All users')],
            [2, _('Only admin users')],
        ),
        required=False, label=_("Global MFA")
    )
    SECURITY_MFA_AUTH_ENABLED_FOR_THIRD_PARTY = serializers.BooleanField(
        required=False, default=True,
        label=_('Third-party login MFA'),
    )
    SECURITY_MFA_BY_EMAIL = serializers.BooleanField(
        required=False, default=False,
        label=_('MFA via Email'),
        help_text=_('Email as a method for multi-factor authentication')
    )
    OTP_ISSUER_NAME = serializers.CharField(
        required=False, max_length=16, label=_('OTP issuer name'),
    )
    OTP_VALID_WINDOW = serializers.IntegerField(
        min_value=0, max_value=10,
        label=_("OTP valid window")
    )
    SECURITY_MFA_VERIFY_TTL = serializers.IntegerField(
        min_value=5, max_value=60 * 60 * 10,
        label=_("MFA verify TTL"),
        help_text=_(
            "Unit: second, The verification MFA takes effect only when you view the account password"
        )
    )
    SECURITY_MFA_IN_LOGIN_PAGE = serializers.BooleanField(
        required=False, default=False,
        label=_("MFA in login page"),
        help_text=_("Eu security regulations(GDPR) require MFA to be on the login page")
    )
    VERIFY_CODE_TTL = serializers.IntegerField(
        min_value=5, max_value=60 * 60 * 10,
        label=_("Verify code TTL (second)"),
        help_text=_("Reset password and send SMS code expiration time")
    )
    SECURITY_LOGIN_CHALLENGE_ENABLED = serializers.BooleanField(
        required=False, default=False,
        label=_("Login dynamic code"),
        help_text=_("The password and additional code are sent to a third party "
                    "authentication system for verification")
    )
    SECURITY_LOGIN_CAPTCHA_ENABLED = serializers.BooleanField(
        required=False, default=False, label=_("Login CAPTCHA"),
        help_text=_("Enable CAPTCHA to prevent robot authentication")
    )
    SECURITY_CHECK_DIFFERENT_CITY_LOGIN = serializers.BooleanField(
        required=False, label=_('Suspicious Login Verification'),
        help_text=_(
            'The system determines whether the login IP address belongs to a common login city. '
            'If the account is logged in from a common login city, the system sends a remote login reminder'
        )
    )
    SECURITY_UNCOMMON_USERS_TTL = serializers.IntegerField(
        min_value=30, max_value=99999, required=False,
        label=_('Auto Disable Threshold (day)'),
        help_text=_("Detect infrequent users daily and disable them if they exceed the predetermined time limit")
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


class SecuritySessionSerializer(serializers.Serializer):
    RDP_SIGN_ENABLED = serializers.BooleanField(
        required=False, label=_('RDP file signing'),
        help_text=_('Sign RDP connection files. If signing fails, provide an unsigned file.'),
    )
    RDP_SIGN_CERT_CONTENT = serializers.CharField(
        required=False, allow_blank=True, write_only=True, max_length=65536,
        trim_whitespace=False, label=_('RDP signing certificate'),
        help_text=_('Upload a PEM certificate with Code Signing EKU. Leave empty to keep the current certificate.'),
    )
    RDP_SIGN_KEY_CONTENT = serializers.CharField(
        required=False, allow_blank=True, write_only=True, max_length=65536,
        trim_whitespace=False, label=_('RDP signing private key'),
        help_text=_('Upload the matching unencrypted PEM private key. Leave empty to keep the current key.'),
    )
    RDP_SIGN_CERT_INFO = serializers.SerializerMethodField(label=_('RDP signing certificate status'))

    def get_RDP_SIGN_CERT_INFO(self, instance):
        try:
            certificate, _private_key = load_rdp_signing_material()
        except RDPSigningMaterialError:
            return _('Not configured or invalid')
        source = _('Core data/certs')
        fingerprint = certificate.fingerprint(hashes.SHA256()).hex(':')
        expires = certificate.not_valid_after_utc.isoformat()
        return f'{source}; SHA256: {fingerprint}; {expires}'

    def validate(self, attrs):
        for name in ('RDP_SIGN_CERT_CONTENT', 'RDP_SIGN_KEY_CONTENT'):
            if attrs.get(name) == '':
                attrs.pop(name)
        if not any(name in attrs for name in RDP_SIGN_SETTING_NAMES + RDP_SIGN_UPLOAD_NAMES):
            return attrs
        config = get_rdp_signing_config()
        if self.instance:
            config.update({name: self.instance[name] for name in RDP_SIGN_SETTING_NAMES if name in self.instance})
        config.update({name: value for name, value in attrs.items() if name in RDP_SIGN_SETTING_NAMES})
        uploaded = any(name in attrs for name in ('RDP_SIGN_CERT_CONTENT', 'RDP_SIGN_KEY_CONTENT'))
        if not config['RDP_SIGN_ENABLED'] and not uploaded:
            return attrs
        try:
            if uploaded:
                if not all(attrs.get(name) for name in RDP_SIGN_UPLOAD_NAMES):
                    raise RDPSigningMaterialError('incomplete_upload')
                validate_rdp_signing_material(*(attrs[name].encode('utf-8') for name in RDP_SIGN_UPLOAD_NAMES))
            else:
                load_rdp_signing_material()
        except RDPSigningMaterialError:
            raise serializers.ValidationError({
                'RDP_SIGN_CERT_CONTENT': _(
                    'Upload a valid PEM Code Signing certificate and its matching unencrypted RSA or EC private key.'
                ),
            }) from None
        return attrs

    SESSION_COOKIE_AGE = serializers.IntegerField(
        min_value=1, max_value=2147483647, required=False,
        validators=[validate_sangfor_login_lifetime],
        label=_('Web login lifetime (seconds)'),
        help_text=_(
            'Sets the web login lifetime. By default, web requests renew the session; this is not a fixed logout countdown. '
            'Log in again to use the new value. Changes do not immediately force logged-in users to log out.'
        )
    )
    CONNECTION_TOKEN_REUSABLE = serializers.BooleanField(
        required=False, label=_('Allow connection credential reuse'),
        help_text=_(
            'When enabled, connection credentials can be set as reusable within their lifetime without obtaining a new '
            'one for each connection. Existing credentials are not automatically converted to reusable credentials.'
        )
    )
    CONNECTION_TOKEN_ONETIME_EXPIRATION = serializers.IntegerField(
        min_value=300, max_value=2147483647, required=False,
        label=_('One-time connection credential lifetime (seconds)'),
        help_text=_(
            'Sets the one-time connection credential lifetime, with a minimum of 300 seconds. '
            'Changes apply to newly created or renewed credentials without affecting established asset connections.'
        )
    )
    CONNECTION_TOKEN_REUSABLE_EXPIRATION = serializers.IntegerField(
        min_value=1, max_value=2147483647, required=False,
        label=_('Reusable connection credential lifetime (seconds)'),
        help_text=_(
            'Sets the reusable credential lifetime, measured from its creation time. '
            'The new value is used when credentials are set as reusable. Existing expiry times remain unchanged.'
        )
    )
    OAUTH2_PROVIDER_ACCESS_TOKEN_EXPIRE_SECONDS = serializers.IntegerField(
        min_value=1, max_value=2147483647, required=False,
        validators=[validate_sangfor_login_lifetime],
        label=_('Client access token lifetime (seconds)'),
        help_text=_(
            'Sets the client access token lifetime. A refresh token can be used to renew access before expiry. '
            'Changes apply to newly issued access tokens. Existing token expiry times remain unchanged.'
        )
    )
    OAUTH2_PROVIDER_REFRESH_TOKEN_EXPIRE_SECONDS = serializers.IntegerField(
        min_value=1, max_value=2147483647, required=False,
        validators=[validate_sangfor_login_lifetime],
        label=_('Client refresh token lifetime (seconds)'),
        help_text=_(
            'Sets the lifetime of the credential used for automatic client renewal. For clients that check this lifetime, '
            'setting it much shorter than the access token lifetime, for example 1 second, prevents automatic renewal '
            'and logs the client out when the access token expires. Log in to the client again after changing this setting.'
        )
    )
    SECURITY_WATERMARK_ENABLED = serializers.BooleanField(
        required=True, label=_('Watermark'),
    )
    SECURITY_WATERMARK_SESSION_CONTENT = serializers.CharField(
        required=False, label=_('Session content'),
    )
    SECURITY_WATERMARK_CONSOLE_CONTENT = serializers.CharField(
        required=False, label=_("Console content")
    )
    SECURITY_WATERMARK_COLOR = serializers.CharField(
        max_length=32, default="", label=_("Font color")
    )
    SECURITY_WATERMARK_FONT_SIZE = serializers.IntegerField(
        required=False, label=_('Font size'), min_value=1, max_value=100,
    )
    SECURITY_WATERMARK_HEIGHT = serializers.IntegerField(
        required=False, label=_('Height'), default=200
    )
    SECURITY_WATERMARK_WIDTH = serializers.IntegerField(
        required=False, label=_('Width'), default=200
    )
    SECURITY_WATERMARK_ROTATE = serializers.IntegerField(
        required=False, label=_('Rotate'), default=45
    )
    SECURITY_MAX_IDLE_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=False,
        label=_('Max idle time (minute)'),
        help_text=_('If idle time more than it, disconnect connection.')
    )
    SESSION_EXPIRE_AT_BROWSER_CLOSE = serializers.BooleanField(
        required=False, default=False, label=_('Session expire at browser closed'),
        help_text=_('Whether to expire the session when the user closes their browser.')
    )
    VIEW_ASSET_ONLINE_SESSION_INFO = serializers.BooleanField(
        required=False,
        default=True,
        label=_('Allow users to view asset session information'),
        help_text=_(
            'When a user connects to an asset, the account selection popup displays the number of active sessions for '
            'the current asset (RDP protocol only).'
        )
    )
    SECURITY_MAX_SESSION_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=False,
        label=_('Max online time (hour)'),
        help_text=_('If session connection time more than it, disconnect connection.')
    )
    SECURITY_LUNA_REMEMBER_AUTH = serializers.BooleanField(
        label=_("Remember manual auth")
    )
    SECURITY_SESSION_SHARE = serializers.BooleanField(
        required=True, label=_('Session share'),
        help_text=_("Enabled, Allows user active session to be shared with other users")
    )

    def get_fields(self):
        fields = super().get_fields()
        if str(settings.VENDOR).strip().lower() != 'sangfor':
            return fields

        fields['OAUTH2_PROVIDER_REFRESH_TOKEN_EXPIRE_SECONDS'].help_text = _(
            'Sets the lifetime of the credential used for automatic client renewal. '
            'This does not set a fixed logout countdown. Log in to the client again after changing this setting.'
        )
        range_help = _('Enter an integer from 300 to 86400 seconds (5 minutes to 24 hours).')
        for name in (
            'SESSION_COOKIE_AGE',
            'OAUTH2_PROVIDER_ACCESS_TOKEN_EXPIRE_SECONDS',
            'OAUTH2_PROVIDER_REFRESH_TOKEN_EXPIRE_SECONDS',
        ):
            fields[name].help_text = f'{fields[name].help_text} {range_help}'

        credential_help = _(
            'Used for connection authentication in transparent proxy character sessions such as SSH and databases; '
            'credential expiry does not disconnect established asset connections.'
        )
        for name in ('CONNECTION_TOKEN_ONETIME_EXPIRATION', 'CONNECTION_TOKEN_REUSABLE_EXPIRATION'):
            fields[name].help_text = f'{fields[name].help_text} {credential_help}'
        return fields


class SecurityBasicSerializer(serializers.Serializer):
    SECURITY_INSECURE_COMMAND = serializers.BooleanField(
        required=False, label=_('Insecure command alert')
    )
    SECURITY_ACCOUNT_USERNAME_FORBIDDEN_CHARS = serializers.CharField(
        required=False, allow_blank=True, label=_('Account username forbidden characters'),
        max_length=128
    )
    SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER = serializers.CharField(
        max_length=8192, required=False, allow_blank=True, label=_('Email recipient'),
        help_text=_('Multiple user using , split')
    )


class SecuritySettingSerializer(
    SecurityPasswordRuleSerializer, SecurityAuthSerializer,
    SecuritySessionSerializer, SecurityBasicSerializer,
    SecurityLoginLimitSerializer,
):
    PREFIX_TITLE = _('Security')


class SecurityBlockIPSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    ip = serializers.CharField(max_length=1024, required=False, allow_blank=True)


class LeakPasswordPSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        return LeakPasswords.objects.using('sqlite').create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using='sqlite')
        return instance

    class Meta:
        read_only_fields = ['id']
        fields = read_only_fields + ['password']
        model = LeakPasswords
