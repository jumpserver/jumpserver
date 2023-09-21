from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel


class Passkey(JMSBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    is_active = models.BooleanField(default=True, verbose_name=_("Enabled"))
    platform = models.CharField(max_length=255, default='', verbose_name=_("Platform"))
    added_on = models.DateTimeField(auto_now_add=True, verbose_name=_("Added on"))
    date_last_used = models.DateTimeField(null=True, default=None, verbose_name=_("Date last used"))
    credential_id = models.CharField(max_length=255, unique=True, null=False, verbose_name=_("Credential ID"))
    token = models.CharField(max_length=255, null=False, verbose_name=_("Token"))

    def __str__(self):
        return self.name
