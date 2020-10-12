import jsonfield

from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger
from common.db import models
from orgs.mixins.models import OrgModelMixin
from ..backends import storage

__all__ = ['Account']

logger = get_logger(__file__)


class Account(models.JMSModel, OrgModelMixin):
    class SecretType(models.ChoiceSet):
        PASSWORD = 'password',  _('Password')
        SSH_KEY = 'ssh-key',  _('SSH Key')
        TOKEN = 'token', _('Token')
        CERT = 'cert', _('Cert')

    name = models.CharField(max_length=256, verbose_name=_('Name'))
    username = models.CharField(max_length=256, null=True, blank=True, verbose_name=_('Username'))
    address = models.CharField(max_length=1024, verbose_name=_('Address'))
    secret_type = models.CharField(max_length=32, choices=SecretType.choices, verbose_name=_('Secret type'))
    secret = models.TextField(verbose_name=_('Secret'))
    type = models.ForeignKey('accounts.AccountType', on_delete=models.PROTECT, verbose_name=_('Type'))
    extra_props = jsonfield.JSONField()
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    comment = models.TextField(default='', verbose_name=_('Comment'))

    namespace = models.ForeignKey('namespaces.Namespace', on_delete=models.PROTECT, verbose_name=_('Namespace'))

    class Meta:
        verbose_name = _('Account')
        permissions = (
            ('gain_secret', _('Can gain secret')),
            ('connect_account', _('Can connect account')),
        )
        # TODO
        # unique_together = [('username', 'address')]

    def save_extra_props(self, extra_props):
        self.extra_props = extra_props
        self.save()

    def create_secret(self, secret):
        storage.create_secret(self, {storage.key: secret})

    def update_secret(self, secret):
        storage.update_secret(self, {storage.key: secret})

    def get_secret(self):
        return storage.get_secret(self)

    def save(self, **kwargs):
        self.secret = ''
        super().save(**kwargs)

    def delete(self, using=None, keep_parents=False):
        storage.delete_secret(self)
        super().delete(using=None, keep_parents=False)
