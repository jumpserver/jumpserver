# -*- coding: utf-8 -*-
#

from celery import shared_task
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ops.celery.decorator import register_as_period_task


@shared_task(
    verbose_name=_('Clean expired session'),
    description=_(
        "Since user logins create sessions, the system will clean up expired sessions every 24 hours"
    )
)
@register_as_period_task(interval=3600 * 24)
def clean_django_sessions():
    Session.objects.filter(expire_date__lt=timezone.now()).delete()
