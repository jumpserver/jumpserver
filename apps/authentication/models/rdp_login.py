import uuid

from django.db import models


class RDPLoginTicket(models.Model):
    """One Windows login attempt; credentials are stored only as hashes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    connection_token = models.ForeignKey(
        'authentication.ConnectionToken', on_delete=models.CASCADE,
        related_name='rdp_login_tickets',
    )
    org_id = models.UUIDField()
    user_id = models.UUIDField()
    asset_id = models.UUIDField()
    host_id = models.UUIDField()
    app_id = models.UUIDField()
    app_name = models.CharField(max_length=128)
    username = models.CharField(max_length=20, unique=True)
    password_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    redeemed_at = models.DateTimeField(null=True)
    redeemed_by_id = models.UUIDField(null=True)
    redemption_id = models.UUIDField(null=True)
    broker_instance_id = models.UUIDField(null=True)
    windows_session_id = models.PositiveBigIntegerField(null=True)
    grant_hash = models.CharField(max_length=64, null=True, unique=True)
    login_deadline = models.DateTimeField(null=True)
    launch_deadline = models.DateTimeField(null=True)
    launched_at = models.DateTimeField(null=True)
    request_id = models.UUIDField(null=True)
    local_sid = models.CharField(max_length=184, blank=True)
    logon_id = models.CharField(max_length=64, blank=True)

    class Meta:
        default_permissions = ()
        constraints = [models.UniqueConstraint(
            fields=['redeemed_by_id', 'redemption_id'], name='rdp_login_unique_redemption',
        )]
