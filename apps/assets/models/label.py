# -*- coding: utf-8 -*-
#

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Label(models.Model):
    SYSTEM_CATEGORY = "S"
    USER_CATEGORY = "U"
    CATEGORY_CHOICES = (
        ("S", _("System")),
        ("U", _("User"))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    alias = models.CharField(max_length=128, verbose_name=_("Alias"), blank=True)
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    category = models.CharField(max_length=128, choices=CATEGORY_CHOICES, verbose_name=_("Category"))
    is_active = models.BooleanField(default=False, verbose_name=_("Is active"))
    date_created = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Date created')
    )

    class Meta:
        db_table = "assets_label"
