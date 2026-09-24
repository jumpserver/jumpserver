import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class UKeyCertificateBinding(models.Model):
    # Separate from User.ukey_sn: switching providers must preserve builtin data.
    user = models.OneToOneField('users.User', primary_key=True, on_delete=models.CASCADE,
                                related_name='ukey_certificate_binding')
    provider = models.CharField(max_length=16, default='xjca', editable=False)
    # Hash the verified certificate's issuer DN + AKI for issuer/serial uniqueness.
    issuer_fingerprint = models.CharField(max_length=64)
    serial_number = models.CharField(max_length=64)
    certificate_fingerprint = models.CharField(max_length=64, unique=True)
    hardware_serial = models.CharField(max_length=128)
    version = models.UUIDField(default=uuid.uuid4, editable=False)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('UKey certificate binding')
        constraints = [models.UniqueConstraint(
            fields=('provider', 'issuer_fingerprint', 'serial_number'),
            name='users_ukey_unique_certificate',
        )]
