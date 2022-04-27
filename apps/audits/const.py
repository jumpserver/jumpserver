# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

DEFAULT_CITY = _("Unknown")

MODELS_NEED_RECORD = (
    # users
    'User', 'UserGroup',
    # acls
    'LoginACL', 'LoginAssetACL', 'LoginConfirmSetting',
    # assets
    'Asset', 'Node', 'AdminUser', 'SystemUser', 'Domain', 'Gateway', 'CommandFilterRule',
    'CommandFilter', 'Platform', 'AuthBook',
    # applications
    'Application',
    # orgs
    'Organization',
    # settings
    'Setting',
    # perms
    'AssetPermission', 'ApplicationPermission',
    # xpack
    'License', 'Account', 'SyncInstanceTask', 'ChangeAuthPlan', 'GatherUserTask',
)
