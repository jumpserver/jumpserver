from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket

__all__ = ['ApplyAssetTicket']

asset_or_node_help_text = _("Select at least one asset or node")


class ApplyAssetTicket(Ticket):
    apply_permission_name = models.CharField(max_length=128, verbose_name=_('Permission name'))
    apply_nodes = models.ManyToManyField('assets.Node', verbose_name=_('Apply nodes'))
    # 申请信息
    apply_assets = models.ManyToManyField('assets.Asset', verbose_name=_('Apply assets'))
    apply_accounts = models.JSONField(default=list, verbose_name=_('Apply accounts'))
    apply_actions = models.IntegerField(default=1, verbose_name=_('Actions'))
    apply_date_start = models.DateTimeField(verbose_name=_('Date start'), null=True)
    apply_date_expired = models.DateTimeField(verbose_name=_('Date expired'), null=True)

    @property
    def apply_actions_display(self):
        return 'Todo'

    def get_apply_actions_display(self):
        return ', '.join(self.apply_actions_display)
