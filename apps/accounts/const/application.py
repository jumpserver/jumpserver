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
    CREDENTIAL_STREAM_CONNECTED = 'credential_stream_connected', _('Credential stream connected')
    CREDENTIAL_STREAM_DISCONNECTED = 'credential_stream_disconnected', _('Credential stream disconnected')
    SECRET_CHANGE_STARTED = 'secret_change_started', _('Secret change started')
    SECRET_CHANGE_COMPLETED = 'secret_change_completed', _('Secret change completed')
    SECRET_CHANGE_FAILED = 'secret_change_failed', _('Secret change failed')
    APPLICATION_SECRET_RESET = 'application_secret_reset', _('Application secret reset')
    ROTATION_STARTED = 'rotation_started', _('Rotation started')
    ROTATION_STEP = 'rotation_step', _('Rotation step')
    ROTATION_CANCELLED = 'rotation_cancelled', _('Rotation cancelled')
    NOTIFICATION = 'notification', _('Application notification')


class ApplicationEvent(TextChoices):
    CREDENTIAL_UPDATED = 'credential.updated', _('Credential updated')
    CREDENTIAL_REVOKED = 'credential.revoked', _('Credential revoked')
    CONFIGURATION_UPDATED = 'configuration.updated', _('Configuration updated')
    CREDENTIAL_CHANGE_STARTED = 'credential.change.started', _('Credential change started')
    CREDENTIAL_CHANGE_COMPLETED = 'credential.change.completed', _('Credential change completed')
    CREDENTIAL_CHANGE_FAILED = 'credential.change.failed', _('Credential change failed')
    ROTATION_STARTED = 'rotation.started', _('Rotation started')
    ROTATION_WAITING = 'rotation.waiting_for_application', _('Rotation waiting for application')
    ROTATION_COMPLETED = 'rotation.completed', _('Rotation completed')
    ROTATION_FAILED = 'rotation.failed', _('Rotation failed')


class WebhookRequestMethod(TextChoices):
    POST = 'POST', 'POST'
    PUT = 'PUT', 'PUT'
    PATCH = 'PATCH', 'PATCH'
