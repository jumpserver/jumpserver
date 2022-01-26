from django.db import models
from django.utils.translation import ugettext_lazy as _


class Scope(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


exclude_permissions = (
    # ('App', 'Model', 'Action', 'Resource') Model 和 Resource 可能不同
    # users.add_user
    ('auth', '*', '*', '*'),
    ('authentication', 'loginconfirmsetting', '*', '*'),
    ('captcha', '*', '*', '*'),
    ('contenttypes', '*', '*', '*'),
    ('django_cas_ng', '*', '*', '*'),
    ('django_celery_beat', '*', '*', '*'),
    ('jms_oidc_rp', '*', '*', '*'),
    ('admin', '*', '*', '*'),
    ('sessions', '*', '*', '*'),
    ('notifications', '*', '*', '*'),

    ('applications', 'historicalaccount', '*', '*'),
    ('applications', 'databaseapp', '*', '*'),
    ('applications', 'k8sapp', '*', '*'),
    ('applications', 'remoteapp', '*', '*'),
    ('assets', 'adminuser', '*', '*'),
    ('assets', 'assetgroup', '*', '*'),
    ('assets', 'cluster', '*', '*'),
    ('assets', 'favoriteasset', '*', '*'),
    ('assets', 'historicalauthbook', '*', '*'),
    ('assets', 'assetuser', '*', '*'),
    ('authentication', 'privatetoken', '*', '*'),
    ('perms', 'databaseapppermission', '*', '*'),
    ('perms', 'k8sapppermission', '*', '*'),
    ('perms', 'remoteapppermission', '*', '*'),
    ('perms', 'userassetgrantedtreenoderelation', '*', '*'),
    ('perms', 'usergrantedmappingnode', '*', '*'),
    ('perms', 'permnode', '*', '*'),
    ('perms', 'rebuildusertreetask', '*', '*'),
    ('rbac', 'contenttype', '*', '*'),
    ('rbac', 'permission', 'add,delete,change', 'permission'),
    ('ops', 'adhoc', '*', '*'),
    ('ops', 'adhocexecution', '*', '*'),
    ('ops', 'celerytask', '*', '*'),
    ('ops', 'task', 'add,change', 'task'),
    ('orgs', 'organizationmember', '*', '*'),
    ('settings', 'setting', 'add,delete', 'setting'),
    ('audits', 'operatelog', 'add,delete,change', 'operatelog'),
    ('audits', 'passwordchangelog', 'add,change,delete', 'passwordchangelog'),
    ('audits', 'userloginlog', 'change,delete,change', 'userloginlog'),
    ('audits', 'ftplog', 'change,delete', 'ftplog'),
    ('terminal', 'session', 'delete', 'session'),
    ('tickets', '*', '*', '*'),
    ('users', 'userpasswordhistory', '*', '*'),
    ('xpack', 'interface', 'add,delete', 'interface'),
)


only_system_permissions = (
    ('users', 'user', 'delete', 'user'),
    ('rbac', 'role', 'delete,add,change', 'role'),
    ('rbac', 'systemrole', '*', '*'),
    ('rbac', 'rolebinding', '*', '*'),
    ('rbac', 'systemrolebinding', '*', '*'),
    ('orgs', 'organization', '*', '*'),
    ('xpack', 'license', '*', '*'),
    ('settings', 'setting', '*', '*'),
)

only_org_permissions = (
)

system_exclude_permissions = list(exclude_permissions) + list(only_org_permissions)
org_exclude_permissions = list(exclude_permissions) + list(only_system_permissions)
