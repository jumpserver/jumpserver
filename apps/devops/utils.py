# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals

import json
import yaml
import time
import uuid

from django.utils import timezone

from assets.models import Asset
from common.utils import get_logger
from .ansible.runner import AdHocRunner, PlayBookRunner

logger = get_logger(__file__)


def run_AdHoc(task_tuple, assets=None,
              task_name='Ansible AdHoc runner',
              task_id=None, pattern='all',
              record=False, verbose=True):
    """
    改造为不输入assets时为本地执行
    :param task_tuple:  (('module_name', 'module_args'), ('module_name', 'module_args'))
    :param assets: [asset1, asset2]
    :param task_name:
    :param task_id:
    :param pattern:
    :param record:
    :param verbose:
    :return: summary: {'success': [], 'failed': [{'192.168.1.1': 'msg'}]}
             result: {'contacted': {'hostname': [{''}, {''}], 'dark': []}
    """
    if not assets:
        runner = AdHocRunner()
    else:
        runner = AdHocRunner(assets)
        if isinstance(assets[0], Asset):
            assets = [asset._to_secret_json() for asset in assets]
    if task_id is None:
        task_id = str(uuid.uuid4())

    if record:
        from ops.models import Task
        if not Task.objects.filter(uuid=task_id):
            record = Task(uuid=task_id,
                          name=task_name,
                          assets='localhost' if not assets else ','.join(str(asset['id']) for asset in assets),
                          module_args=task_tuple,
                          pattern=pattern)
            record.save()
        else:
            record = Task.objects.get(uuid=task_id)
            record.date_start = timezone.now()
            record.date_finished = None
            record.timedelta = None
            record.is_finished = False
            record.is_success = False
            record.save()
    ts_start = time.time()
    if verbose:
        logger.debug('Start runner {}'.format(task_name))
    result = runner.run(task_tuple, pattern=pattern, task_name=task_name)
    timedelta = round(time.time() - ts_start, 2)
    summary = runner.clean_result()
    if record:
        record.date_finished = timezone.now()
        record.is_finished = True
        if verbose:
            record.result = json.dumps(result, indent=4, sort_keys=True)
        record.summary = json.dumps(summary)
        record.timedelta = timedelta
        if len(summary['failed']) == 0:
            record.is_success = True
        else:
            record.is_success = False
        record.save()
    return summary, result


def run_playbook(playbook_path, assets, system_user=None, task_name='Ansible PlayBook Runner',
                 tags=None, record=True, verbose=True):
    """
    改造为不输入assets时为本地执行
    :param task_name:
    :param system_user: become system user
    :param playbook_path:  ../task_id.yml
    :param assets: [{asset1}, {asset2}]
    :param tags: [tagA,tagB]
    :param record:
    :param verbose:
    :return: summary: {'success': [], 'failed': [{'192.168.1.1': 'msg'}]}
             result: {'contacted': {'hostname': [{''}, {''}], 'dark': []}
    """
    print(system_user)
    runner = PlayBookRunner(assets, playbook_path=playbook_path, tags=tags)

    task_id = str(uuid.uuid4())

    if record:
        from ops.models import Task
        if not Task.objects.filter(uuid=task_id):
            with open(playbook_path) as f:
                playbook_json = yaml.load(f)
            record = Task(uuid=task_id,
                          name=task_name,
                          assets='localhost' if not assets else ','.join(str(asset['id']) for asset in assets),
                          module_args=[('playbook', playbook_json)])
            record.save()
        else:
            record = Task.objects.get(uuid=task_id)
            record.date_start = timezone.now()
            record.date_finished = None
            record.timedelta = None
            record.is_finished = False
            record.is_success = False
            record.save()
    ts_start = time.time()
    # if verbose:
    #     logger.debug('Start runner {}'.format(task_name))
    result = runner.run()
    # timedelta = round(time.time() - ts_start, 2)
    summary = runner.clean_result()
    # if record:
    #     record.date_finished = timezone.now()
    #     record.is_finished = True
    #     if verbose:
    #         record.result = json.dumps(result, indent=4, sort_keys=True)
    #     record.summary = json.dumps(summary)
    #     record.timedelta = timedelta
    #     if len(summary['failed']) == 0:
    #         record.is_success = True
    #     else:
    #         record.is_success = False
    #     record.save()
    return summary, result
