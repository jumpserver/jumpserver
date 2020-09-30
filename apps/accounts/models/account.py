import jsonfield

from accounts.backend import get_account_storage
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger
from common.db import models
from orgs.mixins.models import OrgModelMixin

__all__ = ['Account']

logger = get_logger(__file__)


class SecretType(object):
    PASSWORD = 'password'
    SSH_KEY = 'ssh-key'
    TOKEN = 'token'
    CERT = 'cert'

    CHOICES = (
        (PASSWORD, _('Password')),
        (SSH_KEY, _('SSH Key')),
        (TOKEN, _('Token')),
        (CERT, _('Cert')),
    )


class Account(models.JMSModel, OrgModelMixin):
    name = models.CharField(max_length=256, verbose_name=_('Name'))
    username = models.CharField(max_length=256, null=True, blank=True, verbose_name=_('Username'))
    address = models.CharField(max_length=1024, verbose_name=_('Address'))
    secret_type = models.CharField(max_length=32, choices=SecretType.CHOICES, verbose_name=_('Secret type'))
    secret = models.TextField(verbose_name=_('Secret'))
    type = models.ForeignKey('accounts.AccountType', on_delete=models.PROTECT, verbose_name=_('Type'))
    extra_props = jsonfield.JSONField()
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    comment = models.TextField(default='', verbose_name=_('Comment'))

    namespace = models.ForeignKey('namespaces.Namespace', on_delete=models.PROTECT, verbose_name=_('Namespace'))

    class Meta:
        pass
        # TODO
        # unique_together = [('username', 'address')]

    def save(self, **kwargs):
        self.secret = ''
        super(Account, self).save(**kwargs)

    def delete(self, using=None, keep_parents=False):
        storage = get_account_storage()
        storage.delete_secret(self)
        super(Account, self).delete(using=None, keep_parents=False)
