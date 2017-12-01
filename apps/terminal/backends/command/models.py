# -*- coding: utf-8 -*-
#
import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _


class AbstractSessionCommand(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=64, verbose_name=_("User"))
    asset = models.CharField(max_length=128, verbose_name=_("Asset"))
    system_user = models.CharField(max_length=64, verbose_name=_("System user"))
    input = models.CharField(max_length=128, db_index=True, verbose_name=_("Input"))
    output = models.CharField(max_length=1024, verbose_name=_("Output"))
    session = models.CharField(max_length=36, db_index=True, verbose_name=_("Session"))
    timestamp = models.IntegerField(db_index=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.input
