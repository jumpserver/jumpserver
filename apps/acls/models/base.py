from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.db.models import JMSBaseModel
from common.utils import contains_ip
from orgs.mixins.models import OrgModelMixin, OrgManager

__all__ = [
    'ACLManager',
    'BaseACL',
    'BaseACLQuerySet',
    'UserAssetAccountBaseACL',
    'UserAssetAccountACLQuerySet'
]


class ActionChoices(models.TextChoices):
    reject = 'reject', _('Reject')
    accept = 'accept', _('Accept')
    review = 'review', _('Review')


class BaseACLQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def valid(self):
        return self.active()

    def invalid(self):
        return self.inactive()


class UserAssetAccountACLQuerySet(BaseACLQuerySet):
    def filter_user(self, username):
        q = Q(users__username_group__contains=username) | \
            Q(users__username_group__contains='*')
        return self.filter(q)

    def filter_asset(self, name=None, address=None):
        queryset = self.filter()
        if name:
            q = Q(assets__name_group__contains=name) | \
                Q(assets__name_group__contains='*')
            queryset = queryset.filter(q)
        if address:
            ids = [
                q.id for q in queryset
                if contains_ip(address, q.assets.get('address_group', []))
            ]
            queryset = queryset.filter(id__in=ids)
        return queryset

    def filter_account(self, username):
        q = Q(accounts__username_group__contains=username) | \
            Q(accounts__username_group__contains='*')
        return self.filter(q)


class ACLManager(OrgManager):
    def valid(self):
        return self.get_queryset().valid()


class BaseACL(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    priority = models.IntegerField(
        default=50, verbose_name=_("Priority"),
        help_text=_("1-100, the lower the value will be match first"),
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    action = models.CharField(max_length=64, default=ActionChoices.reject, verbose_name=_('Action'))
    reviewers = models.ManyToManyField('users.User', blank=True, verbose_name=_("Reviewers"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    ActionChoices = ActionChoices
    objects = ACLManager.from_queryset(BaseACLQuerySet)()

    class Meta:
        ordering = ('priority', 'date_updated', 'name')
        abstract = True

    def is_action(self, action):
        return self.action == action


class UserAssetAccountBaseACL(BaseACL, OrgModelMixin):
    # username_group
    users = models.JSONField(verbose_name=_('User'))
    # name_group, address_group
    assets = models.JSONField(verbose_name=_('Asset'))
    # username_group
    accounts = models.JSONField(verbose_name=_('Account'))

    objects = ACLManager.from_queryset(UserAssetAccountACLQuerySet)()

    class Meta(BaseACL.Meta):
        unique_together = ('name', 'org_id')
        abstract = True

    @classmethod
    def filter_queryset(cls, user=None, asset=None, account=None, account_username=None, **kwargs):
        queryset = cls.objects.all()
        org_id = None
        if user:
            queryset = queryset.filter_user(user.username)
        if asset:
            org_id = asset.org_id
            queryset = queryset.filter_asset(asset.name, asset.address)
        if account:
            org_id = account.org_id
            queryset = queryset.filter_account(account.username)
        if account_username:
            queryset = queryset.filter_account(username=account_username)
        if org_id:
            kwargs['org_id'] = org_id
        if kwargs:
            queryset = queryset.filter(**kwargs)
        return queryset
