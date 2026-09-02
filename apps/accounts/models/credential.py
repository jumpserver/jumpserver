from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.db import fields
from common.utils import random_string
from orgs.mixins.models import JMSOrgBaseModel

__all__ = [
    'CredentialPolicy', 'CredentialApplicationBinding',
    'CredentialClientInstance', 'CredentialClientStatus',
]


class CredentialPolicy(JMSOrgBaseModel):
    class Status(models.TextChoices):
        idle = 'idle', _('Idle')
        waiting_backup = 'waiting_backup', _('Waiting for backup account')
        ready_for_change = 'ready_for_change', _('Ready for secret change')
        waiting_primary = 'waiting_primary', _('Waiting for primary account')

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    key = models.CharField(max_length=64, unique=True, default='', verbose_name=_('Key'))
    primary_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='primary_credential_policies', verbose_name=_('Primary account')
    )
    backup_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='backup_credential_policies', verbose_name=_('Backup account')
    )
    published_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='published_credential_policies', verbose_name=_('Published account')
    )
    revision = models.PositiveIntegerField(default=1, verbose_name=_('Revision'))
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.idle,
        verbose_name=_('Status')
    )
    primary_version_at_start = models.IntegerField(
        null=True, blank=True, verbose_name=_('Primary version at start')
    )
    rotation_cancelled = models.BooleanField(default=False, verbose_name=_('Rotation cancelled'))
    date_rotation_started = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date rotation started')
    )
    date_last_rotated = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date last rotated')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        unique_together = [('org_id', 'name'), ('org_id', 'primary_account')]
        ordering = ['name']
        verbose_name = _('Credential policy')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = f'cred-{random_string(16).lower()}'
        super().save(*args, **kwargs)

    @property
    def asset(self):
        return self.primary_account.asset

    def participant_statuses(self):
        return CredentialClientStatus.objects.filter(
            binding__policy=self,
            is_rotation_participant=True,
            client__is_active=True,
        ).select_related(
            'binding__application', 'client', 'applied_account'
        )

    def get_blockers(self, now=None):
        now = now or timezone.now()
        offline_before = now - timedelta(minutes=2)
        blockers = []
        for state in self.participant_statuses():
            reason = ''
            if not state.date_last_seen or state.date_last_seen < offline_before:
                reason = 'offline'
            elif (
                state.applied_revision != state.required_revision
                or state.applied_account_id != self.published_account_id
            ):
                reason = 'not_applied'
            if not reason:
                continue
            blockers.append({
                'application': {
                    'id': str(state.binding.application_id),
                    'name': state.binding.application.name,
                },
                'client': {
                    'id': str(state.client_id),
                    'instance_id': state.client.instance_id,
                    'type': state.client.type,
                },
                'reason': reason,
                'applied_revision': state.applied_revision,
                'required_revision': state.required_revision,
                'applied_account': str(state.applied_account_id or ''),
                'date_last_seen': state.date_last_seen,
            })
        return blockers


class CredentialApplicationBinding(JMSOrgBaseModel):
    policy = models.ForeignKey(
        CredentialPolicy, on_delete=models.CASCADE,
        related_name='application_bindings', verbose_name=_('Credential policy')
    )
    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='credential_bindings', verbose_name=_('Integration application')
    )

    class Meta:
        unique_together = [('policy', 'application')]
        ordering = ['application__name']
        verbose_name = _('Credential application binding')

    def __str__(self):
        return f'{self.application} - {self.policy}'


class CredentialClientInstance(JMSOrgBaseModel):
    class Type(models.TextChoices):
        sdk = 'sdk', _('SDK')
        agent = 'agent', _('Agent')

    is_anonymous = False

    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='credential_clients', verbose_name=_('Integration application')
    )
    type = models.CharField(max_length=16, choices=Type.choices, verbose_name=_('Type'))
    instance_id = models.CharField(max_length=128, verbose_name=_('Instance ID'))
    secret = fields.EncryptTextField(default='', blank=True, verbose_name=_('Secret'))
    date_last_seen = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last seen'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        unique_together = [('application', 'instance_id')]
        ordering = ['application__name', 'instance_id']
        verbose_name = _('Credential client instance')

    def __str__(self):
        return f'{self.application.name}:{self.instance_id}'

    @property
    def is_authenticated(self):
        return self.is_active

    @property
    def is_valid(self):
        return self.is_active and self.application.is_active

    @property
    def online(self):
        return bool(
            self.is_active
            and self.date_last_seen
            and self.date_last_seen >= timezone.now() - timedelta(minutes=2)
        )

    @staticmethod
    def has_perms(perms):
        return not perms


class CredentialClientStatus(JMSOrgBaseModel):
    binding = models.ForeignKey(
        CredentialApplicationBinding, on_delete=models.CASCADE,
        related_name='client_statuses', verbose_name=_('Application binding')
    )
    client = models.ForeignKey(
        CredentialClientInstance, on_delete=models.CASCADE,
        related_name='credential_statuses', verbose_name=_('Client instance')
    )
    fetched_revision = models.PositiveIntegerField(default=0, verbose_name=_('Fetched revision'))
    applied_revision = models.PositiveIntegerField(default=0, verbose_name=_('Applied revision'))
    applied_account = models.ForeignKey(
        'accounts.Account', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('Applied account')
    )
    required_revision = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_('Required revision')
    )
    is_rotation_participant = models.BooleanField(
        default=False, verbose_name=_('Rotation participant')
    )
    date_last_seen = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last seen'))
    date_fetched = models.DateTimeField(null=True, blank=True, verbose_name=_('Date fetched'))
    date_applied = models.DateTimeField(null=True, blank=True, verbose_name=_('Date applied'))

    class Meta:
        unique_together = [('binding', 'client')]
        ordering = ['binding__application__name', 'client__instance_id']
        verbose_name = _('Credential client status')

    def __str__(self):
        return f'{self.client} - {self.binding.policy.key}'
