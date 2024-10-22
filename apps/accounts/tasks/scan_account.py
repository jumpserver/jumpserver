from celery import shared_task
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger

logger = get_logger(__file__)
__all__ = [
    'check_accounts_task',
]


@shared_task(
    queue="ansible",
    verbose_name=_('Scan accounts'),
    activity_callback=lambda self, node_ids, task_name=None, *args, **kwargs: (node_ids, None),
    description=_("Unused")
)
def check_accounts_task(node_ids, task_name=None):
    pass
