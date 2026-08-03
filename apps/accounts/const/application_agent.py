from django.db import models
from django.utils.translation import gettext_lazy as _


class ApplicationAgentStatus(models.TextChoices):
    UNREGISTERED = 'unregistered', _('Unregistered')
    ONLINE = 'online', _('Online')
    OFFLINE = 'offline', _('Offline')
    ERROR = 'error', _('Error')


class ApplicationSwitchStatus(models.TextChoices):
    RUNNING = 'running', _('Running')
    WAITING_CONFIRMATION = 'waiting_confirmation', _('Waiting for confirmation')
    COMPLETED = 'completed', _('Completed')
    ROLLING_BACK = 'rolling_back', _('Rolling back')
    ROLLED_BACK = 'rolled_back', _('Rolled back')
    ENDED = 'ended', _('Manually ended')


class ApplicationSwitchItemStatus(models.TextChoices):
    PENDING = 'pending', _('Pending delivery')
    DELIVERED = 'delivered', _('Waiting for confirmation')
    FAILED = 'failed', _('Delivery failed')
    CONFIRMED = 'confirmed', _('Confirmed')
    ROLLBACK_PENDING = 'rollback_pending', _('Rollback pending')
    ROLLBACK_DELIVERED = 'rollback_delivered', _('Rollback waiting for confirmation')
    ROLLED_BACK = 'rolled_back', _('Rolled back')


class ApplicationAgentEventType(models.TextChoices):
    SWITCH = 'switch', _('Switch account')
    ROLLBACK = 'rollback', _('Rollback account')


class ApplicationAgentEventStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    DELIVERED = 'delivered', _('Delivered')
