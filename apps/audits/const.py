# -*- coding: utf-8 -*-
#
from django.db.models import TextChoices, IntegerChoices
from django.utils.translation import gettext_lazy as _

DEFAULT_CITY = _("Unknown")

MODELS_NEED_RECORD = set()


class OperateChoices(TextChoices):
    mkdir = "mkdir", _("Mkdir")
    rmdir = "rmdir", _("Rmdir")
    delete = "delete", _("Delete")
    upload = "upload", _("Upload")
    rename = "rename", _("Rename")
    symlink = "symlink", _("Symlink")
    download = "download", _("Download")
    rename_dir = "rename_dir", _("Rename dir")


class ActionChoices(TextChoices):
    view = "view", _("View")
    update = "update", _("Update")
    delete = "delete", _("Delete")
    create = "create", _("Create")
    # Activities action
    download = "download", _("Download")
    connect = "connect", _("Connect")
    login = "login", _("Login")
    change_auth = "change_password", _("Change password")

    accept = 'accept', _('Accept')
    review = 'review', _('Review')
    notice = 'notice', _('Notifications')
    reject = 'reject', _('Reject')
    approve = 'approve', _('Approve')
    close = 'close', _('Close')


class LoginTypeChoices(TextChoices):
    web = "W", _("Web")
    terminal = "T", _("Terminal")
    unknown = "U", _("Unknown")


class ActivityChoices(TextChoices):
    operate_log = 'O', _('Operate log')
    session_log = 'S', _('Session log')
    login_log = 'L', _('Login log')
    task = 'T', _('Task')


class MFAChoices(IntegerChoices):
    disabled = 0, _("Disabled")
    enabled = 1, _("Enabled")
    unknown = 2, _("-")


class LoginStatusChoices(IntegerChoices):
    success = True, _("Success")
    failed = False, _("Failed")
