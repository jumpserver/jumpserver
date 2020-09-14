# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals

import time

from celery import shared_task
from common.utils import get_logger
from perms.utils.user_node_tree import build_user_mapping_node_with_lock

logger = get_logger(__file__)


@shared_task()
def build_users_perm_tree_celery_task():
    from users.models import User
    users = User.objects.all()
    users_amount = users.count()
    width = len(str(users_amount))

    for i, user in enumerate(users):
        try:
            logger.info(f'{i:0>{width}}/{users_amount} build_mapping_nodes for {user} begin')
            t1 = time.time()
            build_user_mapping_node_with_lock(user)
            t2 = time.time()
            logger.info(f'{i:0>{width}}/{users_amount} build_mapping_nodes for {user} finish cost {t2-t1}s')
        except:
            continue
