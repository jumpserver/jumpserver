from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class NodeType(TextChoices):
    start = 'start', _('Start')
    approval = 'approval', _('Approval')
    condition = 'condition', _('Condition')
    end = 'end', _('End')


class InstanceState(TextChoices):
    pending = 'pending', _('Pending')
    running = 'running', _('Running')
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')
    cancelled = 'cancelled', _('Cancelled')
    expired = 'expired', _('Expired')
    error = 'error', _('Error')


class NodeState(TextChoices):
    running = 'running', _('Running')
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')
    skipped = 'skipped', _('Skipped')
    cancelled = 'cancelled', _('Cancelled')


class TaskState(TextChoices):
    pending = 'pending', _('Pending')
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')
    transferred = 'transferred', _('Transferred')
    cancelled = 'cancelled', _('Cancelled')
    expired = 'expired', _('Expired')
