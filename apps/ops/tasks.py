# coding: utf-8

from __future__ import absolute_import, unicode_literals
import time


from django.utils import timezone
from celery import shared_task

from common.utils import get_logger, encrypt_password
from .utils.runner import AdHocRunner
from .models import TaskRecord

logger = get_logger(__file__)


@shared_task(name="get_assets_hardware_info")
def get_assets_hardware_info(self, assets):
    task_tuple = (
        ('setup', ''),
    )
    hoc = AdHocRunner(assets)
    return hoc.run(task_tuple)


@shared_task(name="asset_test_ping_check")
def asset_test_ping_check(assets):
    task_tuple = (
        ('ping', ''),
    )
    hoc = AdHocRunner(assets)
    result = hoc.run(task_tuple)
    return result['contacted'].keys(), result['dark'].keys()


@shared_task(bind=True)
def push_users(self, assets, users):
    """
    user: {
        username: xxx,
        shell: /bin/bash,
        password: 'staf',
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
        logger.debug('Push user: {}'.format(user))
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
    record = TaskRecord(name='Push user',
                        uuid=self.request.id,
                        date_start=timezone.now(),
                        assets=','.join(asset['hostname'] for asset in assets))
    record.save()
    logger.info('Runner start {0}'.format(timezone.now()))
    hoc = AdHocRunner(assets)
    _ = hoc.run(task_tuple)
    logger.info('Runner complete {0}'.format(timezone.now()))
    result_clean = hoc.clean_result()
    record.date_finished = timezone.now()
    record.is_finished = True

    if len(result_clean['failed']) == 0:
        record.is_success = True
    else:
        record.is_success = False
    record.result = result_clean
    record.save()
    return result_clean
