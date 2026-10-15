# -*- coding: utf-8 -*-
#
import logging

from celery import subtask
from celery.signals import (
    worker_ready, worker_shutdown, after_setup_logger
)
from django.core.cache import cache
from django_celery_beat.models import PeriodicTask

from common.utils import get_logger
from .decorator import get_after_app_ready_tasks, get_after_app_shutdown_clean_tasks
from .logger import CeleryThreadTaskFileHandler

logger = get_logger(__file__)
safe_str = lambda x: x


@worker_ready.connect
def on_app_ready(sender=None, headers=None, **kwargs):
    if cache.get("CELERY_APP_READY", 0) == 1:
        return
    cache.set("CELERY_APP_READY", 1, 10)
    tasks = get_after_app_ready_tasks()
    logger.debug("Work ready signal recv")
    logger.debug("Start need start task: [{}]".format(", ".join(tasks)))
    for task in tasks:
        periodic_task = PeriodicTask.objects.filter(task=task).first()
        if periodic_task and not periodic_task.enabled:
            logger.debug("Periodic task [{}] is disabled!".format(task))
            continue
        subtask(task).delay()


@worker_ready.connect
def clean_orphan_ansible_executor_containers(sender=None, **kwargs):
    """
    When the worker that spawned Docker-isolated ansible jobs dies abruptly
    (SIGKILL / OOM / host reboot) the `docker run --rm` client dies with it but
    dockerd keeps the executor container running.  Clean those up as soon as
    the ansible worker comes back.

    Only the worker consuming the ``ansible`` queue may do this: the ``default``
    worker in the same container is ready at a slightly different time and
    must not remove containers the ansible worker has just started.
    """
    hostname = getattr(sender, 'hostname', '') or ''
    worker_name = hostname.split('@', 1)[0]
    if 'ansible' not in worker_name.split(','):
        return
    try:
        from ops.ansible.docker import remove_orphan_executor_containers
        remove_orphan_executor_containers()
    except Exception as e:
        logger.warning('Clean orphan ansible executor containers failed: %s', e)


@worker_shutdown.connect
def after_app_shutdown_periodic_tasks(sender=None, **kwargs):
    if cache.get("CELERY_APP_SHUTDOWN", 0) == 1:
        return
    cache.set("CELERY_APP_SHUTDOWN", 1, 10)
    tasks = get_after_app_shutdown_clean_tasks()
    logger.debug("Worker shutdown signal recv")
    logger.debug("Clean period tasks: [{}]".format(', '.join(tasks)))
    PeriodicTask.objects.filter(name__in=tasks).delete()


@after_setup_logger.connect
def add_celery_logger_handler(sender=None, logger=None, loglevel=None, format=None, **kwargs):
    if not logger:
        return
    task_handler = CeleryThreadTaskFileHandler()
    task_handler.setLevel(loglevel)
    formatter = logging.Formatter(format)
    task_handler.setFormatter(formatter)
    logger.addHandler(task_handler)
