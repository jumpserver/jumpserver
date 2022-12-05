# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from django.db.models import TextChoices, IntegerChoices

DEFAULT_CITY = _("Unknown")

MODELS_NEED_RECORD = (
    # users
    'User', 'UserGroup',
    # authentication
    'AccessKey', 'TempToken',
    "User",
    "UserGroup",
    # acls
    "LoginACL",
    "LoginAssetACL",
    "LoginConfirmSetting",
    # assets
    'Asset', 'Node', 'AdminUser', 'SystemUser', 'Domain', 'Gateway', 'CommandFilterRule',
    'CommandFilter', 'Platform', 'Label',
    # applications
    'Application',
    # account
    'AuthBook',
    # orgs
    "Organization",
    # settings
    "Setting",
    # perms
    'AssetPermission',
    # notifications
    'SystemMsgSubscription', 'UserMsgSubscription',
    # Terminal
    'Terminal', 'Endpoint', 'EndpointRule', 'CommandStorage', 'ReplayStorage',
    # rbac
    'Role', 'SystemRole', 'OrgRole', 'RoleBinding', 'OrgRoleBinding', 'SystemRoleBinding',
    # xpack
    'License', 'Account', 'SyncInstanceTask', 'ChangeAuthPlan',
    'GatherUserTask', 'Interface',
)


class OperateChoices(TextChoices):
    mkdir = "mkdir", _("Mkdir")
    rmdir = "rmdir", _("Rmdir")
    delete = "delete", _("Delete")
    upload = "upload", _("Upload")
    rename = "rename", _("Rename")
    symlink = "symlink", _("Symlink")
    download = "download", _("Download")


class ActionChoices(TextChoices):
    view = "view", _("View")
    update = "update", _("Update")
    delete = "delete", _("Delete")
    create = "create", _("Create")


class LoginTypeChoices(TextChoices):
    web = "W", _("Web")
    terminal = "T", _("Terminal")
    unknown = "U", _("Unknown")


class MFAChoices(IntegerChoices):
    disabled = 0, _("Disabled")
    enabled = 1, _("Enabled")
    unknown = 2, _("-")


class LoginStatusChoices(IntegerChoices):
    success = True, _("Success")
    failed = False, _("Failed")
