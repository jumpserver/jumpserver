from django.db import models
from django.utils.translation import gettext_lazy as _

from perms.const import ActionChoices
from .general import Ticket

__all__ = ['ApplyAssetTicket']

asset_or_node_help_text = _("Select at least one asset or node")


class ApplyAssetTicket(Ticket):
    apply_permission_name = models.CharField(max_length=128, verbose_name=_('Permission name'))
    apply_nodes = models.ManyToManyField('assets.Node', verbose_name=_('Node'))
    # 申请信息
    apply_assets = models.ManyToManyField('assets.Asset', verbose_name=_('Asset'))
    apply_accounts = models.JSONField(default=list, verbose_name=_('Apply accounts'))
    apply_actions = models.IntegerField(verbose_name=_('Actions'), default=ActionChoices.connect)
    apply_date_start = models.DateTimeField(verbose_name=_('Date start'), null=True)
    apply_date_expired = models.DateTimeField(verbose_name=_('Date expired'), null=True)

    def get_apply_actions_display(self):
        return ActionChoices.display(self.apply_actions)

    class Meta:
        verbose_name = _('Apply Asset Ticket')
