from django.db import models
from django.utils.translation import ugettext_lazy as _


class Scope(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


exclude_permissions = [
    ('assets', 'add_asset'),

    ('users', 'view_user'),
    ('users', 'add_usergroup'),
    ('users', 'change_usergroup'),
    ('users', 'delete_usergroup'),
]


system_scope_permissions = [
    ('users', 'delete_user'),
    ('rbac', 'add_role'),
    ('rbac', 'change_role'),
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
