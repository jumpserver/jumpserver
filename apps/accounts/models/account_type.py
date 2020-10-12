import json
import jsonfield

from django.db import models
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.db.models import JMSModel, ChoiceSet

__all__ = ['PropField', 'AccountType']


class PropField(models.Model):
    class PropType(ChoiceSet):
        STR = 'string', _('String')
        INT = 'integer', _('Integer')
        LIST = 'list', _('List')
        IP = 'ip', 'IP'
        DATETIME = _('Datetime')

        TYPE_TO_SERIALIZER_MAP = {
            STR: serializers.CharField,
            INT: serializers.IntegerField,
            LIST: serializers.ListField,
            IP: serializers.IPAddressField,
            DATETIME: serializers.DateTimeField,
        }

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(max_length=32, choices=PropType.choices, default=PropType.STR, verbose_name=_('Type'))
    default = jsonfield.JSONField()
    choices = jsonfield.JSONField()
    required = models.BooleanField(default=False, verbose_name=_('Required'))

    class Meta:
        verbose_name = _('Prop Field')

    def __str__(self):
        return self.name

    def to_serializer_field(self):
        field = self.PropType.TYPE_TO_SERIALIZER_MAP.get(self.type)
        kwargs = {'required': False}
        if self.required:
            kwargs['required'] = True
            return field(**kwargs)
        if self.default:
            kwargs['default'] = json.loads(json.dumps(self.default))
        return field(**kwargs)


class AccountType(JMSModel):
    class Category(ChoiceSet):
        OS = 'os',  _('Operation System')
        DATABASE = _('Database')
        NETWORK_DEVICE = 'network_device', _('Network Device')
        APP = 'app', _('Application')
        CLOUD = 'cloud', _('Cloud')
        Other = 'other',  _('Other')

    name = models.CharField(max_length=255, unique=True, verbose_name=_('Name'))
    category = models.CharField(max_length=64, choices=Category.choices, default=Category.OS, verbose_name=_('Category'))
    base_type = models.ForeignKey('AccountType', null=True, related_name='sub_types',
                                  on_delete=models.PROTECT, verbose_name=_('Base Type'))
    protocol = models.CharField(max_length=32, verbose_name=_('Protocol'))
    prop_fields = models.ManyToManyField('PropField', verbose_name=_('Properties Definition'))

    class Meta:
        verbose_name = _('Account Type')

    def __str__(self):
        return self.name

    def to_serializer_cls(self):
        fields = self.prop_fields.all()
        serializer_fields = {f.name: f.to_serializer_field() for f in fields}
        name = 'AccountTypeSerializer{}'.format(self.name.title())
        return type(name, (serializers.Serializer,), serializer_fields)
