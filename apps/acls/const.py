from django.db import models
from django.utils.translation import gettext_lazy as _


class ActionChoices(models.TextChoices):
    reject = 'reject', _('Reject')
    accept = 'accept', _('Accept')
    review = 'review', _('Review')
    warning = 'warning', _('Warn')
    notice = 'notice', _('Notify')
    notify_and_warn = 'notify_and_warn', _('Notify and warn')
