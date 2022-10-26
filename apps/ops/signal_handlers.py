import ast

from django.db import transaction
from django.dispatch import receiver
from django.utils import translation, timezone
from django.core.cache import cache
from celery import signals, current_app

from common.db.utils import close_old_connections, get_logger
from common.signals import django_ready
from .celery import app
from .models import CeleryTaskExecution, CeleryTask

logger = get_logger(__name__)

TASK_LANG_CACHE_KEY = 'TASK_LANG_{}'
TASK_LANG_CACHE_TTL = 1800


@receiver(django_ready)
def sync_registered_tasks(*args, **kwargs):
    with transaction.atomic():
        db_tasks = CeleryTask.objects.all()
        celery_task_names = [key for key in app.tasks]
        db_task_names = [task.name for task in db_tasks]

        for task in db_tasks:
            if task.name not in celery_task_names:
                task.delete()
        for task in celery_task_names:
            if task not in db_task_names:
                CeleryTask(name=task).save()


@signals.before_task_publish.connect
def before_task_publish(headers=None, **kwargs):
    task_id = headers.get('id')
    current_lang = translation.get_language()
    key = TASK_LANG_CACHE_KEY.format(task_id)
    cache.set(key, current_lang, 1800)


@signals.task_prerun.connect
def on_celery_task_pre_run(task_id='', **kwargs):
    # 更新状态
    CeleryTaskExecution.objects.filter(id=task_id).update(state='RUNNING', date_start=timezone.now())
    # 关闭之前的数据库连接
    close_old_connections()

    # 保存 Lang context
    key = TASK_LANG_CACHE_KEY.format(task_id)
    task_lang = cache.get(key)
    if task_lang:
        translation.activate(task_lang)


@signals.task_postrun.connect
def on_celery_task_post_run(task_id='', state='', **kwargs):
    close_old_connections()
    print("Task post run: ", task_id, state)

    CeleryTaskExecution.objects.filter(id=task_id).update(
        state=state, date_finished=timezone.now(), is_finished=True
    )


@signals.after_task_publish.connect
def task_sent_handler(headers=None, body=None, **kwargs):
    info = headers if 'task' in headers else body
    task = info.get('task')
    i = info.get('id')
    if not i or not task:
        logger.error("Not found task id or name: {}".format(info))
        return

    args = info.get('argsrepr', '()')
    kwargs = info.get('kwargsrepr', '{}')
    try:
        args = list(ast.literal_eval(args))
        kwargs = ast.literal_eval(kwargs)
    except (ValueError, SyntaxError):
        args = []
        kwargs = {}

    data = {
        'id': i,
        'name': task,
        'state': 'PENDING',
        'is_finished': False,
        'args': args,
        'kwargs': kwargs
    }
    CeleryTaskExecution.objects.create(**data)
