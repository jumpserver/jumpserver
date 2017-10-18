# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals

import json
import time
import uuid

from django.utils import timezone

from assets.models import Asset
from common.utils import get_logger
from .ansible.runner import AdHocRunner

logger = get_logger(__file__)


def local_AdHoc(task_tuple, task_name='Ansible AdHoc runner',
                pattern='all', verbose=True):
    """
    执行本地任务  不记录日志  不与Asset绑定
    :param task_tuple:  (('module_name', 'module_args'), ('module_name', 'module_args'))
    :param assets: [asset1, asset2]
    :param task_name:
    :param pattern:
    :param verbose:
    :return: summary: {'success': [], 'failed': [{'192.168.1.1': 'msg'}]}
             result: {'contacted': {'hostname': [{''}, {''}], 'dark': []}
    """
    runner = AdHocRunner()

    if verbose:
        logger.debug('Start runner {}'.format(task_name))
    result = runner.run(task_tuple, pattern=pattern, task_name=task_name)
    summary = runner.clean_result()

    return summary, result
