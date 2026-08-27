from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.db import fields
from ops.mixin import PeriodTaskModelMixin, PeriodTaskModelQuerySet
from orgs.mixins.models import JMSOrgBaseModel, OrgManager
from ..const import (
    CredentialIssueStatus, CredentialLeaseStatus,
    CredentialPolicyMode, CredentialPolicyStatus,
)

__all__ = [
    'CredentialPolicy', 'CredentialPolicyVersion',
    'CredentialIssueRequest', 'CredentialLease',
]


class CredentialPolicyManager(OrgManager.from_queryset(PeriodTaskModelQuerySet)):
    pass


class CredentialPolicy(PeriodTaskModelMixin, JMSOrgBaseModel):
    objects = CredentialPolicyManager()

    application = models.ForeignKey(
        'accounts.IntegrationApplication', related_name='credential_policies',
        on_delete=models.PROTECT, verbose_name=_('Application'),
    )
    mode = models.CharField(
        max_length=16, choices=CredentialPolicyMode.choices,
        verbose_name=_('Mode'),
    )
    status = models.CharField(
        max_length=16, choices=CredentialPolicyStatus.choices,
        default=CredentialPolicyStatus.enabled, db_index=True,
        verbose_name=_('Status'),
    )
    asset = models.ForeignKey(
        'assets.Asset', related_name='credential_policies',
        on_delete=models.PROTECT, verbose_name=_('Asset'),
    )
    account = models.ForeignKey(
        'accounts.Account', related_name='credential_policies',
        on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Account'),
    )
    account_template = models.ForeignKey(
        'accounts.AccountTemplate', related_name='credential_policies',
        on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Account template'),
    )
    management_account = models.ForeignKey(
        'accounts.Account', related_name='managed_credential_policies',
        on_delete=models.PROTECT, verbose_name=_('Management account'),
    )
    interval = models.PositiveIntegerField(
        default=86400, null=True, blank=True,
        verbose_name=_('Rotation period'),
    )
    password_rules = models.JSONField(
        default=dict, blank=True, verbose_name=_('Password rules'),
    )
    username_template = models.CharField(
        max_length=255, blank=True,
        default='jms_{application}_{policy}_{random}',
        verbose_name=_('Username template'),
    )
    platform_params = models.JSONField(
        default=dict, blank=True, verbose_name=_('Platform parameters'),
    )
    default_ttl = models.PositiveIntegerField(
        default=3600, null=True, blank=True,
        verbose_name=_('Default TTL'),
    )
    max_ttl = models.PositiveIntegerField(
        default=86400, null=True, blank=True,
        verbose_name=_('Maximum TTL'),
    )
    max_active_leases = models.PositiveIntegerField(
        default=10, null=True, blank=True,
        verbose_name=_('Maximum active leases'),
    )
    current_version = models.PositiveIntegerField(
        default=0, verbose_name=_('Current version'),
    )
    date_last_rotated = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date last rotated'),
    )
    last_execution = models.ForeignKey(
        'assets.AutomationExecution', related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Last execution'),
    )
    operation_task_id = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name=_('Operation task ID'),
    )
    last_error = models.TextField(blank=True, verbose_name=_('Last error'))

    class Meta:
        unique_together = [('application', 'name')]
        constraints = [
            models.UniqueConstraint(
                fields=('account',),
                name='accounts_unique_credential_policy_account',
            ),
        ]
        ordering = ('name',)
        verbose_name = _('Credential policy')

    @property
    def interval_ratio(self):
        return 1, 's'

    def get_register_task(self):
        from accounts.tasks import rotate_credential_policy_task

        name = f'credential_policy_rotate_{self.id}'
        return name, rotate_credential_policy_task.name, (str(self.id),), {
            'trigger': 'timing',
        }

    def save(self, *args, **kwargs):
        self.is_periodic = (
            self.mode == CredentialPolicyMode.static
            and self.status == CredentialPolicyStatus.enabled
        )
        self.crontab = ''
        if self.mode == CredentialPolicyMode.dynamic:
            self.interval = None
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields) | {'is_periodic', 'crontab'}
            if self.mode == CredentialPolicyMode.dynamic:
                update_fields.add('interval')
            kwargs['update_fields'] = list(update_fields)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}@{self.application}'


class CredentialPolicyVersion(JMSOrgBaseModel):
    policy = models.ForeignKey(
        CredentialPolicy, related_name='versions',
        on_delete=models.CASCADE, verbose_name=_('Credential policy'),
    )
    version = models.PositiveIntegerField(verbose_name=_('Version'))
    account = models.ForeignKey(
        'accounts.Account', related_name='credential_policy_versions',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Account'),
    )
    account_version = models.IntegerField(
        null=True, blank=True, verbose_name=_('Account version'),
    )
    change_secret_record = models.ForeignKey(
        'accounts.ChangeSecretRecord', related_name='credential_policy_versions',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Change secret record'),
    )

    class Meta:
        default_permissions = ('view',)
        unique_together = [('policy', 'version')]
        ordering = ('-version',)
        verbose_name = _('Credential policy version')


class CredentialIssueRequest(JMSOrgBaseModel):
    policy = models.ForeignKey(
        CredentialPolicy, related_name='issue_requests',
        on_delete=models.CASCADE, verbose_name=_('Credential policy'),
    )
    idempotency_key = models.CharField(
        max_length=128, null=True, blank=True,
        verbose_name=_('Idempotency key'),
    )
    status = models.CharField(
        max_length=16, choices=CredentialIssueStatus.choices,
        default=CredentialIssueStatus.pending, db_index=True,
        verbose_name=_('Status'),
    )
    username = models.CharField(
        max_length=128, blank=True, verbose_name=_('Username'),
    )
    provisional_secret = fields.EncryptTextField(
        blank=True, null=True, verbose_name=_('Provisional secret'),
    )
    lease = models.OneToOneField(
        'accounts.CredentialLease', related_name='issue_request',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Credential lease'),
    )
    execution = models.ForeignKey(
        'assets.AutomationExecution', related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Execution'),
    )
    cleanup_execution = models.ForeignKey(
        'assets.AutomationExecution', related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Cleanup execution'),
    )
    vault_cleanup_pending = models.BooleanField(
        default=False, verbose_name=_('Vault cleanup pending'),
    )
    deadline = models.DateTimeField(db_index=True, verbose_name=_('Deadline'))
    replay_until = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Replay until'),
    )
    date_completed = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date completed'),
    )
    remote_addr = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_('Remote address'),
    )
    error_code = models.CharField(
        max_length=64, blank=True, verbose_name=_('Error code'),
    )
    error = models.TextField(blank=True, verbose_name=_('Error'))

    class Meta:
        default_permissions = ('view',)
        unique_together = [('policy', 'idempotency_key')]
        ordering = ('-date_created',)
        verbose_name = _('Credential issue request')

    @property
    def replayable(self):
        return (
            self.status == CredentialIssueStatus.succeeded
            and self.replay_until
            and self.replay_until > timezone.now()
            and bool(self.lease_id)
        )


class CredentialLease(JMSOrgBaseModel):
    policy = models.ForeignKey(
        CredentialPolicy, related_name='leases',
        on_delete=models.CASCADE, verbose_name=_('Credential policy'),
    )
    account = models.OneToOneField(
        'accounts.Account', related_name='credential_lease',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Account'),
    )
    username = models.CharField(max_length=128, verbose_name=_('Username'))
    status = models.CharField(
        max_length=16, choices=CredentialLeaseStatus.choices,
        default=CredentialLeaseStatus.active, db_index=True,
        verbose_name=_('Status'),
    )
    date_expires = models.DateTimeField(db_index=True, verbose_name=_('Date expires'))
    date_max_expires = models.DateTimeField(verbose_name=_('Date max expires'))
    date_last_renewed = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date last renewed'),
    )
    date_revoked = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date revoked'),
    )
    renew_count = models.PositiveIntegerField(default=0, verbose_name=_('Renew count'))
    revoke_reason = models.CharField(
        max_length=32, blank=True, verbose_name=_('Revoke reason'),
    )
    revoke_succeeded = models.BooleanField(
        null=True, blank=True, verbose_name=_('Revoke succeeded'),
    )
    revoke_error = models.TextField(blank=True, verbose_name=_('Revoke error'))
    issue_execution = models.ForeignKey(
        'assets.AutomationExecution', related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Issue execution'),
    )
    revoke_execution = models.ForeignKey(
        'assets.AutomationExecution', related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Revoke execution'),
    )

    class Meta:
        default_permissions = ('view', 'change')
        ordering = ('-date_created',)
        indexes = [
            models.Index(
                fields=('policy', 'status', 'date_expires'),
                name='acct_lease_policy_status_idx',
            ),
        ]
        verbose_name = _('Credential lease')

    @property
    def renewable(self):
        return (
            self.status == CredentialLeaseStatus.active
            and self.date_expires > timezone.now()
            and self.date_expires < self.date_max_expires
        )
