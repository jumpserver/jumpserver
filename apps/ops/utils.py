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


def run_AdHoc(task_tuple, assets,
              task_name='Ansible AdHoc runner',
              task_id=None, pattern='all', record=True):

    if not assets:
        logger.warning('Empty assets, runner cancel')
        return
    if isinstance(assets[0], Asset):
        assets = [asset._to_secret_json() for asset in assets]
    if task_id is None:
        task_id = str(uuid.uuid4())

    runner = AdHocRunner(assets)
    if record:
        from .models import TaskRecord
        if not TaskRecord.objects.filter(uuid=task_id):
            record = TaskRecord(uuid=task_id,
                                name=task_name,
                                assets=','.join(str(asset['id']) for asset in assets),
                                module_args=task_tuple,
                                pattern=pattern)
            record.save()
        else:
            record = TaskRecord.objects.get(uuid=task_id)
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


def rerun_AdHoc(task_id):
    from .models import TaskRecord
    record = TaskRecord.objects.get(uuid=task_id)
    assets = record.assets_json
    task_tuple = record.module_args
    pattern = record.pattern
    task_name = record.name
    return run_AdHoc(task_tuple, assets, pattern=pattern,
                     task_name=task_name, task_id=task_id)







