from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Asset, Node, BaseAutomation, AutomationExecution
from common.const.choices import Trigger, Status
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.utils import get_logger
from ops.mixin import PeriodTaskSerializerMixin
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

logger = get_logger(__file__)

__all__ = [
    'BaseAutomationSerializer', 'AutomationExecutionSerializer',
    'UpdateAssetSerializer', 'UpdateNodeSerializer', 'AutomationAssetsSerializer',
]


class BaseAutomationSerializer(PeriodTaskSerializerMixin, BulkOrgResourceModelSerializer):
    assets = ObjectRelatedField(many=True, required=False, queryset=Asset.objects, label=_('Assets'))
    nodes = ObjectRelatedField(many=True, required=False, queryset=Node.objects, label=_('Nodes'))

    class Meta:
        read_only_fields = [
            'date_created', 'date_updated', 'created_by',
            'periodic_display', 'executed_amount', 'type'
        ]
        mini_fields = [
            'id', 'name', 'type', 'is_periodic', 'interval',
            'crontab', 'comment', 'is_active'
        ]
        fields = mini_fields + [
            'accounts', 'nodes', 'assets',
        ] + read_only_fields
        extra_kwargs = {
            'name': {'required': True},
            'type': {'read_only': True},
            'executed_amount': {'label': _('Executions')},
        }


class AutomationExecutionSerializer(serializers.ModelSerializer):
    snapshot = serializers.SerializerMethodField(label=_('Automation snapshot'))
    trigger = LabeledChoiceField(choices=Trigger.choices, read_only=True, label=_("Trigger mode"))
    status = LabeledChoiceField(choices=Status.choices, read_only=True, label=_('Status'))
    short_id = serializers.CharField(read_only=True, label=_('Short ID'))

    class Meta:
        model = AutomationExecution
        read_only_fields = [
            'trigger', 'date_start', 'date_finished',
            'snapshot', 'status', 'duration'
        ]
        fields = ['id', 'short_id', 'automation'] + read_only_fields

    @staticmethod
    def get_snapshot(obj):
        from assets.const import AutomationTypes as AssetTypes
        from accounts.const import AutomationTypes as AccountTypes
        tp_dict = dict(AssetTypes.choices) | dict(AccountTypes.choices)
        tp = obj.snapshot.get('type', '')
        snapshot = {
            'type': {'value': tp, 'label': tp_dict.get(tp, tp)},
            'name': obj.snapshot.get('name'),
            'comment': obj.snapshot.get('comment'),
            'accounts': obj.snapshot.get('accounts'),
            'node_amount': len(obj.snapshot.get('nodes', [])),
            'asset_amount': len(obj.snapshot.get('assets', [])),
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
