import ast
import time

from celery import signals
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import pre_save
from django.db.utils import ProgrammingError
from django.dispatch import receiver
from django.utils import translation, timezone

from common.db.utils import close_old_connections, get_logger
from common.signals import django_ready
from orgs.utils import get_current_org_id, set_current_org
from .celery import app
from .models import CeleryTaskExecution, CeleryTask, Job

logger = get_logger(__name__)


@receiver(pre_save, sender=Job)
def on_account_pre_create(sender, instance, **kwargs):
    # 升级版本号
    instance.version += 1


@receiver(signals.worker_ready)
def sync_registered_tasks(*args, **kwargs):
    synced = cache.get('synced_registered_tasks', False)
    if synced:
        return
    cache.set('synced_registered_tasks', True, 60)
    with transaction.atomic():
        try:
            db_tasks = CeleryTask.objects.all()
            celery_task_names = [key for key in app.tasks]
            db_task_names = db_tasks.values_list('name', flat=True)

            db_tasks.exclude(name__in=celery_task_names).delete()
            not_in_db_tasks = set(celery_task_names) - set(db_task_names)
            tasks_to_create = [CeleryTask(name=name) for name in not_in_db_tasks]
            CeleryTask.objects.bulk_create(tasks_to_create)
        except ProgrammingError:
            pass


@receiver(django_ready)
def check_registered_tasks(*args, **kwargs):
    attrs = ['verbose_name', 'activity_callback']
    ignores = [
        'users.tasks.check_user_expired_periodic', 'ops.tasks.clean_celery_periodic_tasks',
        'terminal.tasks.delete_terminal_status_period', 'ops.tasks.check_server_performance_period',
        'settings.tasks.ldap.import_ldap_user', 'users.tasks.check_password_expired',
        'assets.tasks.nodes_amount.check_node_assets_amount_task', 'notifications.notifications.publish_task',
        'perms.tasks.check_asset_permission_will_expired',
        'ops.tasks.create_or_update_registered_periodic_tasks', 'perms.tasks.check_asset_permission_expired',
        'settings.tasks.ldap.import_ldap_user_periodic', 'users.tasks.check_password_expired_periodic',
        'common.utils.verify_code.send_async', 'assets.tasks.nodes_amount.check_node_assets_amount_period_task',
        'users.tasks.check_user_expired', 'orgs.tasks.refresh_org_cache_task',
        'terminal.tasks.upload_session_replay_to_external_storage', 'terminal.tasks.clean_orphan_session',
        'audits.tasks.clean_audits_log_period', 'authentication.tasks.clean_django_sessions'
    ]

    for name, task in app.tasks.items():
        if name.startswith('celery.'):
            continue
        if name in ignores:
            continue
        for attr in attrs:
            if not hasattr(task, attr):
                # print('>>> Task {} has no attribute {}'.format(name, attr))
                pass


@signals.before_task_publish.connect
def before_task_publish(body=None, **kwargs):
    current_lang = translation.get_language()
    current_org_id = get_current_org_id()
    args, kwargs = body[:2]
    kwargs['__current_lang'] = current_lang
    kwargs['__current_org_id'] = current_org_id


@signals.task_prerun.connect
def on_celery_task_pre_run(task_id='', kwargs=None, **others):
    count = 0
    qs = CeleryTaskExecution.objects.filter(id=task_id)
    while not qs.exists() and count < 5:
        count += 1
        time.sleep(1)
        qs = CeleryTaskExecution.objects.filter(id=task_id)

    # 更新状态
    qs.update(state='RUNNING', date_start=timezone.now())

    # 关闭之前的数据库连接
    close_old_connections()

    # 设置语言的一些上下文
    lang = kwargs.pop('__current_lang', None)
    org_id = kwargs.pop('__current_org_id', None)
    if lang:
        print('>> Set language to {}'.format(lang))
        translation.activate(lang)
    if org_id:
        print('>> Set org to {}'.format(org_id))
        set_current_org(org_id)


@signals.task_postrun.connect
def on_celery_task_post_run(task_id='', state='', **kwargs):
    close_old_connections()

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
    CeleryTask.objects.filter(name=task).update(date_last_publish=timezone.now())
