from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.const import (
    AutomationTypes
)
from common.db import fields
from common.db.models import JMSBaseModel
from .base import AccountBaseAutomation, ChangeSecretMixin

__all__ = ['ChangeSecretAutomation', 'ChangeSecretRecord', ]


class ChangeSecretAutomation(ChangeSecretMixin, AccountBaseAutomation):
    recipients = models.ManyToManyField('users.User', verbose_name=_("Recipient"), blank=True)

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.change_secret
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Change secret automation")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'recipients': {
                str(recipient.id): (str(recipient), bool(recipient.secret_key))
                for recipient in self.recipients.all()
            }
        })
        return attr_json


class ChangeSecretRecord(JMSBaseModel):
    execution = models.ForeignKey('accounts.AutomationExecution', on_delete=models.CASCADE)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, null=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, null=True)
    old_secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Old secret'))
    new_secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('New secret'))
    date_started = models.DateTimeField(blank=True, null=True, verbose_name=_('Date started'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('Date finished'))
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))
    error = models.TextField(blank=True, null=True, verbose_name=_('Error'))

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _("Change secret record")

    def __str__(self):
        return self.account.__str__()
