# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from common.utils import get_logger, encrypt_password
from ops.utils import run_AdHoc

logger = get_logger(__file__)


@shared_task(bind=True)
def push_users(self, assets, users):
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
             "dest=/etc/sudoers state=present regexp='^{0} ALL=' "
             "line='{0} ALL=(ALL) NOPASSWD: {1}' "
             "validate='visudo -cf %s'".format(
                 user['username'], user.get('sudo', '/sbin/ifconfig')
             ))
        ])
    task_name = 'Push user {}'.format(','.join([user['name'] for user in users]))
    task = run_AdHoc(task_tuple, assets, pattern='all',
                     task_name=task_name, task_id=self.request.id)
    return task

