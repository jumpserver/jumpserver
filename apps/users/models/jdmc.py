from django.conf import settings
from django.db import models


class JDMCNodeBinding(models.Model):
    name = models.CharField(max_length=128, primary_key=True)
    # Retain the binding after account deletion so delayed enrollment cannot revive a revoked node.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
