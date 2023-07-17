# ~*~ coding: utf-8 ~*~
import os
import uuid
from django.conf import settings

from common.utils import get_logger, make_dirs
from jumpserver.const import PROJECT_DIR

logger = get_logger(__file__)


def get_task_log_path(base_path, task_id, level=2):
    task_id = str(task_id)
    try:
        uuid.UUID(task_id)
    except:
        return os.path.join(PROJECT_DIR, 'data', 'caution.txt')

    rel_path = os.path.join(*task_id[:level], task_id + '.log')
    path = os.path.join(base_path, rel_path)
    make_dirs(os.path.dirname(path), exist_ok=True)
    return path


def get_ansible_log_verbosity(verbosity=0):
    if settings.DEBUG_ANSIBLE:
        return 10
    if verbosity is None and settings.DEBUG:
        return 1
    return verbosity

