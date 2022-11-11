from django.conf import settings


def get_ansible_task_log_path(task_id):
    from ops.utils import get_task_log_path
    return get_task_log_path(settings.CELERY_LOG_DIR, task_id, level=2)
