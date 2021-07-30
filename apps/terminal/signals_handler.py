# -*- coding: utf-8 -*-
#

import os
import socket
from celery import shared_task
from django.conf import settings
from common.utils import get_logger
from common.utils import get_disk_usage, get_cpu_load, get_memory_usage
from ops.celery.decorator import (
    register_as_period_task, after_app_ready_start, after_app_shutdown_clean_periodic
)
from .serializers.terminal import TerminalRegistrationSerializer, StatusSerializer
from .const import TerminalTypeChoices
from .models.terminal import Terminal


logger = get_logger(__file__)


CORE_NODE_NAME = os.environ.get('CORE_NODE_NAME', socket.gethostname())
CORE_TERMINAL_NAME = f'[Core] {CORE_NODE_NAME}'


def get_core_terminal():
    tp = TerminalTypeChoices.core
    terminal = Terminal.objects.filter(name=CORE_TERMINAL_NAME, type=tp).first()
    return terminal


def registration_core_terminal():
    data = {
        'name': CORE_TERMINAL_NAME,
        'type': TerminalTypeChoices.core,
        'remote_addr': socket.gethostbyname(socket.gethostname()),
    }
    serializer = TerminalRegistrationSerializer(data=data)
    serializer.is_valid()
    terminal = serializer.save()
    return terminal


@after_app_ready_start
def get_or_registration_core_terminal(log_output=True):
    terminal = get_core_terminal()
    msg = 'The Core ({}) terminal is already registered.'
    if not terminal:
        terminal = registration_core_terminal()
        msg = 'The Core ({}) terminal is successfully registered.'
    if log_output:
        logger.info(msg.format(terminal.name))
    return terminal


@shared_task
@register_as_period_task(interval=30)
@after_app_ready_start
@after_app_shutdown_clean_periodic
def core_terminal_heartbeat():
    terminal = get_or_registration_core_terminal(log_output=False)
    heartbeat_data = {
        'cpu_load': get_cpu_load(),
        'memory_used': get_memory_usage(),
        'disk_used': get_disk_usage(path=settings.BASE_DIR),
        'sessions': [],
    }
    status_serializer = StatusSerializer(data=heartbeat_data)
    status_serializer.is_valid()
    status_serializer.validated_data.pop('sessions', None)
    status_serializer.validated_data['terminal'] = terminal
    status_serializer.save()

