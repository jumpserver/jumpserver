# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import JMSOrgBaseModel


class Label(JMSOrgBaseModel):
    SYSTEM_CATEGORY = "S"
    USER_CATEGORY = "U"
    CATEGORY_CHOICES = (
        ("S", _("System")),
        ("U", _("User"))
    )
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    category = models.CharField(max_length=128, choices=CATEGORY_CHOICES,
                                default=USER_CATEGORY, verbose_name=_("Category"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    @classmethod
    def get_queryset_group_by_name(cls):
        names = cls.objects.values_list('name', flat=True)
        for name in names:
            yield name, cls.objects.filter(name=name)

    @lazyproperty
    def asset_count(self):
        return self.assets.count()

    def __str__(self):
        return "{}:{}".format(self.name, self.value)

    class Meta:
        db_table = "assets_label"
        unique_together = [('name', 'value', 'org_id')]
        verbose_name = _('Label')
