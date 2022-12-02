from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.mixins import CommonModelMixin
from common.utils import contains_ip

__all__ = ['BaseACL', 'BaseACLQuerySet', 'ACLManager', 'AssetAccountUserACLQuerySet']


class ActionChoices(models.TextChoices):
    reject = 'reject', _('Reject')
    accept = 'allow', _('Allow')
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


class AssetAccountUserACLQuerySet(BaseACLQuerySet):
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
        queryset = self.filter(id__in=ids)
        return queryset

    def filter_account(self, account_username):
        return self.filter(
            Q(accounts__username_group__contains=account_username) |
            Q(accounts__username_group__contains='*')
        )


class ACLManager(models.Manager):
    def valid(self):
        return self.get_queryset().valid()


class BaseACL(CommonModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    priority = models.IntegerField(
        default=50, verbose_name=_("Priority"),
        help_text=_("1-100, the lower the value will be match first"),
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    action = models.CharField(max_length=64, default=ActionChoices.reject, verbose_name=_('Action'))
    reviewers = models.ManyToManyField('users.User', blank=True, verbose_name=_("Reviewers"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    objects = ACLManager.from_queryset(BaseACLQuerySet)()
    ActionChoices = ActionChoices

    class Meta:
        abstract = True
