# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from orgs.mixins.models import OrgModelMixin
from orgs.models import Organization
from orgs.utils import tmp_to_org, get_current_org_id
from users.models import User
from ..const import TicketType, TicketLevel, TicketApprovalStrategy

__all__ = ['TicketFlow', 'ApprovalRule']


class ApprovalRule(JMSBaseModel):
    level = models.SmallIntegerField(
        default=TicketLevel.one, choices=TicketLevel.choices,
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

    class Meta:
        verbose_name = _('Ticket flow approval rule')

    def __str__(self):
        return '{}({})'.format(self.id, self.level)

    def get_assignees(self, org_id=None):
        assignees = []
        org_id = org_id if org_id else get_current_org_id()
        with tmp_to_org(org_id):
            if self.strategy == TicketApprovalStrategy.super_admin:
                assignees = User.get_super_admins()
            elif self.strategy == TicketApprovalStrategy.org_admin:
                assignees = User.get_org_admins()
            elif self.strategy == TicketApprovalStrategy.super_org_admin:
                assignees = User.get_super_and_org_admins()
            elif self.strategy == TicketApprovalStrategy.custom_user:
                assignees = self.assignees.all()
        return assignees


class TicketFlow(JMSBaseModel, OrgModelMixin):
    type = models.CharField(
        max_length=64, choices=TicketType.choices,
        default=TicketType.general, verbose_name=_("Type")
    )
    approval_level = models.SmallIntegerField(
        default=TicketLevel.one,
        choices=TicketLevel.choices,
        verbose_name=_('Approve level')
    )
    rules = models.ManyToManyField(ApprovalRule, related_name='ticket_flows')

    class Meta:
        verbose_name = _('Ticket flow')

    def __str__(self):
        return '{}'.format(self.type)

    @classmethod
    def get_org_related_flows(cls, org_id=None):
        if org_id:
            with tmp_to_org(org_id):
                flows = cls.objects.all()
        else:
            flows = cls.objects.all()
        cur_flow_types = flows.values_list('type', flat=True)
        root_id = Organization.ROOT_ID
        with tmp_to_org(root_id):
            diff_global_flows = cls.objects.exclude(type__in=cur_flow_types).filter(org_id=root_id)
        return flows | diff_global_flows
