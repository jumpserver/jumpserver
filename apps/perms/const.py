# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _

from common.db.fields import BitChoices
from common.utils.integer import bit

__all__ = ["ActionChoices"]


class ActionChoices(BitChoices):
    connect = bit(1), _("Connect (All protocols)")
    upload = bit(2), _("Upload (RDP, SFTP)")
    download = bit(3), _("Download (RDP, SFTP)")
    copy = bit(4), _("Copy (RDP, VNC)")
    paste = bit(5), _("Paste (RDP, VNC)")
    delete = bit(6), _("Delete (SFTP)")
    share = bit(7), _("Share (SSH)")

    @classmethod
    def is_tree(cls):
        return True

    @classmethod
    def branches(cls):
        return (
            cls.connect,
            (_("Transfer"), [cls.upload, cls.download, cls.delete]),
            (_("Clipboard"), [cls.copy, cls.paste]),
            cls.share
        )

    @classmethod
    def transfer(cls):
        return cls.upload | cls.download | cls.delete

    @classmethod
    def clipboard(cls):
        return cls.copy | cls.paste

    @classmethod
    def contains(cls, total, action_value):
        return action_value & total == action_value

    @classmethod
    def display(cls, value):
        return ', '.join([str(c.label) for c in cls if c.value & value == c.value])
