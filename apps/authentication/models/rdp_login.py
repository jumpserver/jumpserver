import uuid

from django.db import models


class RDPLoginTicket(models.Model):
    """Host-bound, single-use login ticket. Never stores a bearer secret."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection_token = models.OneToOneField(
        'authentication.ConnectionToken', on_delete=models.CASCADE,
        related_name='rdp_login_ticket',
    )
    host_id = models.UUIDField()
    app_name = models.CharField(max_length=128)
    ticket_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)
    grant_hash = models.CharField(max_length=64, null=True, unique=True)
    grant_expires_at = models.DateTimeField(null=True)
    launched_at = models.DateTimeField(null=True)

    class Meta:
        default_permissions = ()
