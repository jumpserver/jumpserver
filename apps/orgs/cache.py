from django.db.transaction import on_commit

from common.cache import *
from .utils import current_org, tmp_to_org
from .tasks import refresh_org_cache_task
from orgs.models import Organization


class OrgRelatedCache(Cache):

    def __init__(self):
        super().__init__()
        self.current_org = Organization.get_instance(current_org.id)

    def get_current_org(self):
        """
        暴露给子类控制组织的回调
        1. 在交互式环境下能控制组织
        2. 在 celery 任务下能控制组织
        """
        return self.current_org

    def compute_data(self, *fields):
        with tmp_to_org(self.get_current_org()):
            return super().compute_data(*fields)

    def refresh_async(self, *fields):
        """
        在事务提交之后再发送信号，防止因事务的隔离性导致未获得最新的数据
        """
        def func():
            logger.info(f'CACHE: Send refresh task {self}.{fields}')
            refresh_org_cache_task.delay(self, *fields)
        on_commit(func)

    def expire(self, *fields):
        def func():
            super(OrgRelatedCache, self).expire(*fields)
        on_commit(func)
