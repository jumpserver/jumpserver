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

