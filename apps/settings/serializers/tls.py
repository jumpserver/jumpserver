import ssl

from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class CertificateVerifyMode(models.TextChoices):
    default = 'default', _('Use default trust store (compatible)')
    system = 'system', _('Use system trust store')
    custom_ca = 'custom_ca', _('Use custom CA certificate')
    none = 'none', _('Ignore certificate verification (insecure)')


def validate_ca_certificate(content, field_name):
    if not content:
        return
    if 'PRIVATE KEY-----' in content:
        raise serializers.ValidationError({
            field_name: _('A CA certificate must not contain a private key')
        })
    try:
        ssl.create_default_context(cadata=content)
    except (ssl.SSLError, ValueError):
        raise serializers.ValidationError({
            field_name: _('Invalid PEM CA certificate')
        })
