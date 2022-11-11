# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db.fields import BitChoices
from common.utils.integer import bit

__all__ = ["SpecialAccount", "ActionChoices"]


class ActionChoices(BitChoices):
    connect = bit(0), _("Connect")
    upload = bit(1), _("Upload")
    download = bit(2), _("Download")
    copy = bit(3), _("Copy")
    paste = bit(4), _("Paste")

    @classmethod
    def is_tree(cls):
        return True

    @classmethod
    def branches(cls):
        return (
            (_("Transfer"), [cls.upload, cls.download]),
            (_("Clipboard"), [cls.copy, cls.paste]),
        )


class SpecialAccount(models.TextChoices):
    ALL = "@ALL", "All"
