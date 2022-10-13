# -*- coding: utf-8 -*-
#
import uuid
import os

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models


class CeleryTask(models.Model):
    LOG_DIR = os.path.join(settings.PROJECT_DIR, 'data', 'celery')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=1024)
    args = models.JSONField(verbose_name=_("Args"))
    kwargs = models.JSONField(verbose_name=_("Kwargs"))
    state = models.CharField(max_length=16, verbose_name=_("State"))
    is_finished = models.BooleanField(default=False, verbose_name=_("Finished"))
    date_published = models.DateTimeField(auto_now_add=True)
    date_start = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)

    def __str__(self):
        return "{}: {}".format(self.name, self.id)
