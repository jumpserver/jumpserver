
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.models import OrgModelMixin
from .base import BaseACL
from ..utils import contains_ip


class LoginAssetACL(BaseACL, OrgModelMixin):
    class ActionChoices(models.TextChoices):
        login_confirm = 'login_confirm', _('Login confirm')

    # 条件
    users = models.JSONField(verbose_name=_('User'))
    system_users = models.JSONField(verbose_name=_('System User'))
    assets = models.JSONField(verbose_name=_('Asset'))
    # 动作
    action = models.CharField(
        max_length=64, choices=ActionChoices.choices, default=ActionChoices.login_confirm,
        verbose_name=_('Action')
    )
    # 动作: 附加字段
    # - login_confirm
    reviewers = models.ManyToManyField(
        'users.User', related_name='review_login_asset_confirm_acl', blank=True,
        verbose_name=_("Reviewers")
    )

    class Meta:
        unique_together = ('name', 'org_id')
        ordering = ('priority', 'name')

    @classmethod
    def filter(cls, user, asset, system_user, action=ActionChoices.login_confirm):
        queryset = cls.objects.filter(action=action, org_id=asset.org_id)
        queryset = cls.filter_user(user, queryset)
        queryset = cls.filter_asset(asset, queryset)
        queryset = cls.filter_system_user(system_user, queryset)
        return queryset

    @classmethod
    def filter_user(cls, user, queryset):
        queryset = queryset.filter(
            Q(users__username_group__contains=user.username) |
            Q(users__username_group__contains='*')
        )
        return queryset

    @classmethod
    def filter_asset(cls, asset, queryset):
        queryset = queryset.filter(
            Q(assets__hostname_group__contains=asset.hostname) |
            Q(assets__hostname_group__contains='*')
        )
        ids = [q.id for q in queryset if contains_ip(asset.ip, q.assets.get('ip_group', []))]
        queryset = cls.objects.filter(id__in=ids)
        return queryset

    @classmethod
    def filter_system_user(cls, system_user, queryset):
        queryset = queryset.filter(
            Q(system_users__name_group__contains=system_user.name) |
            Q(system_users__name_group__contains='*')
        ).filter(
            Q(system_users__username_group__contains=system_user.username) |
            Q(system_users__username_group__contains='*')
        ).filter(
            Q(system_users__protocol_group__contains=system_user.protocol) |
            Q(system_users__protocol_group__contains='*')
        )
        return queryset

    @classmethod
    def get_reviewers(cls, queryset):
        reviewers = set()
        for q in queryset:
            reviewers.update(list(q.reviewers.all()))
        return list(reviewers)

    @classmethod
    def create_login_asset_confirm_ticket(cls, user, asset, system_user, assignees):
        from tickets.const import TicketTypeChoices
        from tickets.models import Ticket
        data = {
            'title': _('Login asset confirm') + ' {}'.format(user),
            'type': TicketTypeChoices.login_asset_confirm,
            'meta': {
                'user': str(user),
                'asset': str(asset),
                'system_user': str(system_user),
            },
            'org_id': asset.org_id,
        }
        ticket = Ticket.objects.create(**data)
        ticket.assignees.set(assignees)
        ticket.open(applicant=user)
        return ticket

