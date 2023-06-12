from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import JSONManyToManyField
from common.db.models import JMSBaseModel
from common.utils import contains_ip
from common.utils.time_period import contains_time_period
from orgs.mixins.models import OrgModelMixin, OrgManager

__all__ = [
    'BaseACL', 'UserBaseACL', 'UserAssetAccountBaseACL',
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


class BaseACL(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    priority = models.IntegerField(
        default=50, verbose_name=_("Priority"),
        help_text=_("1-100, the lower the value will be match first"),
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    action = models.CharField(max_length=64, default=ActionChoices.reject, verbose_name=_('Action'))
    reviewers = models.ManyToManyField('users.User', blank=True, verbose_name=_("Reviewers"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    ActionChoices = ActionChoices
    objects = BaseACLQuerySet.as_manager()

    class Meta:
        ordering = ('priority', 'name')
        abstract = True

    def is_action(self, action):
        return self.action == action

    @classmethod
    def get_user_acls(cls, user):
        return cls.objects.none()

    @classmethod
    def get_match_rule_acls(cls, user, ip, acl_qs=None):
        if acl_qs is None:
            acl_qs = cls.get_user_acls(user)
        if not acl_qs:
            return

        for acl in acl_qs:
            if acl.is_action(ActionChoices.review) and not acl.reviewers.exists():
                continue
            ip_group = acl.rules.get('ip_group')
            time_periods = acl.rules.get('time_period')
            is_contain_ip = contains_ip(ip, ip_group) if ip_group else True
            is_contain_time_period = contains_time_period(time_periods) if time_periods else True

            if is_contain_ip and is_contain_time_period:
                # 满足条件，则返回
                return acl
        return None


class UserBaseACL(BaseACL):
    users = JSONManyToManyField('users.User', default=dict, verbose_name=_('Users'))

    class Meta(BaseACL.Meta):
        abstract = True

    @classmethod
    def get_user_acls(cls, user):
        queryset = cls.objects.all()
        q = cls.users.get_filter_q(user)
        queryset = queryset.filter(q)
        return queryset.filter(is_active=True).distinct()


class UserAssetAccountBaseACL(OrgModelMixin, UserBaseACL):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    assets = JSONManyToManyField('assets.Asset', default=dict, verbose_name=_('Assets'))
    accounts = models.JSONField(default=list, verbose_name=_("Accounts"))
    objects = OrgManager.from_queryset(BaseACLQuerySet)()

    class Meta(UserBaseACL.Meta):
        unique_together = [('name', 'org_id')]
        abstract = True

    @classmethod
    def filter_queryset(cls, user=None, asset=None, account=None, account_username=None, **kwargs):
        queryset = cls.objects.all()
        org_id = None

        if user:
            q = cls.users.get_filter_q(user)
            queryset = queryset.filter(q)
        if asset:
            org_id = asset.org_id
            q = cls.assets.get_filter_q(asset)
            queryset = queryset.filter(q)
        if account and not account_username:
            account_username = account.username
        if account_username:
            q = models.Q(accounts__contains=account_username) | \
                models.Q(accounts__contains='*') | \
                models.Q(accounts__contains='@ALL')
            queryset = queryset.filter(q)
        if org_id:
            kwargs['org_id'] = org_id
        if kwargs:
            queryset = queryset.filter(**kwargs)
        return queryset.valid().distinct()
