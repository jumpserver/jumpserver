from django.db import models
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import JMSOrgBaseModel

__all__ = ['VirtualAccount']


class VirtualAccount(JMSOrgBaseModel):
    username = models.CharField(max_length=128, verbose_name=_('Username'), )
    secret_from_login = models.BooleanField(default=None, null=True, verbose_name=_("Secret from login"), )

    class Meta:
        unique_together = [('username', 'org_id')]
