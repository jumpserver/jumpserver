from django.utils.translation import ugettext as _
from rest_framework import serializers

from ops.mixin import PeriodTaskSerializerMixin
from assets.const import AutomationTypes
from assets.models import Asset, BaseAutomation, AutomationExecution
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.utils import get_logger

logger = get_logger(__file__)

__all__ = [
    'BaseAutomationSerializer', 'AutomationExecutionSerializer',
    'UpdateAssetSerializer', 'UpdateNodeSerializer', 'AutomationAssetsSerializer',
]


class BaseAutomationSerializer(PeriodTaskSerializerMixin, BulkOrgResourceModelSerializer):
    class Meta:
        read_only_fields = [
            'date_created', 'date_updated', 'created_by', 'periodic_display'
        ]
        fields = read_only_fields + [
            'id', 'name', 'is_periodic', 'interval', 'crontab', 'comment',
            'type', 'accounts', 'nodes', 'assets', 'is_active'
        ]
        extra_kwargs = {
            'name': {'required': True},
            'periodic_display': {'label': _('Periodic perform')},
        }


class AutomationExecutionSerializer(serializers.ModelSerializer):
    snapshot = serializers.SerializerMethodField(label=_('Automation snapshot'))
    type = serializers.ChoiceField(choices=AutomationTypes.choices, write_only=True, label=_('Type'))
    trigger_display = serializers.ReadOnlyField(source='get_trigger_display', label=_('Trigger mode'))

    class Meta:
        model = AutomationExecution
        fields = [
            'id', 'automation', 'trigger', 'trigger_display',
            'date_start', 'date_finished', 'snapshot', 'type'
        ]

    @staticmethod
    def get_snapshot(obj):
        tp = obj.snapshot['type']
        snapshot = {
            'type': tp,
            'name': obj.snapshot['name'],
            'comment': obj.snapshot['comment'],
            'accounts': obj.snapshot['accounts'],
            'node_amount': len(obj.snapshot['nodes']),
            'asset_amount': len(obj.snapshot['assets']),
            'type_display': getattr(AutomationTypes, tp).label,
        }
        return snapshot


class UpdateAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseAutomation
        fields = ['id', 'assets']


class UpdateNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseAutomation
        fields = ['id', 'nodes']


class AutomationAssetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        only_fields = ['id', 'name', 'address']
        fields = tuple(only_fields)
