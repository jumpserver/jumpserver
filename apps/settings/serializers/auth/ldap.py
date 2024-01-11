from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField

__all__ = [
    'LDAPTestConfigSerializer', 'LDAPUserSerializer', 'LDAPTestLoginSerializer',
    'LDAPSettingSerializer',
]


class LDAPTestConfigSerializer(serializers.Serializer):
    AUTH_LDAP_SERVER_URI = serializers.CharField(max_length=1024)
    AUTH_LDAP_BIND_DN = serializers.CharField(max_length=1024, required=False, allow_blank=True)
    AUTH_LDAP_BIND_PASSWORD = EncryptedField(required=False, allow_blank=True)
    AUTH_LDAP_SEARCH_OU = serializers.CharField()
    AUTH_LDAP_SEARCH_FILTER = serializers.CharField()
    AUTH_LDAP_USER_ATTR_MAP = serializers.JSONField()
    AUTH_LDAP_START_TLS = serializers.BooleanField(required=False)
    AUTH_LDAP = serializers.BooleanField(required=False)


class LDAPTestLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=1024, required=True)
    password = EncryptedField(max_length=2014, required=True, label=_("Password"))


class LDAPUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    name = serializers.CharField()
    email = serializers.CharField()
    groups = serializers.ListField(child=serializers.CharField(), default=[])
    existing = serializers.BooleanField(read_only=True)


class LDAPSettingSerializer(serializers.Serializer):
    # encrypt_fields 现在使用 write_only 来判断了
    PREFIX_TITLE = _('LDAP')

    AUTH_LDAP_SERVER_URI = serializers.CharField(
        required=True, max_length=1024, label=_('LDAP server'),
        help_text=_('eg: ldap://localhost:389')
    )
    AUTH_LDAP_BIND_DN = serializers.CharField(required=False, max_length=1024, label=_('Bind DN'))
    AUTH_LDAP_BIND_PASSWORD = EncryptedField(
        max_length=1024, required=False, label=_('Password')
    )
    AUTH_LDAP_SEARCH_OU = serializers.CharField(
        max_length=1024, allow_blank=True, required=False, label=_('User OU'),
        help_text=_('Use | split multi OUs')
    )
    AUTH_LDAP_SEARCH_FILTER = serializers.CharField(
        max_length=1024, required=True, label=_('User search filter'),
        help_text=_('Choice may be (cn|uid|sAMAccountName)=%(user)s)')
    )
    AUTH_LDAP_USER_ATTR_MAP = serializers.JSONField(
        required=True, label=_('User attr map'),
        help_text=_('User attr map present how to map LDAP user attr to '
                    'jumpserver, username,name,email is jumpserver attr')
    )
    AUTH_LDAP_SYNC_ORG_IDS = serializers.ListField(
        required=False, label=_('Organization'), max_length=36
    )
    AUTH_LDAP_SYNC_IS_PERIODIC = serializers.BooleanField(
        required=False, label=_('Periodic perform')
    )
    AUTH_LDAP_SYNC_CRONTAB = serializers.CharField(
        required=False, max_length=128, allow_null=True, allow_blank=True,
        label=_('Regularly perform')
    )
    AUTH_LDAP_SYNC_INTERVAL = serializers.IntegerField(
        required=False, default=24, allow_null=True, label=_('Cycle perform')
    )
    AUTH_LDAP_CONNECT_TIMEOUT = serializers.IntegerField(
        min_value=1, max_value=300,
        required=False, label=_('Connect timeout (s)'),
    )
    AUTH_LDAP_SEARCH_PAGED_SIZE = serializers.IntegerField(required=False, label=_('Search paged size (piece)'))
    AUTH_LDAP_SYNC_RECEIVERS = serializers.ListField(
        required=False, label=_('Recipient'), max_length=36
    )

    AUTH_LDAP = serializers.BooleanField(required=False, label=_('Enable LDAP auth'))

    @staticmethod
    def post_save():
        from settings.tasks import import_ldap_user_periodic
        import_ldap_user_periodic()
