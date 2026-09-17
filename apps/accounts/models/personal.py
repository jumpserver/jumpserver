from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import Protocol
from assets.models.base import AbsConnectivity
from orgs.mixins.models import JMSOrgBaseModel

from ..const import SecretType
from .mixins import VaultModelMixin

__all__ = ['PersonalAssetCredential']


class PersonalAssetCredential(VaultModelMixin, AbsConnectivity, JMSOrgBaseModel):
    owner = models.ForeignKey(
        'users.User', related_name='personal_asset_credentials',
        on_delete=models.CASCADE, verbose_name=_('Owner'),
    )
    asset = models.ForeignKey(
        'assets.Asset', related_name='personal_credentials',
        on_delete=models.CASCADE, verbose_name=_('Asset'),
    )
    username = models.CharField(max_length=128, verbose_name=_('Username'))
    secret_type = models.CharField(
        max_length=16, choices=SecretType.choices,
        default=SecretType.PASSWORD, verbose_name=_('Secret type'),
    )
    protocol = models.CharField(
        max_length=16, choices=Protocol.choices,
        default=Protocol.ssh, verbose_name=_('Protocol'),
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    version = models.PositiveIntegerField(default=1, verbose_name=_('Version'))

    class Meta:
        verbose_name = _('Personal asset credential')
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=['org_id', 'owner', 'asset', 'username', 'secret_type', 'protocol'],
                name='acct_personal_cred_uniq',
            ),
        ]
        indexes = [
            models.Index(
                fields=['owner', 'asset', 'is_active'],
                name='acct_pcred_owner_asset_idx',
            ),
            models.Index(
                fields=['org_id', 'owner'],
                name='acct_pcred_org_owner_idx',
            ),
        ]

    @property
    def has_secret(self):
        return bool(self.secret)

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset)
