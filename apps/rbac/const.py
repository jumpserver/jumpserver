from django.db import models
from django.utils.translation import ugettext_lazy as _


class Scope(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


exclude_permissions = (
    ('auth', '*', '*'),
    ('authentication', 'loginconfirmsetting', '*'),
    ('captcha', '*', '*'),
    ('contenttypes', '*', '*'),
    ('django_cas_ng', '*', '*'),
    ('django_celery_beat', '*', '*'),
    ('jms_oidc_rp', '*', '*'),
    ('admin', '*', '*'),
    ('sessions', '*', '*'),
    ('notifications', '*', '*'),

    ('applications', 'historicalaccount', '*'),
    ('applications', 'databaseapp', '*'),
    ('applications', 'k8sapp', '*'),
    ('applications', 'remoteapp', '*'),
    ('assets', 'adminuser', '*'),
    ('assets', 'assetgroup', '*'),
    ('assets', 'cluster', '*'),
    ('assets', 'favoriteasset', '*'),
    ('assets', 'historicalauthbook', '*'),
    ('assets', 'assetuser', '*'),
    ('authentication', 'privatetoken', '*'),
    ('perms', 'databaseapppermission', '*'),
    ('perms', 'k8sapppermission', '*'),
    ('perms', 'remoteapppermission', '*'),
    ('perms', 'userassetgrantedtreenoderelation', '*'),
    ('perms', 'usergrantedmappingnode', '*'),
    ('perms', 'permnode', '*'),
    ('perms', 'rebuildusertreetask', '*'),
    ('rbac', 'contenttype', '*'),
    ('rbac', 'permission', 'add_permission'),
    ('rbac', 'permission', 'delete_permission'),
    ('rbac', 'permission', 'change_permission'),
    ('ops', 'adhoc', '*'),
    ('ops', 'adhocexecution', '*'),
    ('ops', 'celerytask', '*'),
    ('ops', 'task', 'add_task'),
    ('ops', 'task', 'change_task'),
    ('orgs', 'organizationmember', '*'),
    ('settings', 'setting', 'add_setting'),
    ('settings', 'setting', 'delete_setting'),
    ('audits', 'operatelog', 'add_operatelog'),
    ('audits', 'operatelog', 'delete_operatelog'),
    ('audits', 'operatelog', 'change_operatelog'),
    ('audits', 'passwordchangelog', 'add_passwordchangelog'),
    ('audits', 'passwordchangelog', 'change_passwordchangelog'),
    ('audits', 'passwordchangelog', 'delete_passwordchangelog'),
    ('audits', 'userloginlog', 'change_userloginlog'),
    ('audits', 'userloginlog', 'delete_userloginlog'),
    ('audits', 'userloginlog', 'change_userloginlog'),
    ('audits', 'ftplog', 'change_ftplog'),
    ('audits', 'ftplog', 'delete_ftplog'),
    ('terminal', 'session', 'delete_session'),
    ('tickets', '*', '*'),
    ('users', 'userpasswordhistory', '*'),
    ('xpack', 'interface', 'add_interface'),
    ('xpack', 'interface', 'delete_interface'),
)


system_scope_permissions = (
    ('users', 'users', 'delete_user'),
    ('rbac', '*', '*'),
    ('orgs', 'organization', '*'),
    ('xpack', 'license', '*'),
    ('settings', 'setting', '*'),
)


auditor_permissions = (
    ('audits', '*', '*'),
    ('rbac', 'extralpermission', 'view_auditview'),
    ('terminal', 'session', '*'),
    ('terminal', 'command', '*'),
)

user_permissions = (
    ('rbac', 'extralpermission', 'view_userview'),
)

app_permissions = [
    ('terminal', '*', '*'),
    ('acls', 'loginacl', 'view_loginacl'),
    ('acls', 'loginassetacl', 'view_loginassetacl'),
    ('applications', 'application', 'view_application'),
    ('applications', 'applicationuser', 'view_applicationuser'),
    ('assets', 'asset', 'view_asset'),
]


class PreRole:
    def __init__(self, name, scope, perms):
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
    system_admin = PreRole('SystemAdmin', Scope.system, [])
    system_auditor = PreRole('SystemAuditor', Scope.system, auditor_permissions)
    system_app = PreRole('App', Scope.system, app_permissions)
    system_user = PreRole('SystemUser', Scope.system, user_permissions)
    org_admin = PreRole('OrgAdmin', Scope.org, [])
    org_auditor = PreRole('OrgAuditor', Scope.org, auditor_permissions)
    org_user = PreRole('OrgUser', Scope.org, user_permissions)

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

