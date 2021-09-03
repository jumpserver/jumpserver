from django.db import models
from common.mixins import CommonModelMixin
from orgs.mixins.models import OrgModelMixin
from django.utils.translation import ugettext_lazy as _
from .terminal import Terminal


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
    share = models.ForeignKey(SessionShare, on_delete=models.SET_NULL, verbose_name=_('Session share'))
    session = models.ForeignKey('terminal.Session', on_delete=models.SET_NULL, verbose_name=_('Session'))
    user = ''
    date_joined = ''
    date_left = ''
    remote_addr = ''
    login_from = ''
    is_success = ''
    reason = ''
    is_finished = ''
    terminal = models.ForeignKey('terminal.Terminal', on_delete=models.SET_NULL, verbose_name=_('Terminal'))
