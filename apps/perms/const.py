# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils.integer import bit
from common.db.fields import BitChoices


__all__ = ['SpecialAccount', 'ActionChoices']


class ActionChoices(BitChoices):
    connect = bit(0), _('Connect')
    upload = bit(1), _('Upload')
    download = bit(2), _('Download')
    copy = bit(3), _('Copy')
    paste = bit(4), _('Paste')

    @classmethod
    def branches(cls):
        return (
            (_('Transfer'), [cls.upload, cls.download]),
            (_('Clipboard'), [cls.copy, cls.paste]),
        )


# class Action(BitOperationChoice):
#     CONNECT = 0b1
#     UPLOAD = 0b1 << 1
#     DOWNLOAD = 0b1 << 2
#     COPY = 0b1 << 3
#     PASTE = 0b1 << 4
#     ALL = 0 << 8
#     TRANSFER = UPLOAD | DOWNLOAD
#     CLIPBOARD = COPY | PASTE
#
#     DB_CHOICES = (
#         (ALL, _('All')),
#         (CONNECT, _('Connect')),
#         (UPLOAD, _('Upload file')),
#         (DOWNLOAD, _('Download file')),
#         (TRANSFER, _("Upload download")),
#         (COPY, _('Clipboard copy')),
#         (PASTE, _('Clipboard paste')),
#         (CLIPBOARD, _('Clipboard copy paste'))
#     )
#
#     NAME_MAP = {
#         ALL: "all",
#         CONNECT: "connect",
#         UPLOAD: "upload",
#         DOWNLOAD: "download",
#         TRANSFER: "transfer",
#         COPY: 'copy',
#         PASTE: 'paste',
#         CLIPBOARD: 'clipboard'
#     }
#
#     NAME_MAP_REVERSE = {v: k for k, v in NAME_MAP.items()}
#     CHOICES = []
#     for i, j in DB_CHOICES:
#         CHOICES.append((NAME_MAP[i], j))
#
#     @classmethod
#     def choices(cls):
#         pass
#

class SpecialAccount(models.TextChoices):
    ALL = '@ALL', 'All'
