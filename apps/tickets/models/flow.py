# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin
from common.db.encoder import ModelJSONFieldEncoder
from orgs.mixins.models import OrgModelMixin
from orgs.models import Organization
from orgs.utils import tmp_to_root_org
from ..const import TicketType, TicketApprovalLevel, TicketApprovalStrategy
from ..signals import post_or_update_change_ticket_flow_approval

__all__ = ['TicketFlow', 'ApprovalRule']


class ApprovalRule(CommonModelMixin):
    level = models.SmallIntegerField(
        default=TicketApprovalLevel.one, choices=TicketApprovalLevel.choices,
        verbose_name=_('Approve level')
    )
    strategy = models.CharField(
        max_length=64, default=TicketApprovalStrategy.super_admin,
        choices=TicketApprovalStrategy.choices,
        verbose_name=_('Approve strategy')
    )
    # 受理人列表
    assignees = models.ManyToManyField(
        'users.User', related_name='assigned_ticket_flow_approval_rule',
        verbose_name=_("Assignees")
    )
    assignees_display = models.JSONField(
        encoder=ModelJSONFieldEncoder, default=list,
        verbose_name=_('Assignees display')
    )

    class Meta:
        verbose_name = _('Ticket flow approval rule')

    def __str__(self):
        return '{}({})'.format(self.id, self.level)

    @classmethod
    def change_assignees_display(cls, qs):
        post_or_update_change_ticket_flow_approval.send(sender=cls, qs=qs)


class TicketFlow(CommonModelMixin, OrgModelMixin):
    type = models.CharField(
        max_length=64, choices=TicketType.choices,
        default=TicketType.general, verbose_name=_("Type")
    )
    approval_level = models.SmallIntegerField(
        default=TicketApprovalLevel.one,
        choices=TicketApprovalLevel.choices,
        verbose_name=_('Approve level')
    )
    rules = models.ManyToManyField(ApprovalRule, related_name='ticket_flows')

    class Meta:
        verbose_name = _('Ticket flow')

    def __str__(self):
        return '{}'.format(self.type)

    @classmethod
    def get_org_related_flows(cls):
        flows = cls.objects.all()
        cur_flow_types = flows.values_list('type', flat=True)
        with tmp_to_root_org():
            diff_global_flows = cls.objects.exclude(type__in=cur_flow_types).filter(org_id=Organization.ROOT_ID)
        return flows | diff_global_flows
