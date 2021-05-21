from django.db.transaction import on_commit
from orgs.models import Organization
from orgs.tasks import refresh_org_cache_task
from orgs.utils import current_org, tmp_to_org

from common.cache import Cache, IntegerField
from common.utils import get_logger
from users.models import UserGroup, User
from assets.models import Node, AdminUser, SystemUser, Domain, Gateway, Asset
from terminal.models import Session
from applications.models import Application
from perms.models import AssetPermission, ApplicationPermission
from .models import OrganizationMember

logger = get_logger(__file__)


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

    def compute_values(self, *fields):
        with tmp_to_org(self.get_current_org()):
            return super().compute_values(*fields)

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


class OrgResourceStatisticsCache(OrgRelatedCache):
    users_amount = IntegerField()
    groups_amount = IntegerField(queryset=UserGroup.objects)

    assets_amount = IntegerField()
    nodes_amount = IntegerField(queryset=Node.objects)
    admin_users_amount = IntegerField(queryset=AdminUser.objects)
    system_users_amount = IntegerField(queryset=SystemUser.objects)
    domains_amount = IntegerField(queryset=Domain.objects)
    gateways_amount = IntegerField(queryset=Gateway.objects)

    applications_amount = IntegerField(queryset=Application.objects)

    asset_perms_amount = IntegerField(queryset=AssetPermission.objects)
    app_perms_amount = IntegerField(queryset=ApplicationPermission.objects)

    total_count_online_users = IntegerField()
    total_count_online_sessions = IntegerField()

    def __init__(self, org):
        super().__init__()
        self.org = org

    def get_key_suffix(self):
        return f'<org:{self.org.id}>'

    def get_current_org(self):
        return self.org

    def compute_users_amount(self):
        users = User.objects.exclude(role='App')

        if not self.org.is_root():
            users = users.filter(m2m_org_members__org_id=self.org.id)

        users_amount = users.values('id').distinct().count()
        return users_amount

    def compute_assets_amount(self):
        if self.org.is_root():
            return Asset.objects.all().count()
        node = Node.org_root()
        return node.assets_amount

    def compute_total_count_online_users(self):
        return len(set(Session.objects.filter(is_finished=False).values_list('user_id', flat=True)))

    def compute_total_count_online_sessions(self):
        return Session.objects.filter(is_finished=False).count()
