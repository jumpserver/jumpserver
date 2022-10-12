from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db import fields
from ops.const import PasswordStrategy, StrategyChoice
from ops.utils import generate_random_password
from .base import BaseAutomation


class ChangePasswordAutomation(BaseAutomation):
    class PasswordStrategy(models.TextChoices):
        custom = 'specific', _('Specific')
        random_one = 'random_one', _('All assets use the same random password')
        random_all = 'random_all', _('All assets use different random password')

    password = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Secret'))
    recipients = models.ManyToManyField(
        'users.User', related_name='recipients_change_auth_strategy', blank=True,
        verbose_name=_("Recipient")
    )

    def save(self, *args, **kwargs):
        self.type = 'change_password'
        super().save(*args, **kwargs)

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
