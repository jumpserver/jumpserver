# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from common.utils import get_logger
from users.models import User
from perms.models import RebuildUserTreeTask
from perms.utils.user_node_tree import rebuild_user_mapping_nodes_if_need_with_lock

logger = get_logger(__file__)


@shared_task(queue='node_tree')
def rebuild_user_mapping_nodes_celery_task(user_id):
    logger.info(f'rebuild user[{user_id}] mapping nodes')
    user = User.objects.get(id=user_id)
    rebuild_user_mapping_nodes_if_need_with_lock(user)


@shared_task(queue='node_tree')
def dispatch_mapping_node_tasks():
    user_ids = RebuildUserTreeTask.objects.all().values_list('user_id', flat=True).distinct()
    for id in user_ids:
        logger.info(f'dispatch mapping node task for user[{id}]')
        rebuild_user_mapping_nodes_celery_task.delay(id)
