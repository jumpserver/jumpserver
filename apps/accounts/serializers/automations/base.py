from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import AutomationExecution
from assets.const import AutomationTypes
from assets.models import Asset, Node, BaseAutomation
from common.const.choices import Trigger
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
            'date_created', 'date_updated', 'created_by', 'periodic_display', 'executed_amount'
        ]
        fields = read_only_fields + [
            'id', 'name', 'is_periodic', 'interval', 'crontab', 'comment',
            'type', 'accounts', 'nodes', 'assets', 'is_active',
        ]
        extra_kwargs = {
            'name': {'required': True},
            'type': {'read_only': True},
            'periodic_display': {'label': _('Periodic perform')},
            'executed_amount': {'label': _('Executed amount')},
        }

    def validate_name(self, name):
        if self.instance and self.instance.name == name:
            return name
        if BaseAutomation.objects.filter(name=name, type=self.model_type).exists():
            raise serializers.ValidationError(_('Name already exists'))
        return name

    @property
    def model_type(self):
        raise NotImplementedError


class AutomationExecutionSerializer(serializers.ModelSerializer):
    snapshot = serializers.SerializerMethodField(label=_('Automation snapshot'))
    type = serializers.ChoiceField(choices=AutomationTypes.choices, write_only=True, label=_('Type'))
    trigger = LabeledChoiceField(choices=Trigger.choices, read_only=True, label=_("Trigger mode"))

    class Meta:
        model = AutomationExecution
        read_only_fields = [
            'trigger', 'date_start', 'date_finished', 'snapshot', 'status'
        ]
        fields = ['id', 'automation', 'type'] + read_only_fields

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
