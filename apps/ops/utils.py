# ~*~ coding: utf-8 ~*~
import os
import uuid

from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, get_object_or_none, make_dirs
from orgs.utils import org_aware_func
from jumpserver.const import PROJECT_DIR

from .models import AdHoc, CeleryTask
from .const import DEFAULT_PASSWORD_RULES

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

