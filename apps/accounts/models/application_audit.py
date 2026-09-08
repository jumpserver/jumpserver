from django.db import models
from django.utils import timezone
from accounts.const import AuditSource
from orgs.mixins.models import JMSOrgBaseModel


class ApplicationAudit(JMSOrgBaseModel):
    event = models.CharField(max_length=64, db_index=True)
    result = models.CharField(max_length=16, default='success', db_index=True)
    service = models.CharField(max_length=128, blank=True)
    service_id = models.UUIDField(null=True)
    credential = models.CharField(max_length=128, blank=True)
    credential_id = models.UUIDField(null=True)
    credential_key = models.CharField(max_length=64, blank=True)
    configuration = models.CharField(max_length=128, blank=True)
    configuration_id = models.UUIDField(null=True)
    instance_id = models.CharField(max_length=128, blank=True)
    source = models.CharField(max_length=16, default=AuditSource.JUMPSERVER)
    operator = models.CharField(max_length=128, blank=True)
    remote_addr = models.GenericIPAddressField(null=True)
    revision = models.PositiveIntegerField(null=True)
    rotation_id = models.UUIDField(null=True)
    summary = models.CharField(max_length=512, blank=True)
    changes = models.JSONField(default=list)

    class Meta:
        ordering = ['-date_created', '-id']
        indexes = [models.Index(fields=['org_id', '-date_created'])]


class ApplicationEventDelivery(JMSOrgBaseModel):
    event = models.ForeignKey(ApplicationAudit, on_delete=models.PROTECT, related_name='deliveries')
    audit = models.OneToOneField(ApplicationAudit, on_delete=models.PROTECT, related_name='delivery')
    client = models.ForeignKey('accounts.CredentialClientInstance', null=True, on_delete=models.SET_NULL)
    code = models.CharField(max_length=64)
    url = models.CharField(max_length=2048, blank=True)
    status = models.CharField(max_length=16, default='pending')
    available_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'client'], name='unique_application_event_client')]
        indexes = [models.Index(fields=['client', 'status', 'available_at'])]


class ApplicationEventAttempt(JMSOrgBaseModel):
    delivery = models.ForeignKey(ApplicationEventDelivery, on_delete=models.CASCADE, related_name='attempts')
    number = models.PositiveSmallIntegerField()
    result = models.CharField(max_length=16, default='pending')
    status_code = models.PositiveSmallIntegerField(null=True)
    reason = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ['number']
        constraints = [models.UniqueConstraint(fields=['delivery', 'number'], name='unique_application_event_attempt')]
