import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone

from orgs.mixins.models import OrgModelMixin

__all__ = ['TicketAttachment']


class TicketAttachment(OrgModelMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ticket = models.ForeignKey('Ticket', on_delete=models.PROTECT, related_name='attachments')
    name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=64)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    purged_at = models.DateTimeField(null=True)

    @property
    def path(self):
        return Path(settings.SHARE_DIR) / 'ticket_attachments' / str(uuid.UUID(str(self.org_id))) / str(self.pk)

    @property
    def expires_at(self):
        return self.date_created + timedelta(days=settings.TICKET_ATTACHMENT_RETENTION_DAYS)

    @property
    def expired(self):
        return bool(self.purged_at or self.expires_at <= timezone.now())

    class Meta:
        default_permissions = ()
        ordering = ['date_created', 'id']
