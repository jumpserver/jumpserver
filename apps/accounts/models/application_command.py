from django.db import models

from orgs.mixins.models import JMSOrgBaseModel

__all__ = ['ApplicationCommand']


class ApplicationCommand(JMSOrgBaseModel):
    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.SET_NULL, null=True, related_name='commands',
    )
    source_event = models.OneToOneField(
        'accounts.ApplicationAudit', on_delete=models.CASCADE, related_name='command',
    )
    event = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    recipients = models.JSONField(default=list)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-date_created', '-id']
