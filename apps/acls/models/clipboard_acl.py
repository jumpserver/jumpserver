from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from perms.const import ActionChoices as PermActionChoices
from .base import UserAssetAccountBaseACL

__all__ = ['ClipboardACL']


class ClipboardACL(UserAssetAccountBaseACL):
    operations = models.IntegerField(
        default=PermActionChoices.clipboard(),
        verbose_name=_('Operations'),
    )
    copy_text_limit = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Copy text character limit'),
        help_text=_('0 means unlimited, unit: characters'),
    )
    paste_text_limit = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Paste text character limit'),
        help_text=_('0 means unlimited, unit: characters'),
    )
    download_file_size_limit = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Download file size limit'),
        help_text=_('0 means unlimited, unit: MB'),
    )
    upload_file_size_limit = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Upload file size limit'),
        help_text=_('0 means unlimited, unit: MB'),
    )

    class Meta(UserAssetAccountBaseACL.Meta):
        verbose_name = _('Clipboard acl')
        abstract = False

    def __str__(self):
        return self.name

    def matches_operation(self, operation):
        return self.operations & operation == operation
