# -*- coding: utf-8 -*-
#

from celery import shared_task
from ops.celery.decorator import register_as_period_task
from django.contrib.sessions.models import Session
from django.utils import timezone

from .utils import write_login_log


@shared_task
def write_login_log_async(*args, **kwargs):
    write_login_log(*args, **kwargs)


@register_as_period_task(interval=3600*24)
@shared_task
def clean_django_sessions():
    Session.objects.filter(expire_date__lt=timezone.now()).delete()


