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
from users.models import User
from tickets.models import Ticket, TicketFlow, ApprovalRule
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
            'type', 'type_display', 'meta', 'state',
            'status', 'status_display', 'applicant_display', 'process',
            'date_created', 'date_updated', 'comment', 'org_id', 'org_name', 'body'
        ]
        fields_fk = ['applicant', ]
        fields_m2m = ['assignees']
        fields = fields_small + fields_fk + fields_m2m

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
        type = attrs.get('type')
        if type:
            attrs['flow'] = TicketFlow.get_org_related_flows().filter(type=type).first()
        return attrs

    @atomic
    def create(self, validated_data):
        instance = super().create(validated_data)
        name = _('Created by ticket ({}-{})').format(instance.title, str(instance.id)[:4])
        with tmp_to_org(instance.org_id):
            if not AssetPermission.objects.filter(name=name).exists():
                instance.meta.update({'apply_permission_name': name})
                return instance
        raise serializers.ValidationError(_('Permission named `{}` already exists'.format(permission_name)))


class TicketApproveSerializer(TicketSerializer):
    meta = serializers.ReadOnlyField()

    class Meta:
        model = Ticket
        fields = TicketSerializer.Meta.fields
        read_only_fields = fields


class TicketFlowApproveSerializer(serializers.ModelSerializer):
    approval_level_display = serializers.ReadOnlyField(
        source='get_approval_level_display', label=_('Approve level display'))
    approve_strategy_display = serializers.ReadOnlyField(
        source='get_approve_strategy_display', label=_('Approve strategy display'))

    class Meta:
        model = ApprovalRule
        fields_mini = ['id', ]
        fields_small = fields_mini + [
            'approval_level', 'approval_level_display', 'approve_strategy', 'approve_strategy_display',
            'assignees_display', 'date_created', 'date_updated'
        ]
        fields_fk = ['ticket_flow', ]
        fields_m2m = ['assignees']
        fields = fields_small + fields_fk + fields_m2m
        read_only_fields = ['assignees_display', 'date_created', 'date_updated']
        extra_kwargs = {
            "assignees": {'allow_null': True, 'required': False}
        }


class TicketFlowSerializer(OrgResourceModelSerializerMixin):
    org_id = serializers.CharField(required=True, max_length=36, allow_blank=True, label=_("Organization"))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    ticket_flow_approves = TicketFlowApproveSerializer(many=True, required=True)

    class Meta:
        model = TicketFlow
        fields_mini = ['id', 'title']
        fields_small = fields_mini + [
            'type', 'type_display', 'created_by', 'date_created', 'date_updated', 'org_id', 'org_name'
        ]
        fields = fields_small + ['ticket_flow_approves', ]
        read_only_fields = ['created_by', 'date_created', 'date_updated']

    def validate_type(self, value):
        if not self.instance or (self.instance and self.instance.type != value):
            if self.Meta.model.objects.filter(type=value).exists():
                error = _('The current organization type already exists')
                raise serializers.ValidationError(error)
        return value

    def validate_org_id(self, org_id):
        org = Organization.get_instance(org_id)
        if not org:
            error = _('The organization `{}` does not exist'.format(org_id))
            raise serializers.ValidationError(error)
        return org_id

    def create_or_update(self, action, validated_data, related, assignees, instance=None):
        childs = validated_data.pop(related, [])
        if not instance:
            instance = getattr(super(), action)(validated_data)
        else:
            instance = getattr(super(), action)(instance, validated_data)
            getattr(instance, related).clear()

        fk = getattr(instance, related).field
        for data in childs:
            data_m2m = data.pop(assignees, None)
            data[fk.name] = instance
            child_instance = fk.model.objects.create(**data)
            if child_instance.approve_strategy == 'super':
                data_m2m = list(User.get_super_admins())
            elif child_instance.approve_strategy == 'super_admin':
                data_m2m = list(User.get_super_and_org_admins())
            getattr(child_instance, assignees).set(data_m2m)
        return instance

    @atomic
    def create(self, validated_data):
        return self.create_or_update('create', validated_data, 'ticket_flow_approves', 'assignees')

    @atomic
    def update(self, instance, validated_data):
        if instance.org_id == Organization.ROOT_ID:
            instance = self.create(validated_data)
        else:
            instance = self.create_or_update('update', validated_data, 'ticket_flow_approves', 'assignees', instance)
        return instance
