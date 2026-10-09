from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AuditSource(TextChoices):
    ADMINISTRATOR = 'Administrator', _('Administrator')
    SDK = 'SDK', _('SDK')
    AGENT = 'Agent', _('Agent')
    JUMPSERVER = 'JumpServer', _('JumpServer')


class AuditEvent(TextChoices):
    COMMAND_REQUESTED = 'command_requested', _('Application command requested')
    COMMAND_RESULT = 'command_result', _('Application command result')
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
    CREDENTIAL_REPUBLISHED = 'credential_republished', _('Credential notification republished')
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
    ROTATION_VERIFICATION_STARTED = 'rotation.verification.started', _('Backup account verification started')
    ROTATION_VERIFICATION_FAILED = 'rotation.verification.failed', _('Backup account verification failed')
    ROTATION_VERIFICATION_CANCELLED = 'rotation.verification.cancelled', _('Backup account verification cancelled')
    ROTATION_PREPARATION_STARTED = 'rotation.preparation.started', _('Rotation preparation started')
    ROTATION_ACCOUNTS_ALIGNED = 'rotation.accounts.aligned', _('Rotation accounts aligned')
    ROTATION_STANDBY_WAITING = 'rotation.standby.waiting', _('Observing standby account usage')
    ROTATION_PREPARATION_READY = 'rotation.preparation.ready', _('Rotation preparation ready')
    ROTATION_PREPARATION_CANCELLED = 'rotation.preparation.cancelled', _('Rotation preparation cancelled')
    CREDENTIAL_UPDATED = 'credential.updated', _('Credential updated')
    CREDENTIAL_REVOKED = 'credential.revoked', _('Credential revoked')
    CONFIGURATION_UPDATED = 'configuration.updated', _('Configuration updated')
    CREDENTIAL_CHANGE_STARTED = 'credential.change.started', _('Credential change started')
    CREDENTIAL_CHANGE_COMPLETED = 'credential.change.completed', _('Credential change completed')
    CREDENTIAL_CHANGE_FAILED = 'credential.change.failed', _('Credential change failed')
    ROTATION_STARTED = 'rotation.started', _('Rotation started')
    ROTATION_WAITING = 'rotation.waiting_for_application', _('Rotation waiting for application')
    ROTATION_SOURCE_WAITING = 'rotation.source.waiting', _('Observing source account secret fetches')
    ROTATION_SOURCE_READY = 'rotation.source.ready', _('Source account secret fetch window completed')
    ROTATION_FORCE_STOPPED = 'rotation.force_stopped', _('Rotation forcibly stopped')
    ROTATION_COMPLETED = 'rotation.completed', _('Rotation completed')
    ROTATION_FAILED = 'rotation.failed', _('Rotation failed')


class ApplicationCommandEvent(TextChoices):
    ACCOUNT_SWITCH_REQUESTED = 'credential.switch.requested', _('Account switch requested')
    APPLICATION_RESTART_REQUESTED = 'application.restart.requested', _('Application restart requested')


class WebhookRequestMethod(TextChoices):
    POST = 'POST', 'POST'
    PUT = 'PUT', 'PUT'
    PATCH = 'PATCH', 'PATCH'
