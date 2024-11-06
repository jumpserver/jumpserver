from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from ops.const import FieldType


class Variable(JMSBaseModel):
    name = models.CharField(max_length=1024, verbose_name=_('Name'), null=True)
    var_name = models.CharField(
        max_length=1024, null=True, verbose_name=_('Variable name'),
        help_text=_("The variable name used in the script has a fixed prefix 'jms_' followed by the input variable "
                    "name. For example, if the variable name is 'name,' the final generated environment variable will "
                    "be 'jms_name'.")
    )
    default_value = models.CharField(max_length=2048, verbose_name=_('Default Value'), null=True)
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=64, default=FieldType.text, verbose_name=_('Variable type'))
    tips = models.CharField(max_length=1024, default='', verbose_name=_('Tips'), null=True, blank=True)
    required = models.BooleanField(default=False, verbose_name=_('Required'))
    extra_args = models.JSONField(default=dict, verbose_name=_('ExtraVars'))
    playbook = models.ForeignKey(
        'ops.Playbook', verbose_name=_("Playbook"), null=True, on_delete=models.CASCADE, related_name='variable'
    )
    adhoc = models.ForeignKey(
        'ops.AdHoc', verbose_name=_("Adhoc"), null=True, on_delete=models.CASCADE, related_name='variable'
    )
    job = models.ForeignKey('ops.Job', verbose_name=_("Job"), null=True, on_delete=models.CASCADE,
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
            'type': self.type,
            'write_only': False,
            'default': self.default_value,
            'extra_args': self.extra_args,
        }

    class Meta:
        verbose_name = _("Variable")
        ordering = ['date_created']
