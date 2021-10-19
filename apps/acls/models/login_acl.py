from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from .base import BaseACL, BaseACLQuerySet
from common.utils import get_request_ip, get_ip_city
from common.utils.ip import contains_ip
from common.utils.time_period import contains_time_period


class ACLManager(models.Manager):

    def valid(self):
        return self.get_queryset().valid()


class LoginACL(BaseACL):
    class ActionChoices(models.TextChoices):
        reject = 'reject', _('Reject')
        allow = 'allow', _('Allow')
        confirm = 'confirm', _('Login confirm')

    # 用户
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, verbose_name=_('User'),
        related_name='login_acls'
    )
    # 规则
    rules = models.JSONField(default=dict, verbose_name=_('Rule'))
    # 动作
    action = models.CharField(
        max_length=64, verbose_name=_('Action'),
        choices=ActionChoices.choices, default=ActionChoices.reject
    )
    reviewers = models.ManyToManyField(
        'users.User', verbose_name=_("Reviewers"),
        related_name="login_confirm_acls", blank=True
    )
    objects = ACLManager.from_queryset(BaseACLQuerySet)()

    class Meta:
        ordering = ('priority', '-date_updated', 'name')

    def __str__(self):
        return self.name

    @property
    def action_reject(self):
        return self.action == self.ActionChoices.reject

    @property
    def action_allow(self):
        return self.action == self.ActionChoices.allow

    @classmethod
    def filter_acl(cls, user):
        return user.login_acls.all().valid().distinct()

    @staticmethod
    def allow_user_to_login(user, ip):
        acl = LoginACL.filter_acl(user).exclude(action=LoginACL.ActionChoices.confirm).first()
        if not acl:
            return True, ''
        ip_group = acl.rules.get('ip_group')
        time_periods = acl.rules.get('time_period')
        is_contain_ip = contains_ip(ip, ip_group)
        is_contain_time_period = contains_time_period(time_periods)
        if (acl.action_allow and is_contain_ip and is_contain_time_period) or \
                (acl.action_reject and not is_contain_ip and not is_contain_time_period):
            return True, ''
        if not (acl.action_allow and is_contain_ip) or \
                not (not acl.action_reject and not is_contain_ip):
            return False, 'ip'
        if not (acl.action_allow and is_contain_time_period) or \
                not (not acl.action_reject and not is_contain_time_period):
            return False, 'time'

    @staticmethod
    def construct_confirm_ticket_meta(request=None):
        login_ip = get_request_ip(request) if request else ''
        login_ip = login_ip or '0.0.0.0'
        login_city = get_ip_city(login_ip)
        login_datetime = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        ticket_meta = {
            'apply_login_ip': login_ip,
            'apply_login_city': login_city,
            'apply_login_datetime': login_datetime,
        }
        return ticket_meta

    def create_confirm_ticket(self, request=None):
        from tickets import const
        from tickets.models import Ticket
        from orgs.models import Organization
        ticket_title = _('Login confirm') + ' {}'.format(self.user)
        ticket_meta = self.construct_confirm_ticket_meta(request)
        data = {
            'title': ticket_title,
            'type': const.TicketType.login_confirm.value,
            'meta': ticket_meta,
            'org_id': Organization.ROOT_ID,
        }
        ticket = Ticket.objects.create(**data)
        ticket.create_process_map_and_node(self.reviewers.all())
        ticket.open(self.user)
        return ticket
