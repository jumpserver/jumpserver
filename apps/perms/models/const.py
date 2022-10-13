from django.db import models
from django.utils.translation import ugettext_lazy as _
from common.db.models import BitOperationChoice


__all__ = ['Action', 'SpecialAccount']


class Action(BitOperationChoice):
    ALL = 0xff
    CONNECT = 0b1
    UPLOAD = 0b1 << 1
    DOWNLOAD = 0b1 << 2
    CLIPBOARD_COPY = 0b1 << 3
    CLIPBOARD_PASTE = 0b1 << 4
    UPDOWNLOAD = UPLOAD | DOWNLOAD
    CLIPBOARD_COPY_PASTE = CLIPBOARD_COPY | CLIPBOARD_PASTE

    DB_CHOICES = (
        (ALL, _('All')),
        (CONNECT, _('Connect')),
        (UPLOAD, _('Upload file')),
        (DOWNLOAD, _('Download file')),
        (UPDOWNLOAD, _("Upload download")),
        (CLIPBOARD_COPY, _('Clipboard copy')),
        (CLIPBOARD_PASTE, _('Clipboard paste')),
        (CLIPBOARD_COPY_PASTE, _('Clipboard copy paste'))
    )

    NAME_MAP = {
        ALL: "all",
        CONNECT: "connect",
        UPLOAD: "upload_file",
        DOWNLOAD: "download_file",
        UPDOWNLOAD: "updownload",
        CLIPBOARD_COPY: 'clipboard_copy',
        CLIPBOARD_PASTE: 'clipboard_paste',
        CLIPBOARD_COPY_PASTE: 'clipboard_copy_paste'
    }

    NAME_MAP_REVERSE = {v: k for k, v in NAME_MAP.items()}
    CHOICES = []
    for i, j in DB_CHOICES:
        CHOICES.append((NAME_MAP[i], j))


class SpecialAccount(models.TextChoices):
    ALL = '@ALL', 'All'
