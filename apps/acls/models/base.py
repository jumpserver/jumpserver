from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import JSONManyToManyField
from common.db.models import JMSBaseModel
from orgs.mixins.models import OrgModelMixin

__all__ = [
    'BaseACL', 'UserAssetAccountBaseACL',
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
    objects = BaseACLQuerySet.as_manager()

    class Meta:
        ordering = ('priority', 'date_updated', 'name')
        abstract = True

    def is_action(self, action):
        return self.action == action


class UserAssetAccountBaseACL(BaseACL, OrgModelMixin):
    users = JSONManyToManyField('users.User', default=dict, verbose_name=_('Users'))
    assets = JSONManyToManyField('assets.Asset', default=dict, verbose_name=_('Assets'))
    accounts = models.JSONField(default=list, verbose_name=_("Account"))

    class Meta(BaseACL.Meta):
        unique_together = ('name', 'org_id')
        abstract = True
