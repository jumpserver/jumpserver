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
    var_name = models.CharField(max_length=128, verbose_name=_('VarName'), null=True)
    default_value = models.CharField(max_length=128, verbose_name=_('DefaultValue'), null=True)
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=64, default=FieldType.text, verbose_name=_('参数类型'))
    tips = models.CharField(max_length=1024, default='', verbose_name=_('Tips'), null=True, blank=True)
    required = models.BooleanField(default=False, verbose_name=_('Required'))
    playbook = models.ForeignKey(
        'ops.Playbook', verbose_name=_("Playbook"), null=True, on_delete=models.SET_NULL, related_name='variable'
    )
    adhoc = models.ForeignKey(
        'ops.AdHoc', verbose_name=_("Adhoc"), null=True, on_delete=models.SET_NULL, related_name='variable'
    )
    job = models.ForeignKey('ops.Job', verbose_name=_("Job"), null=True, on_delete=models.SET_NULL,
                            related_name='variable')

    def __str__(self):
        return self.name

    @property
    def form_data(self):
        return {
            'var_name': self.var_name,
            'label': self.name,
            'help_text': self.tips,
            'read_only': False,
            'required': self.required,
            'type': 'string',
            'write_only': True,
            'default': self.default_value
        }

    class Meta:
        verbose_name = _("Variable")
        ordering = ['date_created']
