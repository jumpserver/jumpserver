from django.conf import settings
from django.db import models

from common.db.models import JMSBaseModel


class UserPasskey(JMSBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    platform = models.CharField(max_length=255, default='')
    added_on = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, default=None)
    credential_id = models.CharField(max_length=255, unique=True)
    token = models.CharField(max_length=255, null=False)
