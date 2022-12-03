from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_request_ip, get_ip_city
from common.utils.ip import contains_ip
from common.utils.time_period import contains_time_period
from common.utils.timezone import local_now_display
from .base import BaseACL


class LoginACL(BaseACL):
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='login_acls', verbose_name=_('User')
    )
    # 规则, ip_group, time_period
    rules = models.JSONField(default=dict, verbose_name=_('Rule'))

    class Meta:
        ordering = ('priority', '-date_updated', 'name')
        verbose_name = _('Login acl')

    def __str__(self):
        return self.name

    def is_action(self, action):
        return self.action == action

    @classmethod
    def filter_acl(cls, user):
        return user.login_acls.all().valid().distinct()

    @staticmethod
    def match(user, ip):
        acl_qs = LoginACL.filter_acl(user)
        if not acl_qs:
            return

        for acl in acl_qs:
            if acl.is_action(LoginACL.ActionChoices.confirm) and \
                    not acl.reviewers.exists():
                continue
            ip_group = acl.rules.get('ip_group')
            time_periods = acl.rules.get('time_period')
            is_contain_ip = contains_ip(ip, ip_group)
            is_contain_time_period = contains_time_period(time_periods)
            if is_contain_ip and is_contain_time_period:
                # 满足条件，则返回
                return acl

    def create_confirm_ticket(self, request):
        from tickets import const
        from tickets.models import ApplyLoginTicket
        from orgs.models import Organization
        title = _('Login confirm') + ' {}'.format(self.user)
        login_ip = get_request_ip(request) if request else ''
        login_ip = login_ip or '0.0.0.0'
        login_city = get_ip_city(login_ip)
        login_datetime = local_now_display()
        data = {
            'title': title,
            'applicant': self.user,
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
