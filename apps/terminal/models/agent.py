"""Durable identity, ownership and evidence for external Agent operations."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from orgs.mixins.models import OrgModelMixin


class AgentApplication(models.Model):
    application = models.OneToOneField(
        'oauth2_provider.Application', on_delete=models.CASCADE, related_name='agent_registration',
    )
    resource = models.URLField(max_length=512)
    is_active = models.BooleanField(default=True)
    date_authorized = models.DateTimeField(null=True)


class AgentOAuthBinding(models.Model):
    """Organization chosen for one authorization, independent of token rotation."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application = models.ForeignKey('oauth2_provider.Application', on_delete=models.CASCADE)
    org_id = models.UUIDField()
    grant = models.OneToOneField(
        'oauth2_provider.Grant', null=True, on_delete=models.CASCADE,
    )
    access_token = models.OneToOneField(
        'oauth2_provider.AccessToken', null=True, on_delete=models.CASCADE,
    )
    refresh_family = models.UUIDField(null=True, unique=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=(
                models.Q(grant__isnull=False, access_token__isnull=True, refresh_family__isnull=True)
                | models.Q(grant__isnull=True, access_token__isnull=False, refresh_family__isnull=True)
                | models.Q(grant__isnull=True, access_token__isnull=True, refresh_family__isnull=False)
            ),
            name='agent_oauth_binding_subject',
        )]


class AgentSession(OrgModelMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    application = models.ForeignKey('oauth2_provider.Application', on_delete=models.PROTECT)
    terminal = models.ForeignKey('terminal.Terminal', on_delete=models.PROTECT)
    connection_token = models.OneToOneField('authentication.ConnectionToken', null=True, on_delete=models.SET_NULL)
    requested = models.JSONField(default=dict)
    terminal_session = models.ForeignKey('terminal.Session', null=True, on_delete=models.SET_NULL)
    oauth_token = models.ForeignKey('oauth2_provider.AccessToken', null=True, on_delete=models.SET_NULL)
    oauth_family = models.UUIDField(null=True)
    resource = models.URLField(max_length=512)
    idempotency_key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    capability = models.UUIDField(default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=32, default='awaiting_approval')
    credentials_released = models.BooleanField(default=False)
    date_created = models.DateTimeField(default=timezone.now)
    date_expires = models.DateTimeField()
    date_closed = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=('org_id', 'user', 'application', 'idempotency_key'), name='agent_session_idempotency',
        )]
        ordering = ('-date_created',)


class AgentAction(OrgModelMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AgentSession, on_delete=models.PROTECT, related_name='actions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    application = models.ForeignKey('oauth2_provider.Application', on_delete=models.PROTECT)
    kind = models.CharField(max_length=32)
    idempotency_key = models.CharField(max_length=128)
    request = models.JSONField(default=dict)
    request_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=32, default='accepted')
    cancel_requested = models.BooleanField(default=False)
    ticket = models.ForeignKey('tickets.ApplyCommandTicket', null=True, on_delete=models.PROTECT)
    interactive_token = models.OneToOneField('authentication.ConnectionToken', null=True, on_delete=models.SET_NULL, related_name='agent_interactive_action')
    interactive_session = models.ForeignKey('terminal.Session', null=True, on_delete=models.SET_NULL, related_name='agent_interactive_actions')
    policy_hash = models.CharField(max_length=64, blank=True)
    date_created = models.DateTimeField(default=timezone.now)
    date_started = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)
    last_sequence = models.PositiveBigIntegerField(default=0)
    evidence_bytes = models.PositiveBigIntegerField(default=0)
    result = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=('org_id', 'user', 'application', 'idempotency_key'), name='agent_action_idempotency',
        )]
        ordering = ('-date_created',)


class AgentEvent(models.Model):
    event_id = models.UUIDField(primary_key=True, editable=False)
    action = models.ForeignKey(AgentAction, on_delete=models.PROTECT, related_name='events')
    sequence = models.PositiveBigIntegerField()
    state = models.CharField(max_length=32)
    payload = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64)
    date_received = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=('action', 'sequence'), name='agent_event_sequence',
        )]
        ordering = ('sequence',)
