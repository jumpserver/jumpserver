from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.db import fields
from common.utils import random_string
from orgs.mixins.models import JMSOrgBaseModel
from .application import IntegrationApplication

__all__ = [
    'ApplicationCredential', 'CredentialApplicationBinding',
    'CredentialClientInstance', 'CredentialClientStatus',
    'ClientAccessConfiguration', 'CredentialRotationRecord',
]


class ApplicationCredential(JMSOrgBaseModel):
    class Mode(models.TextChoices):
        subscription = 'subscription', _('Credential update subscription')
        alternating_rotation = 'alternating_rotation', _('Alternating dual-account rotation')

    class Status(models.TextChoices):
        idle = 'idle', _('Idle')
        waiting_switch = 'waiting_switch', _('Waiting for account switch')
        ready_for_change = 'ready_for_change', _('Ready for secret change')
        changing_secret = 'changing_secret', _('Changing secret')
        change_failed = 'change_failed', _('Secret change failed')
        recovery_required = 'recovery_required', _('Recovery required')
        waiting_revert = 'waiting_revert', _('Waiting for account revert')

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    key = models.CharField(max_length=64, unique=True, default='', verbose_name=_('Key'))
    mode = models.CharField(
        max_length=32, choices=Mode.choices, default=Mode.subscription,
        verbose_name=_('Mode')
    )
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='application_credentials', verbose_name=_('Account')
    )
    alternate_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='alternate_application_credentials', verbose_name=_('Alternate account')
    )
    active_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='active_application_credentials', verbose_name=_('Active account')
    )
    revision = models.PositiveIntegerField(default=1, verbose_name=_('Revision'))
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.idle,
        verbose_name=_('Status')
    )
    rotation_cancelled = models.BooleanField(default=False, verbose_name=_('Rotation cancelled'))
    date_rotation_started = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date rotation started')
    )
    date_last_rotated = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date last rotated')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    change_execution = models.ForeignKey(
        'accounts.AutomationExecution', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name=_('Change secret execution')
    )
    applications = models.ManyToManyField(
        'accounts.IntegrationApplication', through='accounts.CredentialApplicationBinding',
        related_name='application_credentials', verbose_name=_('Integration applications')
    )

    class Meta:
        unique_together = [('org_id', 'name')]
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
        return self.account.asset if self.account_id else None

    def account_key(self, account_id):
        return f'{self.key}:{account_id}'

    @property
    def target_account(self):
        if self.mode != self.Mode.alternating_rotation:
            return None
        if self.active_account_id == self.account_id:
            return self.alternate_account
        return self.account

    @property
    def current_revision(self):
        return self.revision

    def authorized_applications(self):
        if self.mode == self.Mode.subscription:
            return self.applications.all()
        applications = IntegrationApplication.objects.all()
        for account in (self.account, self.alternate_account):
            if account:
                applications = applications.filter(
                    IntegrationApplication.accounts.get_filter_q(account)
                )
        return applications

    def rotation_statuses(self):
        return CredentialClientStatus.objects.filter(
            binding__credential=self,
            binding__application__in=self.authorized_applications(),
            client__configuration__credentials=self,
            client__is_active=True,
            client__configuration__is_active=True,
            client__application__is_active=True,
        )

    def participant_statuses(self):
        return self.rotation_statuses().filter(
            is_rotation_participant=True,
        ).select_related(
            'binding__application', 'client', 'applied_account'
        )

    def get_blockers(self, now=None):
        from accounts.credential_rotation.participants import build
        return build(self, now=now)['blockers']


class CredentialApplicationBinding(JMSOrgBaseModel):
    credential = models.ForeignKey(
        ApplicationCredential, on_delete=models.CASCADE,
        related_name='application_bindings', verbose_name=_('Credential policy')
    )
    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='credential_bindings', verbose_name=_('Integration application')
    )

    class Meta:
        unique_together = [('credential', 'application')]
        ordering = ['application__name']
        verbose_name = _('Credential application binding')

    def __str__(self):
        return f'{self.application} - {self.credential}'


class CredentialClientInstance(JMSOrgBaseModel):
    class Type(models.TextChoices):
        sdk = 'sdk', _('SDK')
        agent = 'agent', _('Agent')

    is_anonymous = False

    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='credential_clients', verbose_name=_('Integration application')
    )
    configuration = models.ForeignKey(
        'accounts.ClientAccessConfiguration', on_delete=models.CASCADE,
        related_name='instances', verbose_name=_('Client access configuration')
    )
    type = models.CharField(max_length=16, choices=Type.choices, verbose_name=_('Type'))
    instance_id = models.CharField(max_length=128, verbose_name=_('Instance ID'))
    secret = fields.EncryptTextField(default='', blank=True, verbose_name=_('Secret'))
    client_version = models.CharField(max_length=32, blank=True, default='', verbose_name=_('Client version'))
    protocol_version = models.PositiveSmallIntegerField(default=1, verbose_name=_('Protocol version'))
    config_schema_version = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_('Configuration schema version')
    )
    config_digest = models.CharField(max_length=64, blank=True, default='', verbose_name=_('Configuration digest'))
    sync_status = models.CharField(max_length=32, blank=True, default='', verbose_name=_('Sync status'))
    sync_error = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Sync error'))
    date_last_synced = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last synced'))
    date_last_seen = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last seen'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        unique_together = [('configuration', 'instance_id')]
        ordering = ['application__name', 'instance_id']
        verbose_name = _('Credential client instance')

    def __str__(self):
        return f'{self.application.name}:{self.instance_id}'

    @property
    def name(self):
        return self.instance_id

    @property
    def is_authenticated(self):
        return self.is_active

    @property
    def is_valid(self):
        return self.is_active and self.application.is_active and self.configuration.is_active

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
    delivered_revision = models.PositiveIntegerField(default=0, verbose_name=_('Delivered revision'))
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
    date_delivered = models.DateTimeField(null=True, blank=True, verbose_name=_('Date delivered'))
    date_applied = models.DateTimeField(null=True, blank=True, verbose_name=_('Date applied'))

    class Meta:
        unique_together = [('binding', 'client')]
        ordering = ['binding__application__name', 'client__instance_id']
        verbose_name = _('Credential client status')

    def __str__(self):
        return f'{self.client} - {self.binding.credential.key}'


class ClientAccessConfiguration(JMSOrgBaseModel):
    class DeliveryMode(models.TextChoices):
        json = 'json', _('JSON files')
        environment = 'environment', _('Environment files')
        socket = 'socket', _('Unix socket')

    class SystemdAction(models.TextChoices):
        reload = 'reload', _('Reload')
        restart = 'restart', _('Restart')

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='access_configurations', verbose_name=_('Integration application')
    )
    type = models.CharField(max_length=16, choices=CredentialClientInstance.Type.choices, verbose_name=_('Type'))
    credentials = models.ManyToManyField(
        ApplicationCredential, related_name='access_configurations', verbose_name=_('Credential policies')
    )
    language = models.CharField(max_length=16, default='python', choices=[('python', 'Python')], verbose_name=_('Language'))
    app_user = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Application user'))
    install_path = models.CharField(max_length=256, default='/opt/jumpserver-pam', verbose_name=_('Install path'))
    delivery_mode = models.CharField(
        max_length=16, choices=DeliveryMode.choices,
        default=DeliveryMode.json, verbose_name=_('Delivery mode'),
    )
    systemd_unit = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Systemd unit'))
    systemd_action = models.CharField(
        max_length=16, choices=SystemdAction.choices,
        default=SystemdAction.restart, verbose_name=_('Systemd action'),
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        unique_together = [('application', 'name')]
        ordering = ['name']
        verbose_name = _('Client access configuration')

    def __str__(self):
        return self.name


class CredentialRotationRecord(JMSOrgBaseModel):
    change_automation = models.OneToOneField(
        'assets.BaseAutomation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='credential_rotation',
        verbose_name=_('Change secret automation'),
    )
    change_execution = models.ForeignKey(
        'accounts.AutomationExecution', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name=_('Change secret execution'),
    )
    credential = models.ForeignKey(
        ApplicationCredential, on_delete=models.CASCADE,
        related_name='rotation_records', verbose_name=_('Credential policy')
    )
    source_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT, related_name='+',
        verbose_name=_('Source account'),
    )
    target_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT, related_name='+',
        verbose_name=_('Target account'),
    )
    change_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT, related_name='+',
        verbose_name=_('Account to change'),
    )
    change_account_version_at_start = models.PositiveIntegerField(
        verbose_name=_('Account version at start')
    )
    status = models.CharField(max_length=16, default='running', choices=[
        ('running', _('Running')), ('success', _('Success')),
        ('failed', _('Failed')), ('cancelled', _('Cancelled')),
    ], verbose_name=_('Status'))
    date_finished = models.DateTimeField(null=True, blank=True, verbose_name=_('Date finished'))
    participant_snapshot = models.JSONField(
        default=dict, blank=True, verbose_name=_('Participant snapshot')
    )

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('Credential rotation record')
