# coding: utf-8
from celery import shared_task, subtask

from common.utils import get_logger, get_object_or_none
from .models import Task

logger = get_logger(__file__)


def rerun_task():
    pass


@shared_task
def run_ansible_task(task_id, callback=None, **kwargs):
    """
    :param task_id: is the tasks serialized data
    :param callback: callback function name
    :return:
    """

    task = get_object_or_none(Task, id=task_id)
    if task:
        result = task.run()
        if callback is not None:
            subtask(callback).delay(result, task_name=task.name)
        return result
    else:
        logger.error("No task found")


@shared_task
def hello(name, callback=None):
    print("Hello {}".format(name))
    if callback is not None:
        subtask(callback).delay("Guahongwei")


@shared_task
def hello_callback(result):
    print(result)
    print("Hello callback")
