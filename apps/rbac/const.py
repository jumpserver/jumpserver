from django.db import models
from django.utils.translation import ugettext_lazy as _


class Scope(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


exclude_permissions = [
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
    ('authentication', 'privatetoken', '*'),
    ('perms', 'databaseapppermission', '*'),
    ('perms', 'k8sapppermission', '*'),
    ('perms', 'remoteapppermission', '*'),
    ('perms', 'userassetgrantedtreenoderelation', '*'),
    ('perms', 'usergrantedmappingnode', '*'),
    ('perms', 'permnode', '*'),
    ('perms', 'rebuildusertreetask', '*'),
    ('rbac', 'contenttype', '*'),
    ('rbac', 'extrapermission', '*'),
    ('rbac', 'permission', '*'),
    ('ops', 'adhoc', '*'),
    ('ops', 'adhocexecution', '*'),
    ('ops', 'celerytask', '*'),
    ('ops', 'task', 'add_task'),
    ('ops', 'task', 'change_task'),
    ('organization', 'organizationmember', '*'),
    ('settings', 'setting', 'add_setting'),
    ('settings', 'setting', 'delete_setting'),
]


system_scope_permissions = [
    ('users', 'users', 'delete_user'),
    ('rbac', 'role', 'add_role'),
    ('rbac', 'role', 'change_role'),
    # 'delete_role',
    # 'view_role',
    # 'view_permission',
    # 'add_organization',
    # 'change_organization',
    # 'delete_organization',
    # 'view_organization',
    # 'change_license',
    # 'change_interface',
    # 'change_setting',
    # 'view_setting',
]
