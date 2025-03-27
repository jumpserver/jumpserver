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
