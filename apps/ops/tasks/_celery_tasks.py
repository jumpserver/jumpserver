from __future__ import absolute_import, unicode_literals

from celery import shared_task

from common import celery_app
from ops.utils.ansible_api import Config, ADHocRunner


@shared_task(name="get_asset_hardware_info")
def get_asset_hardware_info(task_name, task_uuid, *assets):
    conf = Config()
    play_source = {
            "name": "Get host hardware information",
            "hosts": "default",
            "gather_facts": "no",
            "tasks": [
                dict(action=dict(module='setup'))
            ]
        }
    hoc = ADHocRunner(conf, play_source, *assets)
    ext_code, result = hoc.run(task_name, task_uuid)
    return ext_code, result


@shared_task(name="asset_test_ping_check")
def asset_test_ping_check(task_name, task_uuid, *assets):
    conf = Config()
    play_source = {
            "name": "Test host connection use ping",
            "hosts": "default",
            "gather_facts": "no",
            "tasks": [
                dict(action=dict(module='ping'))
            ]
        }
    hoc = ADHocRunner(conf, play_source, *assets)
    ext_code, result = hoc.run(task_name, task_uuid)
    return ext_code, result


@shared_task(name="add_user_to_assert")
def add_user_to_asset():
    pass


@celery_app.task(name='hello-world')
def hello():
    print('hello world!')
