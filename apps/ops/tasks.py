# coding: utf-8

from __future__ import absolute_import, unicode_literals

import json
import time

from celery import shared_task
from django.utils import timezone

from assets.models import Asset
from common.utils import get_logger, encrypt_password
from ops.ansible.runner import AdHocRunner

logger = get_logger(__file__)





@shared_task(bind=True)
def run_AdHoc(self, task_tuple, assets,
              task_name='Ansible AdHoc runner',
              pattern='all', record=True):

    if not assets:
        logger.warning('Empty assets, runner cancel')
    if isinstance(assets[0], Asset):
        assets = [asset._to_secret_json() for asset in assets]

    runner = AdHocRunner(assets)
    if record:
        from .models import TaskRecord
        if not TaskRecord.objects.filter(uuid=self.request.id):
            record = TaskRecord(uuid=self.request.id,
                                name=task_name,
                                assets=','.join(str(asset['id']) for asset in assets),
                                module_args=task_tuple,
                                pattern=pattern)
            record.save()
        else:
            record = TaskRecord.objects.get(uuid=self.request.id)
            record.date_start = timezone.now()
    ts_start = time.time()
    logger.warn('Start runner {}'.format(task_name))
    result = runner.run(task_tuple, pattern=pattern, task_name=task_name)
    timedelta = round(time.time() - ts_start, 2)
    summary = runner.clean_result()
    if record:
        record.date_finished = timezone.now()
        record.is_finished = True
        record.result = json.dumps(result)
        record.summary = json.dumps(summary)
        record.timedelta = timedelta
        if len(summary['failed']) == 0:
            record.is_success = True
        else:
            record.is_success = False
        record.save()
    return summary, result


def rerun_AdHoc(uuid):
    from .models import TaskRecord
    record = TaskRecord.objects.get(uuid=uuid)
    assets = record.assets_json
    task_tuple = record.module_args
    pattern = record.pattern
    task_name = record.name
    task = run_AdHoc.apply_async((task_tuple, assets),
                                 {'pattern': pattern, 'task_name': task_name},
                                 task_id=uuid)
    return task


def push_users(assets, users):
    """
    user: {
        name: 'web',
        username: 'web',
        shell: '/bin/bash',
        password: '123123123',
        public_key: 'string',
        sudo: '/bin/whoami,/sbin/ifconfig'
    }
    """
    if isinstance(users, dict):
        users = [users]
    if isinstance(assets, dict):
        assets = [assets]
    task_tuple = []

    for user in users:
        # 添加用户, 设置公钥, 设置sudo
        task_tuple.extend([
            ('user', 'name={} shell={} state=present password={}'.format(
                user['username'], user.get('shell', '/bin/bash'),
                encrypt_password(user.get('password', None)))),
            ('authorized_key', "user={} state=present key='{}'".format(
                user['username'], user['public_key'])),
            ('lineinfile',
             "name=/etc/sudoers state=present regexp='^{0} ALL=(ALL)' "
             "line='{0} ALL=(ALL) NOPASSWD: {1}' "
             "validate='visudo -cf %s'".format(
                 user['username'], user.get('sudo', '/bin/whoami')
             ))
        ])
    task_name = 'Push user {}'.format(','.join([user['name'] for user in users]))
    task = run_AdHoc.delay(task_tuple, assets, pattern='all', task_name=task_name)
    return task


