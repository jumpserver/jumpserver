# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import JSONManyToManyField, RelatedManager
from common.db.models import JMSBaseModel
from orgs.mixins.models import OrgModelMixin
from orgs.models import Organization
from orgs.utils import tmp_to_org, current_org
from users.models import User
from ..const import TicketType, TicketLevel

__all__ = ['TicketFlow', 'ApprovalRule']


class ApprovalRule(JMSBaseModel):
    level = models.SmallIntegerField(
        default=TicketLevel.one,
        choices=TicketLevel.choices,
        verbose_name=_('Approve level')
    )
    users = JSONManyToManyField('users.User', default=dict, verbose_name=_('Users'))

    class Meta:
        verbose_name = _('Ticket flow approval rule')

    def __str__(self):
        return '{}({})'.format(self.id, self.level)

    def get_assignees(self, org_id=None):
        org = Organization.get_instance(org_id, default=current_org)
        user_qs = User.get_org_users(org=org)
        query = RelatedManager.get_to_filter_qs(self.users.value, user_qs.model)
        assignees = user_qs.filter(*query).distinct()
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
