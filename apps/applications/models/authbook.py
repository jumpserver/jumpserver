from django.db import models

from common import fields
from orgs.mixins.models import OrgModelMixin
from common.mixins.models import CommonModelMixin
from django.utils.translation import ugettext_lazy as _


class AuthBook(OrgModelMixin, CommonModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    username = models.CharField(max_length=128, blank=True, verbose_name=_('Username'), db_index=True)
    database = models.ForeignKey('applications.Application', on_delete=models.CASCADE, null=True,
                                 verbose_name=_('Database'))
    password = fields.EncryptCharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))

    class Meta:
        verbose_name = _('AuthBook')
        unique_together = [('username', 'database')]
