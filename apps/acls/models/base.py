from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import JSONManyToManyField
from common.db.models import JMSBaseModel
from common.utils import contains_ip
from common.utils.time_period import contains_time_period
from orgs.mixins.models import OrgModelMixin, OrgManager
from ..const import ActionChoices

__all__ = [
    'BaseACL', 'UserBaseACL', 'UserAssetAccountBaseACL',
]

from orgs.utils import tmp_to_root_org
from orgs.utils import tmp_to_org


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
        ordering = ('priority', '-is_active', 'name')
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
        with tmp_to_root_org():
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
    def _get_filter_queryset(cls, user=None, asset=None, account=None, account_username=None, **kwargs):
        queryset = cls.objects.all()
        q = models.Q()

        if asset:
            q &= cls.assets.get_filter_q(asset)
        if user:
            q &= cls.users.get_filter_q(user)
        if account and not account_username:
            account_username = account.username
        if account_username:
            q &= models.Q(accounts__contains=account_username) | \
                 models.Q(accounts__contains='*') | \
                 models.Q(accounts__contains='@ALL')
        if kwargs:
            q &= models.Q(**kwargs)
        queryset = queryset.filter(q)
        return queryset.valid().distinct()

    @classmethod
    def filter_queryset(cls, asset=None, **kwargs):
        org_id = asset.org_id if asset else ''
        with tmp_to_org(org_id):
            return cls._get_filter_queryset(asset=asset, **kwargs)
