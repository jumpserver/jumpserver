from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from .base import OrgListField

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
        required=True, max_length=1024, label=_('Server'),
        help_text=_('LDAP server URI')
    )
    AUTH_LDAP_BIND_DN = serializers.CharField(
        required=False, max_length=1024, label=_('Bind DN'),
        help_text=_('Binding Distinguished Name')
    )
    AUTH_LDAP_BIND_PASSWORD = EncryptedField(
        max_length=1024, required=False, label=_('Password'),
        help_text=_('Binding password')
    )
    AUTH_LDAP_SEARCH_OU = serializers.CharField(
        max_length=1024, allow_blank=True, required=False, label=_('Search OU'),
        help_text=_(
            'User Search Base, if there are multiple OUs, you can separate them with the `|` symbol'
        )
    )
    AUTH_LDAP_SEARCH_FILTER = serializers.CharField(
        max_length=1024, required=True, label=_('Search filter'),
        help_text=_('Selection could include (cn|uid|sAMAccountName=%(user)s)')
    )
    AUTH_LDAP_USER_ATTR_MAP = serializers.JSONField(
        required=True, label=_('User attribute'),
        help_text=_(
            'User attribute mapping, where the `key` is the JumpServer user attribute name and the '
            '`value` is the LDAP service user attribute name'
        )
    )
    AUTH_LDAP_SYNC_IS_PERIODIC = serializers.BooleanField(
        required=False, label=_('Periodic run')
    )
    AUTH_LDAP_SYNC_CRONTAB = serializers.CharField(
        required=False, max_length=128, allow_null=True, allow_blank=True,
        label=_('Crontab')
    )
    AUTH_LDAP_SYNC_INTERVAL = serializers.IntegerField(
        required=False, default=24, allow_null=True, label=_('Interval')
    )
    AUTH_LDAP_CONNECT_TIMEOUT = serializers.IntegerField(
        min_value=1, max_value=300,
        required=False, label=_('Connect timeout (s)'),
    )
    AUTH_LDAP_CACHE_TIMEOUT = serializers.IntegerField(
        min_value=0, max_value=3600 * 24 * 30 * 12,
        default=3600 * 24 * 30,
        required=False, label=_('User DN cache timeout (s)'),
        help_text=_(
            'Caching the User DN obtained during user login authentication can effectively'
            'improve the speed of user authentication., 0 means no cache<br>'
            'If the user OU structure has been adjusted, click Submit to clear the user DN cache'
        )
    )
    AUTH_LDAP_SEARCH_PAGED_SIZE = serializers.IntegerField(
        required=False, label=_('Search paged size (piece)')
    )
    AUTH_LDAP_SYNC_RECEIVERS = serializers.ListField(
        required=False, label=_('Recipient'), max_length=36
    )

    AUTH_LDAP = serializers.BooleanField(required=False, label=_('LDAP'))
    AUTH_LDAP_SYNC_ORG_IDS = OrgListField()

    def post_save(self):
        keys = ['AUTH_LDAP_SYNC_IS_PERIODIC', 'AUTH_LDAP_SYNC_INTERVAL', 'AUTH_LDAP_SYNC_CRONTAB']
        kwargs = {k: self.validated_data[k] for k in keys if k in self.validated_data}
        if not kwargs:
            return
        from settings.tasks import import_ldap_user_periodic
        import_ldap_user_periodic(**kwargs)
