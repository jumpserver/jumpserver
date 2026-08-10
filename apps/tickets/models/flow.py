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
        with tmp_to_org(org):
            query = RelatedManager.get_to_filter_qs(self.users.value, user_qs.model)
            assignees = user_qs.filter(*query).distinct()
            return assignees


class TicketFlow(JMSBaseModel, OrgModelMixin):
    name = models.CharField(
        max_length=128, blank=True, default='', verbose_name=_('Name')
    )
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
    cc_users = models.ManyToManyField(
        'users.User', related_name='cc_ticket_flows', blank=True,
        verbose_name=_('CC users')
    )

    class Meta:
        verbose_name = _('Ticket flow')

    def __str__(self):
        return self.name or self.get_type_display()

    @classmethod
    def get_org_related_flows(cls, org_id=None):
        if org_id:
            with tmp_to_org(org_id):
                flows = cls.objects.all()
        else:
            flows = cls.objects.all()

        # A flow in the current organization only overrides a global flow with
        # the same type and name. Different named flows of the same type must
        # remain available after multiple flows per type became supported.
        current_flow_keys = list(flows.values_list('type', 'name'))
        root_id = Organization.ROOT_ID
        with tmp_to_org(root_id):
            diff_global_flows = cls.objects.filter(org_id=root_id)
            for flow_type, name in current_flow_keys:
                diff_global_flows = diff_global_flows.exclude(
                    type=flow_type, name__iexact=name
                )
        return flows | diff_global_flows
