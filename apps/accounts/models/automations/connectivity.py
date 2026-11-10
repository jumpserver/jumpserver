import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import OrgModelMixin

__all__ = ['ConnectivityRecord']


class ConnectivityRecord(OrgModelMixin):
    """An execution's target identity and outcome, independent of live accounts."""

    class Type(models.TextChoices):
        asset = 'ping', _('Asset')
        account = 'verify_account', _('Account')

    class Status(models.TextChoices):
        success = 'success', _('Success')
        failed = 'failed', _('Failed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    execution = models.ForeignKey(
        'assets.AutomationExecution', related_name='connectivity_records',
        on_delete=models.CASCADE, verbose_name=_('Execution'),
    )
    type = models.CharField(max_length=32, choices=Type.choices, verbose_name=_('Type'))
    target = models.TextField()
    # Snapshot IDs are intentionally not foreign keys: deleting an asset or
    # account must not erase the identity in an execution's history.
    asset_id = models.UUIDField(null=True, blank=True)
    account_id = models.UUIDField(null=True, blank=True)
    asset = models.CharField(max_length=256, blank=True, default='', verbose_name=_('Asset'))
    asset_address = models.CharField(max_length=256, blank=True, default='', verbose_name=_('Address'))
    account = models.CharField(max_length=256, blank=True, default='', verbose_name=_('Account'))
    username = models.CharField(max_length=512, blank=True, default='', verbose_name=_('Username'))
    privileged = models.BooleanField(null=True, verbose_name=_('Privileged'))
    status = models.CharField(max_length=16, choices=Status.choices, verbose_name=_('Result'))
    error = models.TextField(blank=True, default='', verbose_name=_('Error'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'))
    date_finished = models.DateTimeField(null=True, verbose_name=_('Date finished'))

    class Meta:
        ordering = ('-date_start', '-id')
        default_permissions = ()  # Uses the existing execution permissions.
        verbose_name = _('Execution')
        indexes = [
            models.Index(fields=['org_id', 'type', '-date_start'], name='accounts_cr_org_type_date_idx'),
        ]
