from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField, JSONManyToManyField, ObjectRelatedField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from orgs.models import Organization
from orgs.utils import get_current_org_id
from tickets.const import TicketLevel, TicketType
from tickets.models import TicketFlow, ApprovalRule
from users.models import User

__all__ = ['TicketFlowSerializer', 'TicketFlowOptionSerializer']


class TicketFlowApproveSerializer(serializers.ModelSerializer):
    users = JSONManyToManyField(label=_('User'))

    class Meta:
        model = ApprovalRule
        fields = ['level', 'users']
        read_only_fields = ['level']

    def validate_users(self, value):
        rule = ApprovalRule()
        rule.users.set(value)
        assignees = rule.get_assignees(org_id=get_current_org_id())
        if not assignees.exists():
            error = _('No approvers matched. Please update the approval rule')
            raise serializers.ValidationError(error)
        return value


class TicketFlowSerializer(OrgResourceModelSerializerMixin):
    name = serializers.CharField(
        required=True, allow_blank=False, max_length=128, label=_('Name')
    )
    type = LabeledChoiceField(
        choices=TicketType.choices, read_only=True, label=_('Type')
    )
    rules = TicketFlowApproveSerializer(many=True, required=True)
    cc_users = ObjectRelatedField(
        queryset=User.objects, many=True, required=False,
        attrs=('id', 'name', 'username'), label=_('CC users')
    )

    class Meta:
        model = TicketFlow
        fields_mini = ['id', 'name', 'type']
        fields_small = fields_mini + [
            'approval_level', 'created_by', 'date_created',
            'date_updated', 'org_id', 'org_name'
        ]
        fields = fields_small + ['rules', 'cc_users']
        read_only_fields = ['created_by', 'date_created', 'date_updated']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        name = attrs.get('name', getattr(self.instance, 'name', ''))
        ticket_type = attrs.get(
            'type', getattr(self.instance, 'type', TicketType.apply_asset)
        )
        current_org_id = str(get_current_org_id())
        flows = TicketFlow.objects.filter(
            org_id=current_org_id, name__iexact=name, type=ticket_type
        )
        if self.instance and self.instance.org_id == current_org_id:
            flows = flows.exclude(id=self.instance.id)
        if flows.exists():
            error = _('A ticket flow with the same name and type already exists')
            raise serializers.ValidationError({'name': error})

        approval_level = attrs.get(
            'approval_level', getattr(self.instance, 'approval_level', TicketLevel.one)
        )
        rules = attrs.get('rules')
        if rules is not None and len(rules) != approval_level:
            error = _('The number of approval rules must match the approval level')
            raise serializers.ValidationError({'rules': error})
        return attrs

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
        validated_data['type'] = TicketType.apply_asset
        return self.create_or_update('create', validated_data)

    def update(self, instance, validated_data):
        current_org_id = str(get_current_org_id())
        root_org_id = Organization.ROOT_ID
        if instance.org_id == root_org_id and current_org_id != root_org_id:
            instance = self.create(validated_data)
        else:
            instance = self.create_or_update('update', validated_data, instance)
        return instance


class TicketFlowOptionSerializer(serializers.ModelSerializer):
    type = LabeledChoiceField(choices=TicketType.choices, read_only=True, label=_('Type'))
    approval_level = LabeledChoiceField(
        choices=TicketLevel.choices, read_only=True, label=_('Approve level')
    )
    cc_users = ObjectRelatedField(
        many=True, read_only=True, attrs=('id', 'name', 'username'), label=_('CC users')
    )

    class Meta:
        model = TicketFlow
        fields = ['id', 'name', 'type', 'approval_level', 'cc_users']
