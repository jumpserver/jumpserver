from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.models import OrgModelMixin, OrgManager
from .base import BaseACL, BaseACLQuerySet
from common.utils.ip import contains_ip


class ACLManager(OrgManager):

    def valid(self):
        return self.get_queryset().valid()


class LoginAssetACL(BaseACL, OrgModelMixin):
    class ActionChoices(models.TextChoices):
        login_confirm = 'login_confirm', _('Login confirm')

    # 条件
    users = models.JSONField(verbose_name=_('User'))
    accounts = models.JSONField(verbose_name=_('Account'), default=dict)
    assets = models.JSONField(verbose_name=_('Asset'))
    # 动作
    action = models.CharField(
        max_length=64, choices=ActionChoices.choices, default=ActionChoices.login_confirm,
        verbose_name=_('Action')
    )
    # 动作: 附加字段
    # - login_confirm
    reviewers = models.ManyToManyField(
        'users.User', related_name='review_login_asset_acls', blank=True,
        verbose_name=_("Reviewers")
    )

    objects = ACLManager.from_queryset(BaseACLQuerySet)()

    class Meta:
        unique_together = ('name', 'org_id')
        ordering = ('priority', '-date_updated', 'name')
        verbose_name = _('Login asset acl')

    def __str__(self):
        return self.name

    @classmethod
    def filter(cls, user, asset, account, action):
        queryset = cls.objects.filter(action=action)
        queryset = cls.filter_user(user, queryset)
        queryset = cls.filter_asset(asset, queryset)
        queryset = cls.filter_account(account, queryset)
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
            Q(assets__hostname_group__contains=asset.name) |
            Q(assets__hostname_group__contains='*')
        )
        ids = [q.id for q in queryset if contains_ip(asset.address, q.assets.get('ip_group', []))]
        queryset = cls.objects.filter(id__in=ids)
        return queryset

    @classmethod
    def filter_account(cls, account, queryset):
        queryset = queryset.filter(
            Q(accounts__name_group__contains=account.name) |
            Q(accounts__name_group__contains='*')
        ).filter(
            Q(accounts__username_group__contains=account.username) |
            Q(accounts__username_group__contains='*')
        )
        return queryset

    @classmethod
    def create_login_asset_confirm_ticket(cls, user, asset, account, assignees, org_id):
        from tickets.const import TicketType
        from tickets.models import ApplyLoginAssetTicket
        title = _('Login asset confirm') + ' ({})'.format(user)
        data = {
            'title': title,
            'org_id': org_id,
            'applicant': user,
            'apply_login_user': user,
            'apply_login_asset': asset,
            'apply_login_account': str(account),
            'type': TicketType.login_asset_confirm,
        }
        ticket = ApplyLoginAssetTicket.objects.create(**data)
        ticket.open_by_system(assignees)
        return ticket

