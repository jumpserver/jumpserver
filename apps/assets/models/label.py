# -*- coding: utf-8 -*-
#

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from orgs.mixins import OrgModelMixin


class Label(OrgModelMixin):
    SYSTEM_CATEGORY = "S"
    USER_CATEGORY = "U"
    CATEGORY_CHOICES = (
        ("S", _("System")),
        ("U", _("User"))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    category = models.CharField(max_length=128, choices=CATEGORY_CHOICES,
                                default=USER_CATEGORY, verbose_name=_("Category"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("Comment"))
    date_created = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Date created')
    )

    @classmethod
    def get_queryset_group_by_name(cls):
        names = cls.objects.values_list('name', flat=True)
        for name in names:
            yield name, cls.objects.filter(name=name)

    def __str__(self):
        return "{}:{}".format(self.name, self.value)

    class Meta:
        db_table = "assets_label"
        unique_together = [('name', 'value', 'org_id')]
