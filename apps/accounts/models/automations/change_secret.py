from django.db import models
from django.utils.translation import ugettext_lazy as _

from accounts.const import (
    AutomationTypes, SecretType, SecretStrategy, SSHKeyStrategy
)
from accounts.models import Account
from common.db import fields
from common.db.models import JMSBaseModel
from .base import AccountBaseAutomation

__all__ = ['ChangeSecretAutomation', 'ChangeSecretRecord', 'ChangeSecretMixin']


class ChangeSecretMixin(models.Model):
    secret_type = models.CharField(
        choices=SecretType.choices, max_length=16,
        default=SecretType.PASSWORD, verbose_name=_('Secret type')
    )
    secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Secret'))
    secret_strategy = models.CharField(
        choices=SecretStrategy.choices, max_length=16,
        default=SecretStrategy.custom, verbose_name=_('Secret strategy')
    )
    password_rules = models.JSONField(default=dict, verbose_name=_('Password rules'))
    ssh_key_change_strategy = models.CharField(
        choices=SSHKeyStrategy.choices, max_length=16,
        default=SSHKeyStrategy.add, verbose_name=_('SSH key change strategy')
    )

    get_all_assets: callable  # get all assets

    class Meta:
        abstract = True

    def create_nonlocal_accounts(self, usernames, asset):
        pass

    def get_account_ids(self):
        usernames = self.accounts
        accounts = Account.objects.none()
        for asset in self.get_all_assets():
            self.create_nonlocal_accounts(usernames, asset)
            accounts = accounts | asset.accounts.all()
        account_ids = accounts.filter(
            username__in=usernames, secret_type=self.secret_type
        ).values_list('id', flat=True)
        return [str(_id) for _id in account_ids]

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'secret': self.secret,
            'secret_type': self.secret_type,
            'accounts': self.get_account_ids(),
            'password_rules': self.password_rules,
            'secret_strategy': self.secret_strategy,
            'ssh_key_change_strategy': self.ssh_key_change_strategy,
        })
        return attr_json


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
    new_secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Secret'))
    date_started = models.DateTimeField(blank=True, null=True, verbose_name=_('Date started'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('Date finished'))
    status = models.CharField(max_length=16, default='pending')
    error = models.TextField(blank=True, null=True, verbose_name=_('Error'))

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _("Change secret record")

    def __str__(self):
        return self.account.__str__()

    @property
    def timedelta(self):
        if self.date_started and self.date_finished:
            return self.date_finished - self.date_started
        return None
