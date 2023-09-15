from django.utils.translation import gettext_noop

from .const import Scope, system_exclude_permissions, org_exclude_permissions

_view_root_perms = (
    ('orgs', 'organization', 'view', 'rootorg'),
)
_view_all_joined_org_perms = (
    ('orgs', 'organization', 'view', 'alljoinedorg'),
)

user_perms = (
    ('rbac', 'menupermission', 'view', 'workbench'),
    ('rbac', 'menupermission', 'view', 'webterminal'),
    ('rbac', 'menupermission', 'view', 'filemanager'),
    ('perms', 'permedasset', 'view,connect', 'myassets'),
    ('perms', 'permedapplication', 'view,connect', 'myapps'),
    ('assets', 'asset', 'match', 'asset'),
    ('assets', 'systemuser', 'match', 'systemuser'),
    ('assets', 'node', 'match', 'node'),
    ("ops", "adhoc", "*", "*"),
    ("ops", "playbook", "*", "*"),
    ("ops", "job", "*", "*"),
    ("ops", "jobexecution", "*", "*"),
    ("ops", "celerytaskexecution", "view", "*"),
)

system_user_perms = (
    ('authentication', 'connectiontoken', 'add,view,reuse,expire', 'connectiontoken'),
    ('authentication', 'temptoken', 'add,change,view', 'temptoken'),
    ('authentication', 'accesskey', '*', '*'),
    ('authentication', 'passkey', '*', '*'),
    ('tickets', 'ticket', 'view', 'ticket'),
)
system_user_perms += (user_perms + _view_all_joined_org_perms)

_auditor_perms = (
    ('rbac', 'menupermission', 'view', 'audit'),
    ('audits', '*', '*', '*'),
    ('audits', 'joblog', '*', '*'),
    ('terminal', 'commandstorage', 'view', 'commandstorage'),
    ('terminal', 'sessionreplay', 'view,download', 'sessionreplay'),
    ('terminal', 'session', '*', '*'),
    ('terminal', 'command', '*', '*'),
)

auditor_perms = user_perms + _auditor_perms

system_auditor_perms = system_user_perms + _auditor_perms + _view_root_perms

app_exclude_perms = [
    ('users', 'user', 'add,delete', 'user'),
    ('orgs', 'org', 'add,delete,change', 'org'),
    ('rbac', '*', '*', '*'),
]

need_check = [
    *auditor_perms, *user_perms, *app_exclude_perms,
    *system_exclude_permissions, *org_exclude_permissions
]
defines_errors = [d for d in need_check if len(d) != 4]
if len(defines_errors) != 0:
    raise ValueError('Perms define error: {}'.format(defines_errors))


class PredefineRole:
    id_prefix = '00000000-0000-0000-0000-00000000000'

    def __init__(self, index, name, scope, perms, perms_type='include'):
        self.id = self.id_prefix + index
        self.name = name
        self.scope = scope
        self.perms = perms
        self.perms_type = perms_type

    def get_role(self):
        from rbac.models import Role
        return Role.objects.get(id=self.id)

    @property
    def default_perms(self):
        from rbac.models import Permission
        q = Permission.get_define_permissions_q(self.perms)
        permissions = Permission.get_permissions(self.scope)

        if not q:
            permissions = permissions.none()
        elif self.perms_type == 'include':
            permissions = permissions.filter(q)
        else:
            permissions = permissions.exclude(q)

        perms = permissions.values_list('id', flat=True)
        return perms

    def _get_defaults(self):
        perms = self.default_perms
        defaults = {
            'id': self.id, 'name': self.name, 'scope': self.scope,
            'builtin': True, 'permissions': perms, 'created_by': 'System',
        }
        return defaults

    def update_or_create_role(self):
        from rbac.models import Role
        defaults = self._get_defaults()
        permissions = defaults.pop('permissions', [])
        role, created = Role.objects.update_or_create(defaults, id=self.id)
        role.permissions.set(permissions)
        return role, created


class BuiltinRole:
    system_admin = PredefineRole(
        '1', gettext_noop('SystemAdmin'), Scope.system, []
    )
    system_auditor = PredefineRole(
        '2', gettext_noop('SystemAuditor'), Scope.system, system_auditor_perms
    )
    system_component = PredefineRole(
        '4', gettext_noop('SystemComponent'), Scope.system, app_exclude_perms, 'exclude'
    )
    system_user = PredefineRole(
        '3', gettext_noop('User'), Scope.system, system_user_perms
    )
    org_admin = PredefineRole(
        '5', gettext_noop('OrgAdmin'), Scope.org, []
    )
    org_auditor = PredefineRole(
        '6', gettext_noop('OrgAuditor'), Scope.org, auditor_perms
    )
    org_user = PredefineRole(
        '7', gettext_noop('OrgUser'), Scope.org, user_perms
    )
    system_role_mapper = None
    org_role_mapper = None

    @classmethod
    def get_roles(cls):
        roles = {
            k: v
            for k, v in cls.__dict__.items()
            if isinstance(v, PredefineRole)
        }
        return roles

    @classmethod
    def get_system_role_by_old_name(cls, name):
        if not cls.system_role_mapper:
            cls.system_role_mapper = {
                'App': cls.system_component.get_role(),
                'Admin': cls.system_admin.get_role(),
                'User': cls.system_user.get_role(),
                'Auditor': cls.system_auditor.get_role()
            }
        return cls.system_role_mapper.get(name, cls.system_role_mapper['User'])

    @classmethod
    def get_org_role_by_old_name(cls, name):
        if not cls.org_role_mapper:
            cls.org_role_mapper = {
                'Admin': cls.org_admin.get_role(),
                'User': cls.org_user.get_role(),
                'Auditor': cls.org_auditor.get_role(),
            }
        return cls.org_role_mapper.get(name, cls.org_role_mapper['User'])

    @classmethod
    def sync_to_db(cls, show_msg=False):
        roles = cls.get_roles()
        print("  - Update builtin roles")

        for pre_role in roles.values():
            role, created = pre_role.update_or_create_role()
            if show_msg:
                print("    - Update: {} - {}".format(role.name, created))
