import json
import jsonfield

from django.db import models
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin

__all__ = ['PropField', 'AccountType']


class Type(object):
    STR = 'string'
    INT = 'integer'
    LIST = 'list'
    IP = 'ip'
    DATETIME = 'datetime'

    CHOICES = (
        (STR, _('String')),
        (INT, _('Integer')),
        (LIST, _('List')),
        (IP, _('Ip')),
        (DATETIME, _('Datetime')),
    )

    TYPE_TO_SERIALIZER_MAP = {
        STR: serializers.CharField,
        INT: serializers.IntegerField,
        LIST: serializers.ListField,
        IP: serializers.IPAddressField,
        DATETIME: serializers.DateTimeField,
    }


class Category(object):
    OS = 'os'
    DATABASE = 'db'
    NETWORK_DEVICE = 'network_device'
    APP = 'app'
    CLOUD = 'cloud'
    Other = 'other'

    CHOICES = (
        (OS, _('Operation System')),
        (DATABASE, _('Database')),
        (NETWORK_DEVICE, _('Network Device')),
        (APP, _('Application')),
        (CLOUD, _('Cloud')),
        (Other, _('Other')),
    )


class PropField(models.Model):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(max_length=32, choices=Type.CHOICES, default=Type.STR, verbose_name=_('Type'))
    default = jsonfield.JSONField()
    choices = jsonfield.JSONField()
    required = models.BooleanField(default=False, verbose_name=_('Required'))

    def __str__(self):
        return self.name

    def to_serializer_field(self):
        field = Type.TYPE_TO_SERIALIZER_MAP.get(self.type)
        kwargs = {'required': False}
        if self.required:
            kwargs['required'] = True
            return field(**kwargs)
        if self.default:
            kwargs['default'] = json.loads(json.dumps(self.default))
        return field(**kwargs)


class AccountType(CommonModelMixin):
    name = models.CharField(max_length=256, verbose_name=_('Name'))
    category = models.CharField(max_length=64, choices=Category.CHOICES, verbose_name=_('Category'))
    base_type = models.ForeignKey('AccountType', null=True, related_name='sub_types',
                                  on_delete=models.PROTECT, verbose_name=_('Base Type'))
    protocol = models.CharField(max_length=32, verbose_name=_('Protocol'))
    prop_fields = models.ManyToManyField('PropField', verbose_name=_('Properties Definition'))

    def __str__(self):
        return self.name

    def generate_serializer(self):
        fields = self.prop_fields.all()
        serializer_fields = {f.name: f.to_serializer_field() for f in fields}
        return type('AccountTypeSerializer', (serializers.Serializer,), serializer_fields)
