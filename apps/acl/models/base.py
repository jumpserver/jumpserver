
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from common.mixins import CommonModelMixin


__all__ = ['BaseACL']


class BaseACL(CommonModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    priority = models.IntegerField(
        default=50, verbose_name=_("Priority"),
        help_text=_("1-100, the higher will be match first"),
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        abstract = True

