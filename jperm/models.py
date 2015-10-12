import datetime

from django.db import models
from juser.models import User, UserGroup
from jasset.models import Asset, AssetGroup


class PermLog(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    result = models.CharField(max_length=1000, null=True, blank=True, default='')
    is_finished = models.BooleanField(default=False)
