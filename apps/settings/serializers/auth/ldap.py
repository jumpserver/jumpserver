from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from orgs.models import Organization
from rbac.builtin import BuiltinRole
from rbac.const import Scope
from rbac.models import Role
from users.models import User, UserGroup
from orgs.utils import tmp_to_root_org
from .base import AttributeMapField, LDAP_ATTRIBUTE_PATTERN, OrgListField
from .mixin import LDAPSerializerMixin

__all__ = [
    'LDAPTestConfigSerializer', 'LDAPUserSerializer', 'LDAPTestLoginSerializer',
    'LDAPSettingSerializer',
]

USER_ATTR_FIELDS = {
    'username', 'name', 'email', 'phone', 'comment', 'is_active',
    'groups',
}
REQUIRED_USER_ATTR_FIELDS = {'username', 'name', 'email'}


def user_attr_map_field(**kwargs):
    return AttributeMapField(
        allowed_fields=USER_ATTR_FIELDS,
        required_fields=REQUIRED_USER_ATTR_FIELDS,
        **kwargs,
    )


def ldap_attribute_field(**kwargs):
    return serializers.RegexField(
        LDAP_ATTRIBUTE_PATTERN,
        error_messages={'invalid': _('Invalid LDAP attribute name')},
        **kwargs,
    )


def validate_group_search_filter(value):
    if not value:
        return value
    try:
        value % 'user'
    except (TypeError, ValueError):
        pass
    else:
        if value.count('%s') == 1:
            return value
    raise serializers.ValidationError(
        _('Group search filter must contain exactly one `%s` placeholder')
    )


def validate_group_mapping_source(serializer, attrs):
    def get_value(name):
        if name in attrs:
            return attrs[name]
        instance = serializer.instance
        if isinstance(instance, dict):
            return instance.get(name)
        return getattr(instance, name, None) if instance is not None else None

    group_rules = get_value('AUTH_LDAP_USER_GROUP_MAP') or []
    role_rules = get_value('AUTH_LDAP_USER_ROLE_MAP') or []
    exact_group_rules = any(
        rule.get('value') != '*' for rule in group_rules
    )
    role_uses_groups = any(
        rule.get('value') != '*' and
        str(rule.get('attribute', '')).casefold() == 'groups'
        for rule in role_rules
    )
    if not exact_group_rules and not role_uses_groups:
        return
    attr_map = get_value('AUTH_LDAP_USER_ATTR_MAP') or {}
    has_group_source = any([
        get_value('AUTH_LDAP_GROUP_ATTRIBUTE'),
        get_value('AUTH_LDAP_GROUP_SEARCH_FILTER'),
        attr_map.get('groups') if isinstance(attr_map, dict) else None,
    ])
    if not has_group_source:
        field = (
            'AUTH_LDAP_USER_GROUP_MAP'
            if exact_group_rules else 'AUTH_LDAP_USER_ROLE_MAP'
        )
        raise serializers.ValidationError({
            field: _(
                'Exact user group mappings require a group attribute or group search filter'
            )
        })


class StringUUIDField(serializers.UUIDField):
    def to_internal_value(self, data):
        return str(super().to_internal_value(data))


class AuthMappingListSerializer(serializers.ListSerializer):
    identity_fields = ()

    def validate(self, attrs):
        wildcard_count = sum(item['value'] == '*' for item in attrs)
        if wildcard_count > 1:
            raise serializers.ValidationError(_('Only one wildcard mapping is allowed'))

        seen = set()
        for item in attrs:
            identity = tuple(
                value.casefold() if isinstance(value := item.get(field), str) else value
                for field in self.identity_fields
            )
            if identity in seen:
                raise serializers.ValidationError(_('Duplicate mapping rows are not allowed'))
            seen.add(identity)
        return attrs


class LDAPUserGroupMapListSerializer(AuthMappingListSerializer):
    identity_fields = ('value', 'user_group_id')


class LDAPUserGroupMapSerializer(serializers.Serializer):
    value = serializers.CharField(max_length=4096)
    user_group_id = StringUUIDField()

    class Meta:
        list_serializer_class = LDAPUserGroupMapListSerializer

    def validate_user_group_id(self, value):
        with tmp_to_root_org():
            group = UserGroup.objects.filter(id=value).only('org_id').first()
        if not group:
            raise serializers.ValidationError(_('User group does not exist'))
        if str(group.org_id) == Organization.SYSTEM_ID:
            raise serializers.ValidationError(
                _('User groups in the system organization cannot be mapped')
            )
        return value


class LDAPUserRoleMapListSerializer(AuthMappingListSerializer):
    identity_fields = (
        'attribute', 'value', 'scope', 'role_id', 'org_id',
    )


class LDAPUserRoleMapSerializer(serializers.Serializer):
    attribute = ldap_attribute_field(
        max_length=256, required=False, allow_blank=True, default=''
    )
    value = serializers.CharField(max_length=4096)
    scope = serializers.ChoiceField(choices=Scope.choices)
    role_id = StringUUIDField()
    org_id = StringUUIDField(required=False, allow_null=True, default=None)

    class Meta:
        list_serializer_class = LDAPUserRoleMapListSerializer

    def validate(self, attrs):
        attribute = attrs['attribute']
        value = attrs['value']
        scope = attrs['scope']
        role_id = attrs['role_id']
        org_id = attrs['org_id']

        if value == '*':
            if attribute:
                raise serializers.ValidationError({
                    'attribute': _('Wildcard role mapping must not specify an attribute')
                })
        elif not attribute:
            raise serializers.ValidationError({
                'attribute': _('Role mapping attribute is required')
            })

        if role_id == BuiltinRole.system_component.id:
            raise serializers.ValidationError({
                'role_id': _('The system component role cannot be mapped')
            })
        role = Role.objects.filter(id=role_id).only('scope').first()
        if not role:
            raise serializers.ValidationError({'role_id': _('Role does not exist')})
        if role.scope != scope:
            raise serializers.ValidationError({
                'scope': _('Role scope does not match the selected scope')
            })

        if scope == Scope.system:
            if org_id is not None:
                raise serializers.ValidationError({
                    'org_id': _('System role mapping must not specify an organization')
                })
        elif org_id is None:
            raise serializers.ValidationError({
                'org_id': _('Organization role mapping requires an organization')
            })
        elif org_id == Organization.SYSTEM_ID:
            raise serializers.ValidationError({
                'org_id': _('The system organization cannot be mapped')
            })
        elif not Organization.objects.filter(id=org_id).exists():
            raise serializers.ValidationError({
                'org_id': _('Organization does not exist')
            })
        return attrs


class LDAPTestUserGroupMapSerializer(serializers.Serializer):
    value = serializers.CharField(
        max_length=4096, required=False, allow_blank=True
    )
    user_group_id = serializers.CharField(
        max_length=36, required=False, allow_blank=True
    )


class LDAPTestUserRoleMapSerializer(serializers.Serializer):
    attribute = ldap_attribute_field(
        max_length=256, required=False, allow_blank=True
    )
    value = serializers.CharField(
        max_length=4096, required=False, allow_blank=True
    )
    scope = serializers.CharField(
        max_length=128, required=False, allow_blank=True
    )
    role_id = serializers.CharField(
        max_length=36, required=False, allow_blank=True
    )
    org_id = serializers.CharField(
        max_length=36, required=False, allow_blank=True, allow_null=True
    )


class LDAPTestConfigSerializer(serializers.Serializer):
    AUTH_LDAP_SERVER_URI = serializers.CharField(max_length=1024)
    AUTH_LDAP_BIND_DN = serializers.CharField(max_length=1024, required=False, allow_blank=True)
    AUTH_LDAP_BIND_PASSWORD = EncryptedField(required=False, allow_blank=True)
    AUTH_LDAP_SEARCH_OU = serializers.CharField()
    AUTH_LDAP_SEARCH_FILTER = serializers.CharField()
    AUTH_LDAP_USER_ATTR_MAP = user_attr_map_field()
    AUTH_LDAP_GROUP_ATTRIBUTE = ldap_attribute_field(
        max_length=256, required=False, allow_blank=True
    )
    AUTH_LDAP_GROUP_SEARCH_OU = serializers.CharField(
        max_length=4096, required=False, allow_blank=True
    )
    AUTH_LDAP_GROUP_SEARCH_FILTER = serializers.CharField(
        max_length=1024, required=False, allow_blank=True,
        validators=[validate_group_search_filter]
    )
    AUTH_LDAP_GROUP_SEARCH_USER_ATTRIBUTE = ldap_attribute_field(
        max_length=256, required=False, allow_blank=True
    )
    AUTH_LDAP_USER_GROUP_MAP = LDAPTestUserGroupMapSerializer(
        many=True, required=False
    )
    AUTH_LDAP_USER_ROLE_MAP = LDAPTestUserRoleMapSerializer(
        many=True, required=False
    )
    AUTH_LDAP_START_TLS = serializers.BooleanField(required=False)
    AUTH_LDAP_CACERT_CONTENT = EncryptedField(required=False, allow_blank=True)
    AUTH_LDAP_CERT_CONTENT = EncryptedField(required=False, allow_blank=True)
    AUTH_LDAP_KEY_CONTENT = EncryptedField(required=False, allow_blank=True)
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
    mapped_groups = serializers.SerializerMethodField()
    mapped_roles = serializers.SerializerMethodField()
    existing = serializers.BooleanField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_mapping_preview(self, obj, field):
        previews = self.context.get('ldap_mapping_previews', {})
        return previews.get(id(obj), {}).get(field, [])

    def get_mapped_groups(self, obj):
        return self.get_mapping_preview(obj, 'mapped_groups')

    def get_mapped_roles(self, obj):
        return self.get_mapping_preview(obj, 'mapped_roles')

    def get_status(self, obj):
        previews = self.context.get('ldap_mapping_previews', {})
        error = previews.get(id(obj), {}).get('error')
        if error:
            return {'error': error}
        return obj.get('status')


class LDAPSettingSerializer(LDAPSerializerMixin, serializers.Serializer):
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
        max_length=4096, allow_blank=True, required=False, label=_('Search OU'),
        help_text=_(
            'User Search Base, if there are multiple OUs, you can separate them with the `|` symbol'
        )
    )
    AUTH_LDAP_SEARCH_FILTER = serializers.CharField(
        max_length=1024, required=True, label=_('Search filter'),
        help_text=_('Selection could include (cn|uid|sAMAccountName=%(user)s)')
    )
    AUTH_LDAP_USER_ATTR_MAP = user_attr_map_field(
        required=True, label=_('User attribute'),
        help_text=_(
            'User attribute mapping, where the `key` is this system user attribute name and the '
            '`value` is the LDAP service user attribute name'
        )
    )
    AUTH_LDAP_GROUP_ATTRIBUTE = ldap_attribute_field(
        max_length=256, required=False, allow_blank=True,
        label=_('Group attribute'),
        help_text=_('LDAP user attribute containing the user groups')
    )
    AUTH_LDAP_GROUP_SEARCH_OU = serializers.CharField(
        max_length=4096, required=False, allow_blank=True,
        label=_('Group search OU'),
        help_text=_('Group search base; leave blank to use the user search OU')
    )
    AUTH_LDAP_GROUP_SEARCH_FILTER = serializers.CharField(
        max_length=1024, required=False, allow_blank=True,
        validators=[validate_group_search_filter],
        label=_('Group search filter'),
        help_text=_('Group search filter containing exactly one `%s` placeholder')
    )
    AUTH_LDAP_GROUP_SEARCH_USER_ATTRIBUTE = ldap_attribute_field(
        max_length=256, required=False, allow_blank=True,
        label=_('Group search user attribute'),
        help_text=_(
            'User attribute substituted into the group search filter; '
            'leave blank to use the mapped username attribute, or use `dn` for the user DN'
        )
    )
    AUTH_LDAP_USER_GROUP_MAP = LDAPUserGroupMapSerializer(
        many=True, required=False, label=_('User group mapping')
    )
    AUTH_LDAP_USER_ROLE_MAP = LDAPUserRoleMapSerializer(
        many=True, required=False, label=_('User role mapping')
    )
    AUTH_LDAP_ALWAYS_UPDATE_USER = serializers.BooleanField(
        required=False, label=_('Always update user'),
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
    AUTH_LDAP_STRICT_SYNC = serializers.BooleanField(
        required=False, label=_('Strict sync'),
        help_text=_('In strict mode, users not found in LDAP will be disabled during full or automatic sync')
    )
    AUTH_LDAP_CACHE_TIMEOUT = serializers.IntegerField(
        min_value=0, max_value=3600 * 24 * 30 * 12,
        default=0,
        required=False, label=_('User DN cache timeout (s)'),
        help_text=_(
            'Caching the User DN obtained during user login authentication can effectively '
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
    AUTH_LDAP_START_TLS = serializers.BooleanField(
        required=False, label=_('StartTLS'),
        help_text=_('Use StartTLS to upgrade ldap:// connections to TLS')
    )
    AUTH_LDAP_CACERT_CONTENT = EncryptedField(
        allow_blank=True, required=False, write_only=True,
        label=_('CA certificate'),
        help_text=_('CA certificate for verifying LDAPS/StartTLS server')
    )
    AUTH_LDAP_CERT_CONTENT = EncryptedField(
        allow_blank=True, required=False, write_only=True,
        label=_('Client certificate'),
        help_text=_('Client certificate for mutual TLS (optional)')
    )
    AUTH_LDAP_KEY_CONTENT = EncryptedField(
        allow_blank=True, required=False, write_only=True,
        label=_('Client private key'),
        help_text=_('Client private key for mutual TLS (optional)')
    )

    category = User.Source.ldap.value
    periodic_key = 'AUTH_LDAP_SYNC_IS_PERIODIC'
    interval_key = 'AUTH_LDAP_SYNC_INTERVAL'
    crontab_key = 'AUTH_LDAP_SYNC_CRONTAB'

    def validate(self, attrs):
        attrs = super().validate(attrs)
        validate_group_mapping_source(self, attrs)
        return attrs

    def post_save(self):
        super().post_save()
        from settings.utils import LDAPSyncUtil
        LDAPSyncUtil(category=self.category).clear_cache()

    @staticmethod
    def import_task_function(**kwargs):
        from settings.tasks import import_ldap_user_periodic
        import_ldap_user_periodic(**kwargs)
