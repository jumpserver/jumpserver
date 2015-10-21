import datetime

from django.db import models
from juser.models import User, UserGroup
from jasset.models import Asset, AssetGroup


class PermLog(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100, null=True, blank=True, default='')
    results = models.CharField(max_length=1000, null=True, blank=True, default='')
    is_success = models.BooleanField(default=False)
    is_finish = models.BooleanField(default=False)
