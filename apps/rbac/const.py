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
    ('common', 'setting', '*', '*'),

    ('authentication', 'privatetoken', '*', '*'),
    ('users', 'userpasswordhistory', '*', '*'),
    ('applications', 'applicationuser', '*', '*'),
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
    ('perms', 'databaseapppermission', '*', '*'),
    ('perms', 'k8sapppermission', '*', '*'),
    ('perms', 'remoteapppermission', '*', '*'),
    ('perms', 'userassetgrantedtreenoderelation', '*', '*'),
    ('perms', 'usergrantedmappingnode', '*', '*'),
    ('perms', 'permnode', '*', '*'),
    ('perms', 'rebuildusertreetask', '*', '*'),
    ('perms', 'permedasset', 'add,change,delete', 'permedasset'),
    ('perms', 'permedapplication', 'add,change,delete', 'permedapplication'),
    ('rbac', 'contenttype', '*', '*'),
    ('rbac', 'permission', 'add,delete,change', 'permission'),
    ('rbac', 'rolebinding', '*', '*'),
    ('rbac', 'role', '*', '*'),
    ('ops', 'adhoc', '*', '*'),
    ('ops', 'adhocexecution', 'delete,change', '*'),
    ('ops', 'celerytask', '*', '*'),
    ('ops', 'task', 'add,change', 'task'),
    ('ops', 'commandexecution', 'delete,change', 'commandexecution'),
    ('orgs', 'organizationmember', '*', '*'),
    ('settings', 'setting', 'add,delete', 'setting'),
    ('audits', 'operatelog', 'add,delete,change', 'operatelog'),
    ('audits', 'passwordchangelog', 'add,change,delete', 'passwordchangelog'),
    ('audits', 'userloginlog', 'add,change,delete,change', 'userloginlog'),
    ('audits', 'ftplog', 'change,delete', 'ftplog'),
    ('tickets', 'ticket', '*', '*'),
    ('tickets', 'comment', 'change,delete', 'comment'),
    ('tickets', 'ticketstep', '*', '*'),
    ('tickets', 'ticketapprovalrule', '*', '*'),
    ('xpack', 'interface', '*', '*'),
    ('xpack', 'license', '*', '*'),
    ('common', 'permission', 'add,delete,view,change', 'permission'),
    ('terminal', 'command', 'delete,change', 'command'),
    ('terminal', 'status', 'delete,change', 'status'),
    ('terminal', 'sessionjoinrecord', 'delete', 'sessionjoinrecord'),
    ('terminal', 'sessionreplay', 'delete', 'sessionreplay'),
    ('terminal', 'session', 'delete', 'session'),
    ('terminal', 'session', 'delete,change', 'command'),
)


only_system_permissions = (
    ('users', 'user', 'delete', 'user'),
    ('rbac', 'role', 'delete,add,change', 'role'),
    ('rbac', 'systemrole', '*', '*'),
    ('rbac', 'rolebinding', '*', '*'),
    ('rbac', 'systemrolebinding', '*', '*'),
    ('rbac', 'orgrole', 'delete,add,change', '*'),
    ('rbac', 'orgrolebinding', 'delete,add,change', '*'),
    ('orgs', 'organization', '*', '*'),
    ('xpack', 'license', '*', '*'),
    ('settings', 'setting', '*', '*'),
    ('ops', 'task', 'view', 'taskmonitor'),
    ('terminal', 'terminal', '*', '*'),
    ('terminal', 'commandstorage', '*', '*'),
    ('terminal', 'replaystorage', '*', '*'),
    ('terminal', 'status', '*', '*'),
    ('terminal', 'task', '*', '*'),
    ('tickets', 'ticketflow', '*', '*'),
)

only_org_permissions = (
)

system_exclude_permissions = list(exclude_permissions) + list(only_org_permissions)
org_exclude_permissions = list(exclude_permissions) + list(only_system_permissions)
