# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from django.db.transaction import atomic
from rest_framework import serializers
from common.drf.serializers import MethodSerializer
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from perms.models import AssetPermission
from orgs.models import Organization
from orgs.utils import tmp_to_org
from tickets.models import Ticket, TicketFlow, ApprovalRule
from tickets.const import TicketApprovalStrategy
from .meta import type_serializer_classes_mapping

__all__ = [
    'TicketDisplaySerializer', 'TicketApplySerializer', 'TicketApproveSerializer', 'TicketFlowSerializer'
]


class TicketSerializer(OrgResourceModelSerializerMixin):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    status_display = serializers.ReadOnlyField(source='get_status_display', label=_('Status display'))
    meta = MethodSerializer()

    class Meta:
        model = Ticket
        fields_mini = ['id', 'title']
        fields_small = fields_mini + [
            'type', 'type_display', 'meta', 'state', 'approval_step',
            'status', 'status_display', 'applicant_display', 'process_map',
            'date_created', 'date_updated', 'comment', 'org_id', 'org_name', 'body',
            'serial_num',
        ]
        fields_fk = ['applicant', ]
        fields = fields_small + fields_fk

    def get_meta_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)
        if isinstance(self.instance, Ticket):
            _type = self.instance.type
        else:
            _type = self.context['request'].query_params.get('type')

        if _type:
            action_serializer_classes_mapping = type_serializer_classes_mapping.get(_type)
            if action_serializer_classes_mapping:
                query_action = self.context['request'].query_params.get('action')
                action = query_action if query_action else self.context['view'].action
                serializer_class = action_serializer_classes_mapping.get(action)
                if not serializer_class:
                    serializer_class = action_serializer_classes_mapping.get('default')
            else:
                serializer_class = default_serializer
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class

        return serializer


class TicketDisplaySerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = TicketSerializer.Meta.fields
        read_only_fields = fields


class TicketApplySerializer(TicketSerializer):
    org_id = serializers.CharField(
        required=True, max_length=36, allow_blank=True, label=_("Organization")
    )

    class Meta:
        model = Ticket
        fields = TicketSerializer.Meta.fields
        writeable_fields = [
            'id', 'title', 'type', 'meta', 'comment', 'org_id'
        ]
        read_only_fields = list(set(fields) - set(writeable_fields))
        extra_kwargs = {
            'type': {'required': True},
        }

    def validate_type(self, tp):
        request_type = self.context['request'].query_params.get('type')
        if tp != request_type:
            error = _(
                'The `type` in the submission data (`{}`) is different from the type '
                'in the request url (`{}`)'.format(tp, request_type)
            )
            raise serializers.ValidationError(error)
        return tp

    @staticmethod
    def validate_org_id(org_id):
        org = Organization.get_instance(org_id)
        if not org:
            error = _('The organization `{}` does not exist'.format(org_id))
            raise serializers.ValidationError(error)
        return org_id

    def validate(self, attrs):
        ticket_type = attrs.get('type')
        org_id = attrs.get('org_id')
        flow = TicketFlow.get_org_related_flows(org_id=org_id).filter(type=ticket_type).first()
        if flow:
            attrs['flow'] = flow
        else:
            error = _('The ticket flow `{}` does not exist'.format(ticket_type))
            raise serializers.ValidationError(error)
        return attrs

    @atomic
    def create(self, validated_data):
        instance = super().create(validated_data)
        name = _('Created by ticket ({}-{})').format(instance.title, str(instance.id)[:4])
        with tmp_to_org(instance.org_id):
            if not AssetPermission.objects.filter(name=name).exists():
                instance.meta.update({'apply_permission_name': name})
                return instance
        raise serializers.ValidationError(_('Permission named `{}` already exists'.format(name)))


class TicketApproveSerializer(TicketSerializer):
    meta = serializers.ReadOnlyField()

    class Meta:
        model = Ticket
        fields = TicketSerializer.Meta.fields
        read_only_fields = fields


class TicketFlowApproveSerializer(serializers.ModelSerializer):
    strategy_display = serializers.ReadOnlyField(source='get_strategy_display', label=_('Approve strategy'))
    assignees_read_only = serializers.SerializerMethodField(label=_('Assignees'))
    assignees_display = serializers.SerializerMethodField(label=_('Assignees display'))

    class Meta:
        model = ApprovalRule
        fields_small = [
            'level', 'strategy', 'assignees_read_only', 'assignees_display', 'strategy_display'
        ]
        fields_m2m = ['assignees', ]
        fields = fields_small + fields_m2m
        read_only_fields = ['level', 'assignees_display']
        extra_kwargs = {
            'assignees': {'write_only': True, 'allow_empty': True, 'required': False}
        }

    def get_assignees_display(self, obj):
        return [str(assignee) for assignee in obj.get_assignees()]

    def get_assignees_read_only(self, obj):
        if obj.strategy == TicketApprovalStrategy.custom_user:
            return obj.assignees.values_list('id', flat=True)
        return []

    def validate(self, attrs):
        if attrs['strategy'] == TicketApprovalStrategy.custom_user and not attrs.get('assignees'):
            error = _('Please select the Assignees')
            raise serializers.ValidationError({'assignees': error})
        return super().validate(attrs)


class TicketFlowSerializer(OrgResourceModelSerializerMixin):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    rules = TicketFlowApproveSerializer(many=True, required=True)

    class Meta:
        model = TicketFlow
        fields_mini = ['id', ]
        fields_small = fields_mini + [
            'type', 'type_display', 'approval_level', 'created_by', 'date_created', 'date_updated',
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
        if instance.org_id == Organization.ROOT_ID:
            instance = self.create(validated_data)
        else:
            instance = self.create_or_update('update', validated_data, instance)
        return instance
