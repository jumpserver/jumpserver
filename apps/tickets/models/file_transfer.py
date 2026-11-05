import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from orgs.mixins.models import OrgModelMixin

__all__ = ['TicketTransferFile', 'TicketTransferExecution']


class TicketTransferFile(OrgModelMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    ticket = models.ForeignKey('Ticket', null=True, on_delete=models.PROTECT, related_name='transfer_files')
    name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    kind = models.CharField(max_length=8, default='upload')
    date_created = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    purged_at = models.DateTimeField(null=True)

    @property
    def path(self):
        # File content is private shared worker data, never a media URL or a user path.
        return Path(settings.SHARE_DIR) / 'ticket_transfers' / str(uuid.UUID(str(self.org_id))) / str(self.pk)

    def summary(self):
        return {'id': str(self.pk), 'name': self.name, 'size': self.size, 'sha256': self.sha256}

    class Meta:
        default_permissions = ()


class TicketTransferExecution(OrgModelMixin):
    ticket = models.OneToOneField('Ticket', primary_key=True, on_delete=models.PROTECT,
                                 related_name='transfer_execution')
    state = models.CharField(max_length=16, default='queued', db_index=True)
    files = models.JSONField(default=list)
    remote_addr = models.GenericIPAddressField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_started = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)
    dispatch_after = models.DateTimeField(null=True)

    class Meta:
        default_permissions = ()
