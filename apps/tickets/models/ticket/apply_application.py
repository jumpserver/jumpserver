from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket
from applications.const import AppCategory, AppType

__all__ = ['ApplyApplicationTicket']


class ApplyApplicationTicket(Ticket):
    apply_permission_name = models.CharField(max_length=128, verbose_name=_('Permission name'))
    # 申请信息
    apply_category = models.CharField(
        max_length=16, choices=AppCategory.choices, verbose_name=_('Category')
    )
    apply_type = models.CharField(
        max_length=16, choices=AppType.choices, verbose_name=_('Type')
    )
    apply_applications = models.ManyToManyField(
        'applications.Application', verbose_name=_('Apply applications'),
    )
    apply_system_users = models.ManyToManyField(
        'assets.SystemUser', verbose_name=_('Apply system users'),
    )
    apply_date_start = models.DateTimeField(verbose_name=_('Date start'), null=True)
    apply_date_expired = models.DateTimeField(verbose_name=_('Date expired'), null=True)

    @property
    def apply_category_display(self):
        return AppCategory.get_label(self.apply_category)

    @property
    def apply_type_display(self):
        return AppType.get_label(self.apply_type)
