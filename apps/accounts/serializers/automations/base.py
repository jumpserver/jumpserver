from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.const import AutomationTypes
from assets.models import BaseAutomation
from assets.serializers.automations import AutomationExecutionSerializer as AssetAutomationExecutionSerializer
from assets.serializers.automations import BaseAutomationSerializer as AssetBaseAutomationSerializer
from common.utils import get_logger

logger = get_logger(__file__)

__all__ = [
    'BaseAutomationSerializer', 'AutomationExecutionSerializer',
    'AutomationListSerializerMixin',
]


class BaseAutomationSerializer(AssetBaseAutomationSerializer):
    def validate_name(self, name):
        if self.instance and self.instance.name == name:
            return name
        if BaseAutomation.objects.filter(name=name, type=self.model_type).exists():
            raise serializers.ValidationError(_('Name already exists'))
        return name

    @property
    def model_type(self):
        raise NotImplementedError


class AutomationListSerializerMixin(serializers.Serializer):
    """
    列表页用:只返回 assets/nodes 的数量(由 RelationCountMixin 批量 annotate),
    不返回 assets/nodes 大数组,避免任务绑定海量资产/节点时列表 payload 膨胀、前端卡顿。
    明细(retrieve)仍用完整序列化器返回数组,供 hover 懒加载。
    子类 Meta 需声明 relation_count_fields 并把这两个字段放进 fields、剔除 assets/nodes。
    """
    assets_amount = serializers.IntegerField(read_only=True, label=_('Assets amount'))
    nodes_amount = serializers.IntegerField(read_only=True, label=_('Nodes amount'))

    @classmethod
    def setup_eager_loading(cls, queryset):
        # 列表不预加载 assets/nodes 的 m2m,只需计数
        return queryset


class AutomationExecutionSerializer(AssetAutomationExecutionSerializer):
    snapshot = serializers.SerializerMethodField(label=_('Automation snapshot'))

    @staticmethod
    def get_snapshot(obj):
        tp = obj.snapshot.get('type', '')
        type_display = tp if not hasattr(AutomationTypes, tp) \
            else getattr(AutomationTypes, tp).label
        snapshot = {
            'type': tp,
            'name': obj.snapshot.get('name'),
            'comment': obj.snapshot.get('comment'),
            'accounts': obj.snapshot.get('accounts'),
            'node_amount': len(obj.snapshot.get('nodes', [])),
            'asset_amount': len(obj.snapshot.get('assets', [])),
            'type_display': type_display,
        }
        return snapshot
