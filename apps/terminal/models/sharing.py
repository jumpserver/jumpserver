from django.db import models
from common.mixins import CommonModelMixin
from orgs.mixins.models import OrgModelMixin
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from .session import Session


__all__ = ['SessionSharing', 'SessionJoinRecord']


class SessionSharing(CommonModelMixin, OrgModelMixin):
    session = models.ForeignKey(
        'terminal.Session', on_delete=models.CASCADE, verbose_name=_('Session')
    )
    creator = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_('User')
    )
    verify_code = models.CharField(max_length=16, verbose_name=_('Verify code'))
    is_active = models.BooleanField(
        default=True, verbose_name=_('Active'), db_index=True
    )
    expired_time = models.IntegerField(
        default=0, verbose_name=_('Expired time (min)'), db_index=True
    )

    def is_valid(self):
        pass


class SessionJoinRecord(CommonModelMixin, OrgModelMixin):
    LOGIN_FROM = Session.LOGIN_FROM

    session = models.ForeignKey(
        'terminal.Session', on_delete=models.CASCADE, verbose_name=_('Session')
    )
    sharing = models.ForeignKey(
        SessionSharing, on_delete=models.CASCADE,
        verbose_name=_('Session share')
    )
    joiner = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_('User')
    )
    date_joined = models.DateTimeField(
        verbose_name=_("Date start"), db_index=True, default=timezone.now
    )
    date_left = models.DateTimeField(
        verbose_name=_("Date end"), null=True, db_index=True
    )
    remote_addr = models.CharField(
        max_length=128, verbose_name=_("Remote addr"), blank=True, null=True,
        db_index=True
    )
    login_from = models.CharField(
        max_length=2, choices=LOGIN_FROM.choices, default="WT",
        verbose_name=_("Login from")
    )
    is_success = models.BooleanField(default=True, db_index=True)
    reason = models.CharField(
        max_length=1024, blank=True, null=True, verbose_name=_('Reason')
    )
    is_finished = models.BooleanField(default=False, db_index=True)
