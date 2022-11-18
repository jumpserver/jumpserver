from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket

__all__ = ['ApplyApplicationTicket']


class ApplyApplicationTicket(Ticket):
    apply_permission_name = models.CharField(max_length=128, verbose_name=_('Permission name'))
    # 申请信息
    apply_category = models.CharField(
        max_length=16, verbose_name=_('Category')
    )
    apply_type = models.CharField(
        max_length=16, verbose_name=_('Type')
    )
    apply_applications = models.ManyToManyField(
        'applications.Application', verbose_name=_('Apply applications'),
    )
    apply_system_users = models.ManyToManyField(
        'assets.SystemUser', verbose_name=_('Apply system users'),
    )
    apply_actions = models.IntegerField(
        choices=[
            (255, 'All'), (1, 'Connect'), (2, 'Upload file'), (4, 'Download file'), (6, 'Upload download'),
            (8, 'Clipboard copy'), (16, 'Clipboard paste'), (24, 'Clipboard copy paste')
        ], default=255, verbose_name=_('Actions')
    )
    apply_date_start = models.DateTimeField(verbose_name=_('Date start'), null=True)
    apply_date_expired = models.DateTimeField(verbose_name=_('Date expired'), null=True)
