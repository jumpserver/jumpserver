# -*- coding: utf-8 -*-

import os

from kombu import Exchange, Queue
from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')
from jumpserver import settings
# from django.conf import settings

app = Celery('jumpserver')

configs = {k: v for k, v in settings.__dict__.items() if k.startswith('CELERY')}
# Using a string here means the worker will not have to
# pickle the object when using Windows.
# app.config_from_object('django.conf:settings', namespace='CELERY')
configs["CELERY_QUEUES"] = [
    Queue("celery", Exchange("celery"), routing_key="celery"),
    Queue("ansible", Exchange("ansible"), routing_key="ansible"),
    Queue("celery_node_tree", Exchange("celery_node_tree"), routing_key="celery_node_tree")
]
configs["CELERY_ROUTES"] = {
    "ops.tasks.run_ansible_task": {'exchange': 'ansible', 'routing_key': 'ansible'},
}

app.namespace = 'CELERY'
app.conf.update(configs)
app.autodiscover_tasks(lambda: [app_config.split('.')[0] for app_config in settings.INSTALLED_APPS])

app.conf.beat_schedule = {
    'check-asset-permission-expired': {
        'task': 'perms.tasks.check_asset_permission_expired',
        'schedule': settings.PERM_EXPIRED_CHECK_PERIODIC,
        'args': ()
    },
    'check-node-assets-amount': {
        'task': 'assets.tasks.nodes_amount.check_node_assets_amount_celery_task',
        'schedule': crontab(minute=0, hour=0),
        'args': ()
    },
}
