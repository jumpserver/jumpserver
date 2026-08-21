from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
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
    不返回 assets/nodes 大数组和 recipients,避免列表 payload 膨胀。
    明细(retrieve)仍使用完整序列化器返回相关字段。
    子类 Meta 需声明 relation_count_fields 并把数量字段放进 fields。
    """
    assets_amount = serializers.IntegerField(read_only=True, label=_('Assets amount'))
    nodes_amount = serializers.IntegerField(read_only=True, label=_('Nodes amount'))
    executed_amount = serializers.IntegerField(
        source='_executed_amount', read_only=True, label=_('Executed amount')
    )

    @classmethod
    def setup_eager_loading(cls, queryset):
        relation = queryset.model._meta.get_field('executions')
        execution_model = relation.related_model
        automation_field = relation.field.attname
        executed_amount = (
            execution_model._base_manager
            .filter(**{automation_field: OuterRef('pk')})
            .order_by()
            .values(automation_field)
            .annotate(amount=Count('*'))
            .values('amount')[:1]
        )
        return queryset.annotate(
            _executed_amount=Coalesce(
                Subquery(executed_amount, output_field=IntegerField()),
                0,
            )
        )


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
