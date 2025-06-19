# -*- coding: utf-8 -*-
#
import datetime
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from authentication.models import ConnectionToken, TempToken
from common.const.crontab import CRONTAB_AT_AM_TWO
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org


@shared_task(
    verbose_name=_('Clean expired session'),
    description=_(
        "Since user logins create sessions, the system will clean up expired sessions every 24 hours"
    )
)
@register_as_period_task(interval=3600 * 24)
def clean_django_sessions():
    Session.objects.filter(expire_date__lt=timezone.now()).delete()


@shared_task(
    verbose_name=_('Clean expired temporary, connection tokens'),
    description=_(
        "When connecting to assets or generating temporary passwords, the system creates corresponding connection "
        "tokens or temporary credential records. To maintain security and manage storage, the system automatically "
        "deletes expired tokens every day at 2:00 AM based on the retention settings configured under System settings "
        "> Security > User password > Token Retention Period"
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def clean_expire_token():
    logging.info('Cleaning expired temporary and connection tokens...')
    with tmp_to_root_org():
        now = timezone.now()
        days = settings.SECURITY_EXPIRED_TOKEN_RECORD_KEEP_DAYS
        expired_time = now - datetime.timedelta(days=days)
        count = ConnectionToken.objects.filter(date_expired__lt=expired_time).delete()
        logging.info('Deleted %d expired connection tokens.', count[0])
        count = TempToken.objects.filter(date_expired__lt=expired_time).delete()
        logging.info('Deleted %d temporary tokens.', count[0])
    logging.info('Cleaned expired temporary and connection tokens.')
