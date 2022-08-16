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
    'CommandFilter', 'Platform', 'Account',
    # applications
    # orgs
    'Organization',
    # settings
    'Setting',
    # perms
    'AssetPermission',
    # xpack
    'License', 'Account', 'SyncInstanceTask', 'ChangeAuthPlan', 'GatherUserTask',
)
