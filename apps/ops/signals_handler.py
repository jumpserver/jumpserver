from django.utils import translation
from django.core.cache import cache
from celery.signals import task_prerun, task_postrun, before_task_publish

from common.db.utils import close_old_connections


TASK_LANG_CACHE_KEY = 'TASK_LANG_{}'
TASK_LANG_CACHE_TTL = 1800


@before_task_publish.connect()
def before_task_publish(headers=None, **kwargs):
    task_id = headers.get('id')
    current_lang = translation.get_language()
    key = TASK_LANG_CACHE_KEY.format(task_id)
    cache.set(key, current_lang, 1800)


@task_prerun.connect()
def on_celery_task_pre_run(task_id='', **kwargs):
    # 关闭之前的数据库连接
    close_old_connections()

    # 保存 Lang context
    key = TASK_LANG_CACHE_KEY.format(task_id)
    task_lang = cache.get(key)
    if task_lang:
        translation.activate(task_lang)


@task_postrun.connect()
def on_celery_task_post_run(**kwargs):
    close_old_connections()
