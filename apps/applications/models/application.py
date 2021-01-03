from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin
from common.mixins import CommonModelMixin
from .. import const


class Application(CommonModelMixin, OrgModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    category = models.CharField(
        max_length=16, choices=const.ApplicationCategoryChoices.choices, verbose_name=_('Category')
    )
    type = models.CharField(
        max_length=16, choices=const.ApplicationTypeChoices.choices, verbose_name=_('Type')
    )
    domain = models.ForeignKey(
        'assets.Domain', null=True, blank=True, related_name='applications',
        on_delete=models.SET_NULL, verbose_name=_("Domain"),
    )
    attrs = models.JSONField(default=dict, verbose_name=_('Attrs'))
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        ordering = ('name',)

    def __str__(self):
        category_display = self.get_category_display()
        type_display = self.get_type_display()
        return f'{self.name}({type_display})[{category_display}]'

    @property
    def category_remote_app(self):
        return self.category == const.ApplicationCategoryChoices.remote_app.value
