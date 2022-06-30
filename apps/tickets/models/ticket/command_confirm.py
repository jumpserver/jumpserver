from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket


class ApplyCommandTicket(Ticket):
    apply_run_user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, verbose_name=_('Run user')
    )
    apply_run_asset = models.CharField(max_length=128, verbose_name=_('Run asset'))
    apply_run_system_user = models.ForeignKey(
        'assets.SystemUser', on_delete=models.SET_NULL,
        null=True, verbose_name=_('Run system user')
    )
    apply_run_command = models.CharField(max_length=4096, verbose_name=_('Run command'))
    apply_from_session = models.ForeignKey(
        'terminal.Session', on_delete=models.SET_NULL,
        null=True, verbose_name=_("Session")
    )
    apply_from_cmd_filter = models.ForeignKey(
        'assets.CommandFilter', on_delete=models.SET_NULL,
        null=True, verbose_name=_('From cmd filter')
    )
    apply_from_cmd_filter_rule = models.ForeignKey(
        'assets.CommandFilterRule', on_delete=models.SET_NULL,
        null=True, verbose_name=_('From cmd filter rule')
    )
