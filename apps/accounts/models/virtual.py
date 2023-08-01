from django.db import models
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import JMSOrgBaseModel
from ..const import AliasAccount

__all__ = ['VirtualAccountSetting']


class VirtualAccountSetting(JMSOrgBaseModel):
    account = models.CharField(max_length=128, choices=AliasAccount.virtual_choices(), verbose_name=_('Account'), )
    secret_from_login = models.BooleanField(default=False, verbose_name=_("Secret from login"))

    class Meta:
        unique_together = [('username', 'org_id')]
