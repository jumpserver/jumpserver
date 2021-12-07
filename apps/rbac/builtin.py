from django.utils.translation import ugettext_lazy as _

from . import const


auditor_perms = (
    ('audits', '*', '*'),
    ('rbac', 'extralpermission', 'view_auditview'),
    ('terminal', 'session', '*'),
    ('terminal', 'command', '*'),
)

user_perms = (
    ('rbac', 'extralpermission', 'view_userview'),
)

app_perms = [
    ('terminal', '*', '*'),
    ('acls', 'loginacl', 'view_loginacl'),
    ('acls', 'loginassetacl', 'view_loginassetacl'),
    ('applications', 'application', 'view_application'),
    ('applications', 'applicationuser', 'view_applicationuser'),
    ('assets', 'asset', 'view_asset'),
]


class PreRole:
    def __init__(self, _id, name, scope, perms):
        self.id = _id
        self.name = name
        self.scope = scope
        self.perms = perms

    def get_role(self):
        from rbac.models import Role
        return Role.objects.get(name=self.name)

    def get_defaults(self):
        from rbac.models import Permission
        q = Permission.get_define_permissions_q(self.perms)
        permissions = Permission.get_permissions(self.scope)
        perms = permissions.filter(q).values_list('id', flat=True)
        defaults = {'scope': self.scope, 'builtin': True, 'name': self.name, permissions: perms}
        return defaults

    def get_or_create_role(self):
        from rbac.models import Role
        defaults = self.get_defaults()
        permissions = defaults.pop('permissions', [])
        role, created = Role.objects.get_or_create(defaults, name=self.name)
        role.permissions.set(permissions)
        return role, created


class BuiltinRole:
    system_admin = PreRole('SystemAdmin', const.Scope.system, [])
    system_auditor = PreRole('SystemAuditor', const.Scope.system, auditor_perms)
    system_user = PreRole('SystemUser', const.Scope.system, user_perms)
    system_app = PreRole('App', const.Scope.system, app_perms)
    org_admin = PreRole('OrgAdmin', const.Scope.org, [])
    org_auditor = PreRole('OrgAuditor', const.Scope.org, auditor_perms)
    org_user = PreRole('OrgUser', const.Scope.org, user_perms)

    @classmethod
    def get_roles(cls):
        roles = {
            k: v
            for k, v in cls.__dict__.items()
            if isinstance(v, PreRole)
        }
        return roles

    @classmethod
    def get_system_role_by_old_name(cls, name):
        mapper = {
            'App': cls.system_app,
            'Admin': cls.system_app,
            'User': cls.system_user,
            'Auditor': cls.system_auditor
        }
        return mapper[name].get_role()

    @classmethod
    def get_org_role_by_old_name(cls, name):
        mapper = {
            'Admin': cls.org_admin,
            'User': cls.org_user,
            'Auditor': cls.org_auditor,
        }
        return mapper[name].get_role()

    @classmethod
    def sync_to_db(cls):
        roles = cls.get_roles()

        for pre_role in roles.values():
            role, created = pre_role.get_or_create_role()
            print("Create builtin Role: {} - {}".format(role.name, created))

