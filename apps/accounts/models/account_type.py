from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db.models import ChoiceSet
from common.mixins.models import CommonModelMixin


class PropDef(models.Model):
    class TYPE(ChoiceSet):
        TEXT = 'text', _('Text')
        NUMBER = 'number', _('Number')
        LIST = 'list', _('List')
        DATETIME = 'datetime', _('Datetime')

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(choices=TYPE, default=TYPE.TEXT, verbose_name=_('Type'))
    default = models.JSONField(default='', verbose_name=_('Default'))
    choices = models.JSONField(default=list, verbose_name=_('Choices'))
    required = models.BooleanField(default=False, verbose_name=_('Required'))

    def __str__(self):
        return self.name

    def to_serializer_field(self):
        pass


class AccountType(CommonModelMixin):
    class Category(ChoiceSet):
        OS = 'os', _('Operation System')
        DATABASE = 'db', _('Database')
        NETWORK_DEVICE = 'network_device', _('Network Device')
        APP = 'app', _('Application')
        CLOUD = 'cloud', _('Cloud')
        Other = 'other', _('Other')

    name = models.CharField(max_length=2048, verbose_name=_('Name'))
    category = models.CharField(choices=Category, verbose_name=_('Category'))
    base_type = models.ForeignKey('AccountType', related_name='sub_types', on_delete=models.PROTECT, verbose_name=_('Base Type'))
    protocol = models.CharField(max_length=32, verbose_name=_('Protocol'))
    props_define = models.ManyToManyField('PropDef', verbose_name=_('Properties Definition'))
