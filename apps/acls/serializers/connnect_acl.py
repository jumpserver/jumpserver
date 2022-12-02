from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.drf.serializers import BulkModelSerializer
from common.const.choices import ConnectMethodChoices
from ..models import ConnectACL


__all__ = ['ConnectACLSerializer', ]


class ConnectACLSerializer(BulkModelSerializer):
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_('Action'))

    class Meta:
        model = ConnectACL
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'priority', 'rules', 'rules_display', 'action', 'action_display', 'is_active',
            'date_created', 'date_updated', 'comment', 'created_by'
        ]
        fields_m2m = ['users', 'user_groups']
        fields = fields_small + fields_m2m
        extra_kwargs = {
            'priority': {'default': 50},
            'is_active': {'default': True}
        }

    @staticmethod
    def validate_rules(rules):
        for r in rules:
            label = ConnectMethodChoices.get_label(r)
            if not label:
                error = _('Invalid connection method: {}').format(r)
                raise serializers.ValidationError(error)
        return rules
