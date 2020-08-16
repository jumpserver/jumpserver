from django.utils.crypto import get_random_string
from perms.utils import run_user_mapping_node_task

from common.thread_pools import SingletonThreadPoolExecutor
from common.utils import get_logger
from perms.models import RebuildUserTreeTask

logger = get_logger(__name__)


class Executor(SingletonThreadPoolExecutor):
    pass


executor = Executor()


def run_mapping_node_tasks():
    failed_user_ids = []

    ident = get_random_string()
    logger.debug(f'[{ident}]mapping_node_tasks running')

    while True:
        task = RebuildUserTreeTask.objects.exclude(
            user_id__in=failed_user_ids
        ).first()

        if task is None:
            break

        user = task.user
        try:
            run_user_mapping_node_task(user)
        except:
            logger.exception(f'[{ident}]mapping_node_tasks_exception')
            failed_user_ids.append(user.id)

    logger.debug(f'[{ident}]mapping_node_tasks finished')


def submit_update_mapping_node_task():
    executor.submit(run_mapping_node_tasks)


def submit_update_mapping_node_task_for_user(user):
    executor.submit(run_user_mapping_node_task, user)
