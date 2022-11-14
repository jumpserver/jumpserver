# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

DEFAULT_CITY = _("Unknown")

MODELS_NEED_RECORD = (
    # users
    'User', 'UserGroup',
    # authentication
    'AccessKey', 'TempToken',
    # acls
    'LoginACL', 'LoginAssetACL', 'LoginConfirmSetting',
    # assets
    'Asset', 'Node', 'AdminUser', 'SystemUser', 'Domain', 'Gateway', 'CommandFilterRule',
    'CommandFilter', 'Platform', 'Label',
    # applications
    'Application',
    # account
    'AuthBook',
    # orgs
    'Organization',
    # settings
    'Setting',
    # perms
    'AssetPermission', 'ApplicationPermission',
    # notifications
    'SystemMsgSubscription', 'UserMsgSubscription',
    # Terminal
    'Terminal', 'Endpoint', 'EndpointRule', 'CommandStorage', 'ReplayStorage',
    # rbac
    'Role', 'SystemRole', 'OrgRole', 'RoleBinding', 'OrgRoleBinding', 'SystemRoleBinding',
    # xpack
    'License', 'Account', 'SyncInstanceTask', 'ChangeAuthPlan', 'ApplicationChangeAuthPlan',
    'GatherUserTask', 'Interface',
)
