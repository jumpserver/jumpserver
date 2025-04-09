import os
import uuid

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import Asset
from common.permissions import IsValidUser
from ops.models.job import JMSPermedInventory

__all__ = ['InventoryClassifiedHostsAPI']


class InventoryClassifiedHostsAPI(APIView):
    permission_classes = [IsValidUser]

    def post(self, request, **kwargs):
        asset_ids = request.data.get('assets', [])
        node_ids = request.data.get('nodes', [])
        runas_policy = request.data.get('runas_policy', 'privileged_first')
        account_prefer = request.data.get('runas', 'root,Administrator')
        module = request.data.get('module', 'shell')
        # 合并节点和资产
        assets = list(Asset.objects.filter(id__in=asset_ids).all())

        # 创建临时目录
        tmp_dir = os.path.join(settings.PROJECT_DIR, 'inventory', str(uuid.uuid4()))
        os.makedirs(tmp_dir, exist_ok=True)

        # 创建库存对象并获取分类的主机
        inventory = JMSPermedInventory(
            assets=assets,
            nodes=node_ids,
            module=module,
            account_policy=runas_policy,
            account_prefer=account_prefer,
            user=self.request.user
        )
        classified_hosts = inventory.get_classified_hosts(tmp_dir)

        return Response(data=classified_hosts)
