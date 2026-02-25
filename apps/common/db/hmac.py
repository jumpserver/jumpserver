import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

__all__ = ['AbstractHmac']


class AbstractHmac(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    record_id = models.UUIDField(db_index=True, verbose_name=_("Record ID"))
    encrypt_fields = models.CharField(
        max_length=1024, default='', verbose_name=_("Encrypt fields")
    )
    encrypt_value = models.CharField(
        max_length=1024, default='', verbose_name=_("Encrypt value")
    )

    HMAC_FIELDS = []
    HMAC_FIELDS_STR = ''

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.HMAC_FIELDS:
            cls.HMAC_FIELDS_STR = ','.join(cls.HMAC_FIELDS)

    class Meta:
        abstract = True
