from django.db import models
from django.utils.translation import gettext_lazy as _


class Protocol(models.Model):
    name = models.CharField(max_length=32, verbose_name=_("Name"))
    port = models.IntegerField(verbose_name=_("Port"))
