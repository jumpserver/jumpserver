from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from orgs.models import Organization
from orgs.utils import get_current_org_id
from tickets.const import TicketApprovalStrategy, TicketType
from tickets.models import TicketFlow, ApprovalRule

__all__ = ['TicketFlowSerializer']


class TicketFlowApproveSerializer(serializers.ModelSerializer):
    strategy = LabeledChoiceField(
        choices=TicketApprovalStrategy.choices, required=True, label=_('Approve strategy')
    )
    assignees_read_only = serializers.SerializerMethodField(label=_('Assignees'))
    assignees_display = serializers.SerializerMethodField(label=_('Assignees display'))

    class Meta:
        model = ApprovalRule
        fields_small = [
            'level', 'strategy', 'assignees_read_only', 'assignees_display',
        ]
        fields_m2m = ['assignees', ]
        fields = fields_small + fields_m2m
        read_only_fields = ['level', 'assignees_display']
        extra_kwargs = {
            'assignees': {'write_only': True, 'allow_empty': True, 'required': False}
        }

    @staticmethod
    def get_assignees_display(instance):
        return [str(assignee) for assignee in instance.get_assignees()]

    @staticmethod
    def get_assignees_read_only(instance):
        if instance.strategy == TicketApprovalStrategy.custom_user:
            return instance.assignees.values_list('id', flat=True)
        return []

    def validate(self, attrs):
        if attrs['strategy'] == TicketApprovalStrategy.custom_user and not attrs.get('assignees'):
            error = _('Please select the Assignees')
            raise serializers.ValidationError({'assignees': error})
        return super().validate(attrs)


class TicketFlowSerializer(OrgResourceModelSerializerMixin):
    type = LabeledChoiceField(
        choices=TicketType.choices, required=True, label=_('Type')
    )
    rules = TicketFlowApproveSerializer(many=True, required=True)

    class Meta:
        model = TicketFlow
        fields_mini = ['id', ]
        fields_small = fields_mini + [
            'type', 'approval_level', 'created_by', 'date_created', 'date_updated',
            'org_id', 'org_name'
        ]
        fields = fields_small + ['rules', ]
        read_only_fields = ['created_by', 'org_id', 'date_created', 'date_updated']
        extra_kwargs = {
            'type': {'required': True},
            'approval_level': {'required': True}
        }

    def validate_type(self, value):
        if not self.instance or (self.instance and self.instance.type != value):
            if self.Meta.model.objects.filter(type=value).exists():
                error = _('The current organization type already exists')
                raise serializers.ValidationError(error)
        return value

    def create_or_update(self, action, validated_data, instance=None):
        related = 'rules'
        assignees = 'assignees'
        childs = validated_data.pop(related, [])
        if not instance:
            instance = getattr(super(), action)(validated_data)
        else:
            instance = getattr(super(), action)(instance, validated_data)
            getattr(instance, related).all().delete()
        instance_related = getattr(instance, related)
        child_instances = []
        related_model = instance_related.model
        # Todo: 这个权限的判断
        for level, data in enumerate(childs, 1):
            data_m2m = data.pop(assignees, None)
            child_instance = related_model.objects.create(**data, level=level)
            getattr(child_instance, assignees).set(data_m2m)
            child_instances.append(child_instance)
        instance_related.set(child_instances)
        return instance

    @atomic
    def create(self, validated_data):
        return self.create_or_update('create', validated_data)

    @atomic
    def update(self, instance, validated_data):
        current_org_id = get_current_org_id()
        root_org_id = Organization.ROOT_ID
        if instance.org_id == root_org_id and current_org_id != root_org_id:
            instance = self.create(validated_data)
        else:
            instance = self.create_or_update('update', validated_data, instance)
        return instance
