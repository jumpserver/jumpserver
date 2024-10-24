import os.path
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from ops.const import FieldType

dangerous_keywords = (
    'hosts:localhost',
    'hosts:127.0.0.1',
    'hosts:::1',
    'delegate_to:localhost',
    'delegate_to:127.0.0.1',
    'delegate_to:::1',
    'local_action',
    'connection:local',
    'ansible_connection'
)


class Variable(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), null=True)
    username = models.CharField(max_length=128, verbose_name=_('Username'), null=True)
    default_value = models.CharField(max_length=128, verbose_name=_('DefaultValue'), null=True)
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=64, default=FieldType.text, verbose_name=_('参数类型'))
    tips = models.CharField(max_length=1024, default='', verbose_name=_('Tips'), null=True, blank=True)
    require = models.BooleanField(default=False, verbose_name=_('Require'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Variable")
        ordering = ['date_created']
