from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from .base import BaseACL, BaseACLQuerySet
from common.utils import get_request_ip, get_ip_city
from common.utils.ip import contains_ip


class ACLManager(models.Manager):

    def valid(self):
        return self.get_queryset().valid()


class LoginACL(BaseACL):
    class ActionChoices(models.TextChoices):
        reject = 'reject', _('Reject')
        allow = 'allow', _('Allow')
        confirm = 'confirm', _('Login confirm')

    # 用户
    users = models.JSONField(default=dict, verbose_name=_('User match'))
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, verbose_name=_('User'),
        null=True, blank=True, related_name='login_acls'
    )
    # 规则
    ip_group = models.JSONField(default=list, verbose_name=_('Login IP'))
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
        queryset = (cls.objects.filter(
            Q(users__username_group__contains=user.username) |
            Q(users__username_group__contains='*')
        ) | user.login_acls.all()).valid().distinct()
        return queryset

    @staticmethod
    def allow_user_to_login(user, ip):
        acl = LoginACL.filter_acl(user).exclude(action=LoginACL.ActionChoices.confirm).first()
        if not acl:
            return True
        is_contained = contains_ip(ip, acl.ip_group)
        if acl.action_allow and is_contained:
            return True
        if acl.action_reject and not is_contained:
            return True
        return False

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
