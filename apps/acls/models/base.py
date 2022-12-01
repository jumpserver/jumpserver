from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from common.mixins import CommonModelMixin


__all__ = ['BaseACL', 'BaseACLQuerySet', 'ACLManager']


class ActionChoices(models.TextChoices):
    reject = 'reject', _('Reject')
    allow = 'allow', _('Allow')
    confirm = 'confirm', _('Confirm')


class BaseACLQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def valid(self):
        return self.active()

    def invalid(self):
        return self.inactive()


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
    action = models.CharField(
        max_length=64, verbose_name=_('Action'),
        choices=ActionChoices.choices, default=ActionChoices.reject
    )
    reviewers = models.ManyToManyField('users.User', blank=True, verbose_name=_("Reviewers"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    objects = ACLManager.from_queryset(BaseACLQuerySet)()
    ActionChoices = ActionChoices

    class Meta:
        abstract = True
