from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AuditSource(TextChoices):
    ADMINISTRATOR = 'Administrator', _('Administrator')
    SDK = 'SDK', _('SDK')
    AGENT = 'Agent', _('Agent')
    JUMPSERVER = 'JumpServer', _('JumpServer')


class AuditEvent(TextChoices):
    CONFIGURATION_CREATED = 'configuration_created', _('Configuration created')
    CONFIGURATION_UPDATED = 'configuration_updated', _('Configuration updated')
    CONFIGURATION_DELETED = 'configuration_deleted', _('Configuration deleted')
    AUTHORIZATION_GRANTED = 'authorization_granted', _('Authorization granted')
    AUTHORIZATION_REVOKED = 'authorization_revoked', _('Authorization revoked')
    CLIENT_REGISTERED = 'client_registered', _('Client registered')
    CLIENT_ENABLED = 'client_enabled', _('Client enabled')
    CLIENT_DISABLED = 'client_disabled', _('Client disabled')
    CREDENTIAL_FETCHED = 'credential_fetched', _('Credential fetched')
    CREDENTIAL_CONFIRMED = 'credential_confirmed', _('Credential confirmed')
    CREDENTIAL_PUBLISHED = 'credential_published', _('Credential published')
    SECRET_CHANGE_FINISHED = 'secret_change_finished', _('Secret change finished')
    APPLICATION_SECRET_RESET = 'application_secret_reset', _('Application secret reset')
    ROTATION_STARTED = 'rotation_started', _('Rotation started')
    ROTATION_STEP = 'rotation_step', _('Rotation step')
    ROTATION_CANCELLED = 'rotation_cancelled', _('Rotation cancelled')
    SUBSCRIPTION_SNAPSHOT = 'subscription_snapshot', _('Subscription snapshot')
    NOTIFICATION = 'notification', _('Application notification')


class ApplicationEvent(TextChoices):
    CREDENTIAL_PUBLISHED = 'credential.published', _('Credential published')
    CREDENTIAL_UNAVAILABLE = 'credential.unavailable', _('Credential unavailable')
    ROTATION_FAILED = 'rotation.failed', _('Rotation failed')
    ACCESS_REVOKED = 'access.revoked', _('Access revoked')
