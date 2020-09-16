# -*- coding: utf-8 -*-
from django.conf import settings
from django.dispatch import receiver
from terminal.signals import post_command_executed
from terminal.utils import send_command_alert_mail
from common.utils import get_logger

logger = get_logger(__name__)


@receiver(post_command_executed)
def on_insecure_command_execute(sender, risk_level, **kwargs):
    if risk_level >= settings.INSECURE_COMMAND_LEVEL and settings.SEND_COMMAND_ALERT_EMAIL_ENABLED:
        try:
            send_command_alert_mail(risk_level, **kwargs)
        except Exception as e:
            logger.error(e)
