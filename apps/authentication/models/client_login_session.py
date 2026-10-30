import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from oauth2_provider.settings import oauth2_settings


class ClientLoginSession(models.Model):
    """One interactive desktop authentication, across OAuth token rotations."""

    class RevokeReason(models.TextChoices):
        logout = 'logout', _('Logout')
        app_exit = 'app_exit', _('Client exit')
        idle_timeout = 'idle_timeout', _('Idle timeout')
        absolute_timeout = 'absolute_timeout', _('Maximum login time')
        policy_changed = 'policy_changed', _('Client login policy changed')
        security_revoke = 'security_revoke', _('Authorization revoked')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application = models.ForeignKey(oauth2_settings.APPLICATION_MODEL, on_delete=models.CASCADE)
    token_family = models.UUIDField()
    authenticated_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_activity_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoke_reason = models.CharField(max_length=32, choices=RevokeReason.choices, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('application', 'token_family'), name='client_login_app_family_uniq'),
            models.CheckConstraint(
                condition=(models.Q(revoked_at__isnull=True, revoke_reason='') |
                           (models.Q(revoked_at__isnull=False) & ~models.Q(revoke_reason=''))),
                name='client_login_revoke_pair',
            ),
        ]
