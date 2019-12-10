# coding: utf-8
#

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin
from common.mixins import CommonModelMixin
from common.fields.model import EncryptCharField
from .. import const


__all__ = ['DatabaseApp']


class DatabaseApp(CommonModelMixin, OrgModelMixin):
    LOGIN_AUTO = 'auto'
    LOGIN_MANUAL = 'manual'
    LOGIN_MODE_CHOICES = (
        (LOGIN_AUTO, _('Automatic login')),
        (LOGIN_MANUAL, _('Manually login'))
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(
        default=const.DATABASE_APP_TYPE_MYSQL,
        choices=const.DATABASE_APP_TYPE_CHOICES,
        max_length=128, verbose_name=_('Database type')
    )
    host = models.CharField(
        max_length=128, verbose_name=_('Host'), db_index=True
    )
    port = models.IntegerField(default=3306, verbose_name=_('Port'))
    database = models.CharField(
        max_length=128, blank=True, null=True, verbose_name=_('Database'),
        db_index=True
    )
    login_mode = models.CharField(
        choices=LOGIN_MODE_CHOICES, default=LOGIN_AUTO, max_length=10,
        verbose_name=_('Login mode')
    )
    user = models.CharField(
        max_length=32, blank=True, db_index=True, verbose_name=_('Username')
    )
    password = EncryptCharField(
        max_length=128, blank=True, null=True, verbose_name=_('Password')
    )
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    class Meta:
        unique_together = [('org_id', 'name'), ]
        verbose_name = _("DatabaseApp")
        ordering = ('name', )
