from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db.models import ChoiceSet
from common.mixins import CommonModelMixin
from orgs.mixins.models import OrgModelMixin


class Account(CommonModelMixin, OrgModelMixin):
    class SecretTypes(ChoiceSet):
        PASSWORD = 'password', _('Password')
        SSH_KEY = 'ssh-key', _('SSH Key')
        TOKEN = 'token', _('Token')
        CERT = 'cert', _('Cert')

    name = models.CharField(max_length=2048, verbose_name=_('Name'))
    username = models.CharField(max_length=2048, verbose_name=_('Username'))
    address = models.CharField(max_length=4096, verbose_name=_('Address'))
    secret_type = models.CharField(choices=SecretTypes, default=SecretTypes.PASSWORD)
    secret = models.TextField(verbose_name=_('Secret'))
    comment = models.TextField(verbose_name=_('Comment'))

    namespace = models.ForeignKey('namespaces.Namespace', on_delete=models.PROTECT, verbose_name=_('Namespace'))
