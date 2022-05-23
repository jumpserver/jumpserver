from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Ticket

from applications.const import AppCategory, AppType

__all__ = ['ApplyApplicationTicket']


class ApplyApplicationTicket(Ticket):
    apply_permission_name = models.CharField(max_length=128,  verbose_name=_('Apply name'))
    # 申请信息
    apply_category = models.CharField(
        choices=AppCategory.choices, verbose_name=_('Category'),
        allow_null=True,
    )
    apply_type = models.CharField(
        choices=AppType.choices, verbose_name=_('Type'),
        allow_null=True
    )
    apply_applications = models.ManyToManyField(
        'applications.Application',
        required=True, verbose_name=_('Apply applications'),
        allow_null=True
    )
    apply_applications_display = models.JSONField(
        verbose_name=_('Apply applications display')
    )
    apply_system_users = models.ManyToManyField(
        'assets.SystemUser', verbose_name=_('Apply system users'),
    )
    apply_system_users_display = models.JSONField(
        verbose_name=_('Apply system user display'), allow_null=True,
    )
    apply_date_start = models.DateTimeField(
        required=True, verbose_name=_('Date start'), allow_null=True
    )
    apply_date_expired = models.DateTimeField(
        required=True, verbose_name=_('Date expired'), allow_null=True
    )
