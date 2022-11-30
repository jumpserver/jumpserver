from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.models import OrgModelMixin, OrgManager
from .base import BaseACL, BaseACLQuerySet
from common.utils.ip import contains_ip


class ACLQuerySet(BaseACLQuerySet):
    def filter_user(self, user):
        return self.filter(
            Q(users__username_group__contains=user.username) |
            Q(users__username_group__contains='*')
        )

    def filter_asset(self, asset):
        queryset = self.filter(
            Q(assets__name_group__contains=asset.name) |
            Q(assets__name_group__contains='*')
        )
        ids = [
            q.id for q in queryset
            if contains_ip(asset.address, q.assets.get('address_group', []))
        ]
        queryset = LoginAssetACL.objects.filter(id__in=ids)
        return queryset

    def filter_account(self, account_username):
        return self.filter(
            Q(accounts__username_group__contains=account_username) |
            Q(accounts__username_group__contains='*')
        )


class ACLManager(OrgManager):

    def valid(self):
        return self.get_queryset().valid()


class LoginAssetACL(BaseACL, OrgModelMixin):
    class ActionChoices(models.TextChoices):
        login_confirm = 'login_confirm', _('Login confirm')

    # 条件
    users = models.JSONField(verbose_name=_('User'))
    accounts = models.JSONField(verbose_name=_('Account'))
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

    objects = ACLManager.from_queryset(ACLQuerySet)()

    class Meta:
        unique_together = ('name', 'org_id')
        ordering = ('priority', '-date_updated', 'name')
        verbose_name = _('Login asset acl')

    def __str__(self):
        return self.name

    @classmethod
    def create_login_asset_confirm_ticket(cls, user, asset, account_username, assignees, org_id):
        from tickets.const import TicketType
        from tickets.models import ApplyLoginAssetTicket
        title = _('Login asset confirm') + ' ({})'.format(user)
        data = {
            'title': title,
            'org_id': org_id,
            'applicant': user,
            'apply_login_user': user,
            'apply_login_asset': asset,
            'apply_login_account': account_username,
            'type': TicketType.login_asset_confirm,
        }
        ticket = ApplyLoginAssetTicket.objects.create(**data)
        ticket.open_by_system(assignees)
        return ticket

