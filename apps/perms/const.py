# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db.fields import BitChoices
from common.utils.integer import bit

__all__ = ["ActionChoices"]


class ActionChoices(BitChoices):
    connect = bit(1), _("Connect")
    upload = bit(2), _("Upload")
    download = bit(3), _("Download")
    copy = bit(4), _("Copy")
    paste = bit(5), _("Paste")

    @classmethod
    def is_tree(cls):
        return True

    @classmethod
    def branches(cls):
        return (
            cls.connect,
            (_("Transfer"), [cls.upload, cls.download]),
            (_("Clipboard"), [cls.copy, cls.paste]),
        )

    @classmethod
    def has_perm(cls, action_name, total):
        action_value = getattr(cls, action_name)
        return action_value & total == action_value

    @classmethod
    def display(cls, value):
        return ', '.join([str(c.label) for c in cls if c.value & value == c.value])
