from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import EncryptTextField
from .common import Asset


class Database(Asset):
    db_name = models.CharField(max_length=1024, verbose_name=_("Database"), blank=True)
    use_ssl = models.BooleanField(default=False, verbose_name=_("Use SSL"))
    ca_cert = EncryptTextField(verbose_name=_("CA cert"), blank=True)
    client_cert = EncryptTextField(verbose_name=_("Client cert"), blank=True)
    client_key = EncryptTextField(verbose_name=_("Client key"), blank=True)
    allow_invalid_cert = models.BooleanField(default=False, verbose_name=_('Allow invalid cert'))

    def __str__(self):
        return '{}({}://{}/{})'.format(self.name, self.type, self.address, self.db_name)

    @property
    def ip(self):
        return self.address

    class Meta:
        verbose_name = _("Database")
