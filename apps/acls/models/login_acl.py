from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import get_request_ip, get_ip_city
from common.utils.timezone import local_now_display
from .base import UserBaseACL


class LoginACL(UserBaseACL):
    # 规则, ip_group, time_period
    rules = models.JSONField(default=dict, verbose_name=_('Rule'))

    class Meta(UserBaseACL.Meta):
        verbose_name = _('Login acl')
        abstract = False

    def __str__(self):
        return self.name

    def is_action(self, action):
        return self.action == action

    def create_confirm_ticket(self, request, user):
        from tickets import const
        from tickets.models import ApplyLoginTicket
        from orgs.models import Organization
        title = _('Login confirm') + ' {}'.format(user)
        login_ip = get_request_ip(request) if request else ''
        login_ip = login_ip or '0.0.0.0'
        login_city = get_ip_city(login_ip)
        login_datetime = local_now_display()
        data = {
            'title': title,
            'applicant': user,
            'apply_login_ip': login_ip,
            'org_id': Organization.ROOT_ID,
            'apply_login_city': login_city,
            'apply_login_datetime': login_datetime,
            'type': const.TicketType.login_confirm,
        }
        ticket = ApplyLoginTicket.objects.create(**data)
        assignees = self.reviewers.all()
        ticket.open_by_system(assignees)
        return ticket
