from django.db import models
from common.mixins import CommonModelMixin
from orgs.mixins.models import OrgModelMixin
from django.utils.translation import ugettext_lazy as _
from .terminal import Terminal
from django.utils import timezone
from .session import Session


class SessionShare(CommonModelMixin, OrgModelMixin):
    verify_code = models.IntegerField(verbose_name=_('Verify code'))
    link = models.CharField(max_length=1024, verbose_name=_('Share link'))
    session = models.ForeignKey('terminal.Session', on_delete=models.SET_NULL, verbose_name=_('Session'))
    terminal = models.ForeignKey('terminal.Terminal', on_delete=models.SET_NULL, verbose_name=_('Terminal'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    expired_time = models.IntegerField(default=0, verbose_name=_('Expired time (min)'))

    def is_valid(self):
        pass


class ShareJoinRecord(CommonModelMixin, OrgModelMixin):
    LOGIN_FROM = Session.LOGIN_FROM

    share = models.ForeignKey(SessionShare, on_delete=models.SET_NULL, verbose_name=_('Session share'))
    session = models.ForeignKey('terminal.Session', on_delete=models.SET_NULL, verbose_name=_('Session'))
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, verbose_name=_('User'))
    date_joined = models.DateTimeField(verbose_name=_("Date start"), db_index=True, default=timezone.now)
    date_left = models.DateTimeField(verbose_name=_("Date end"), null=True)
    remote_addr = models.CharField(max_length=128, verbose_name=_("Remote addr"), blank=True, null=True)
    login_from = models.CharField(max_length=2, choices=LOGIN_FROM.choices, default="WT", verbose_name=_("Login from"))
    is_success = models.BooleanField(default=True, db_index=True)
    reason = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_('Reason'))
    is_finished = models.BooleanField(default=False, db_index=True)
    terminal = models.ForeignKey('terminal.Terminal', on_delete=models.SET_NULL, verbose_name=_('Terminal'))
