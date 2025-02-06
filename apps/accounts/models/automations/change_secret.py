from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from accounts.const import (
    AutomationTypes, ChangeSecretRecordStatusChoice
)
from common.db import fields
from common.db.models import JMSBaseModel
from .base import AccountBaseAutomation, ChangeSecretMixin

__all__ = ['ChangeSecretAutomation', 'ChangeSecretRecord', 'BaseSecretRecord']


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
            'recipients': [str(r.id) for r in self.recipients.all()]
        })
        return attr_json


class BaseSecretRecord(JMSBaseModel):
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.SET_NULL,
        null=True, related_name='%(class)ss'
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL,
        null=True, related_name='asset_%(class)ss'
    )
    execution = models.ForeignKey(
        'accounts.AutomationExecution', on_delete=models.SET_NULL,
        null=True, related_name='execution_%(class)ss',
    )
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('Date finished'), db_index=True)
    status = models.CharField(
        max_length=16, verbose_name=_('Status'), default=ChangeSecretRecordStatusChoice.pending.value
    )
    error = models.TextField(blank=True, null=True, verbose_name=_('Error'))

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.account.username}@{self.asset}'

    @classmethod
    def get_valid_records(cls):
        return cls.objects.exclude(
            Q(execution__isnull=True) | Q(asset__isnull=True) | Q(account__isnull=True)
        )


class ChangeSecretRecord(BaseSecretRecord):
    old_secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Old secret'))
    new_secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('New secret'))
    ignore_fail = models.BooleanField(default=False, verbose_name=_('Ignore fail'))

    class Meta:
        verbose_name = _("Change secret record")
