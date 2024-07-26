from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField, JSONManyToManyField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from orgs.models import Organization
from orgs.utils import get_current_org_id
from tickets.const import TicketType
from tickets.models import TicketFlow, ApprovalRule

__all__ = ['TicketFlowSerializer']


class TicketFlowApproveSerializer(serializers.ModelSerializer):
    users = JSONManyToManyField(label=_('User'))

    class Meta:
        model = ApprovalRule
        fields = ['level', 'users']
        read_only_fields = ['level']


class TicketFlowSerializer(OrgResourceModelSerializerMixin):
    type = LabeledChoiceField(
        choices=TicketType.choices, required=True, label=_('Type')
    )
    rules = TicketFlowApproveSerializer(many=True, required=True)

    class Meta:
        model = TicketFlow
        fields_mini = ['id', 'type']
        fields_small = fields_mini + [
            'approval_level', 'created_by', 'date_created',
            'date_updated', 'org_id', 'org_name'
        ]
        fields = fields_small + ['rules']
        read_only_fields = ['created_by', 'date_created', 'date_updated']
        extra_kwargs = {
            'approval_level': {'required': True}
        }

    def validate_type(self, value):
        if not self.instance or (self.instance and self.instance.type != value):
            if self.Meta.model.objects.filter(type=value).exists():
                error = _('The current organization type already exists')
                raise serializers.ValidationError(error)
        return value

    def create_or_update(self, action, validated_data, instance=None):
        children = validated_data.pop('rules', [])
        if instance is None:
            instance = getattr(super(), action)(validated_data)
        else:
            instance = getattr(super(), action)(instance, validated_data)
            instance.rules.all().delete()

        child_instances = [
            instance.rules.model.objects.create(**data, level=level)
            for level, data in enumerate(children, 1)
        ]
        instance.rules.set(child_instances)
        return instance

    def create(self, validated_data):
        return self.create_or_update('create', validated_data)

    def update(self, instance, validated_data):
        current_org_id = get_current_org_id()
        root_org_id = Organization.ROOT_ID
        if instance.org_id == root_org_id and current_org_id != root_org_id:
            instance = self.create(validated_data)
        else:
            instance = self.create_or_update('update', validated_data, instance)
        return instance
