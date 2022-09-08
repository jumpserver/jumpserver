from django.db import models
from django.utils.translation import ugettext_lazy as _

from ops.const import SSHKeyStrategy, PasswordStrategy, StrategyChoice
from ops.utils import generate_random_password
from common.db.fields import (
    EncryptCharField, EncryptTextField, JsonDictCharField
)
from .common import AutomationStrategy


class ChangeAuthStrategy(AutomationStrategy):
    is_password = models.BooleanField(default=True)
    password_strategy = models.CharField(
        max_length=128, blank=True, null=True, choices=PasswordStrategy.choices,
        verbose_name=_('Password strategy')
    )
    password_rules = JsonDictCharField(
        max_length=2048, blank=True, null=True, verbose_name=_('Password rules')
    )
    password = EncryptCharField(
        max_length=256, blank=True, null=True, verbose_name=_('Password')
    )

    is_ssh_key = models.BooleanField(default=False)
    ssh_key_strategy = models.CharField(
        max_length=128, blank=True, null=True, choices=SSHKeyStrategy.choices,
        verbose_name=_('SSH Key strategy')
    )
    private_key = EncryptTextField(
        max_length=4096, blank=True, null=True, verbose_name=_('SSH private key')
    )
    public_key = EncryptTextField(
        max_length=4096, blank=True, null=True, verbose_name=_('SSH public key')
    )
    recipients = models.ManyToManyField(
        'users.User', related_name='recipients_change_auth_strategy', blank=True,
        verbose_name=_("Recipient")
    )

    class Meta:
        verbose_name = _("Change auth strategy")

    def gen_execute_password(self):
        if self.password_strategy == PasswordStrategy.custom:
            return self.password
        elif self.password_strategy == PasswordStrategy.random_one:
            return generate_random_password(**self.password_rules)
        else:
            return None

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'type': StrategyChoice.change_auth,

            'password': self.gen_execute_password(),
            'is_password': self.is_password,
            'password_rules': self.password_rules,
            'password_strategy': self.password_strategy,

            'is_ssh_key': self.is_ssh_key,
            'public_key': self.public_key,
            'private_key': self.private_key,
            'ssh_key_strategy': self.ssh_key_strategy,
            'recipients': {
                str(recipient.id): (str(recipient), bool(recipient.secret_key))
                for recipient in self.recipients.all()
            }
        })
        return attr_json
