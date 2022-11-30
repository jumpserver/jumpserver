from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class Database(Asset):
    db_name = models.CharField(max_length=1024, verbose_name=_("Database"), blank=True)
    use_ssl = models.BooleanField(default=False, verbose_name=_("Use SSL"))
    ca_cert = models.TextField(verbose_name=_("CA cert"), blank=True)
    client_cert = models.TextField(verbose_name=_("Client cert"), blank=True)
    client_key = models.TextField(verbose_name=_("Client key"), blank=True)
    allow_invalid_cert = models.BooleanField(default=False, verbose_name=_('Allow invalid cert'))

    def __str__(self):
        return '{}({}://{}/{})'.format(self.name, self.type, self.address, self.db_name)

    @property
    def ip(self):
        return self.address

    @property
    def specific(self):
        return {
            'db_name': self.db_name,
            'use_ssl': self.use_ssl,
            'ca_cert': self.ca_cert,
            'client_cert': self.client_cert,
            'client_key': self.client_key,
            'allow_invalid_cert': self.allow_invalid_cert,
        }

    class Meta:
        verbose_name = _("Database")
