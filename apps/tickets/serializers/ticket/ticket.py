# -*- coding: utf-8 -*-
#
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from orgs.models import Organization
from tickets.const import TicketType, TicketStatus, TicketState
from tickets.models import Ticket, TicketAssignee, Workflow
from users.models import User

__all__ = [
    'TicketApplySerializer', 'TicketApproveSerializer', 'TicketSerializer',
]


class TicketSerializer(OrgResourceModelSerializerMixin):
    applicant = ObjectRelatedField(read_only=True, attrs=('id', 'name', 'username'))
    type = LabeledChoiceField(choices=TicketType.choices, read_only=True, label=_('Type'))
    status = LabeledChoiceField(
        choices=TicketStatus.choices, read_only=True,
        label=_('Ticket status'),
        help_text=_('Indicates whether the ticket is open or finished')
    )
    state = LabeledChoiceField(
        choices=TicketState.choices, read_only=True,
        label=_('Approval result'),
        help_text=_(
            'Indicates the current approval outcome: pending, closed, '
            'approved, or rejected'
        )
    )
    process_map = serializers.JSONField(read_only=True, default=list, label=_('Process map'))
    cc_users = ObjectRelatedField(
        many=True, read_only=True, attrs=('id', 'name', 'username'), label=_('CC users')
    )
    workflow = ObjectRelatedField(
        read_only=True, attrs=('id', 'name'), label=_('Ticket flow')
    )

    workflow_instance = serializers.SerializerMethodField()
    my_tasks = serializers.SerializerMethodField()

    @staticmethod
    def get_workflow_instance(obj):
        instance = getattr(obj, 'workflow_instance', None)
        return str(instance.pk) if instance else None

    def get_my_tasks(self, obj):
        request = self.context.get('request')
        if not request:
            return []
        return [str(pk) for pk in obj.approval_tasks.filter(
            assignee=request.user, state='pending', node_instance__instance__state='running'
        ).values_list('pk', flat=True)]

    class Meta:
        model = Ticket
        fields_mini = ['id', 'title']
        fields_small = fields_mini + ['org_id', 'workflow', 'comment']
        fields_m2m = ['cc_users']
        read_only_fields = [
            'serial_num', 'process_map', 'approval_step', 'type',
            'state', 'applicant', 'status', 'date_created',
            'date_updated', 'org_name', 'rel_snapshot', 'workflow_instance', 'my_tasks'
        ]
        fields = fields_small + fields_m2m + read_only_fields
        extra_kwargs = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_type_choices()

    def set_type_choices(self):
        tp = self.fields.get('type')
        if not tp:
            return
        choices = tp.choices
        choices.pop(TicketType.general, None)
        tp.choices = choices.items()

    @classmethod
    def setup_eager_loading(cls, queryset):
        ticket_assignees = TicketAssignee.objects.select_related('assignee')
        return queryset.select_related('applicant', 'workflow', 'workflow_instance').prefetch_related(
            Prefetch(
                'ticket_steps__ticket_assignees',
                queryset=ticket_assignees,
            ),
            'cc_users',
        )


class TicketApproveSerializer(TicketSerializer):
    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields
        read_only_fields = fields


class TicketApplySerializer(TicketSerializer):
    workflow_id = serializers.UUIDField(required=True, write_only=True, label=_('Workflow'))
    org_id = serializers.CharField(required=True, max_length=36, label=_("Organization"))
    applicant = serializers.UUIDField(required=False, source='applicant_id')

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ['workflow_id']

    def validate(self, attrs):
        from orgs.utils import tmp_to_root_org
        from tickets.workflow.approvers import available_users
        from rest_framework.exceptions import PermissionDenied
        if self.instance:
            raise serializers.ValidationError('Submitted requests are immutable. Withdraw and submit a new request.')
        org_id = attrs['org_id']
        if org_id == Organization.ROOT_ID or not Organization.objects.filter(pk=org_id).exists():
            raise serializers.ValidationError({'org_id': 'Select a concrete organization.'})
        user = self.context['request'].user
        applicant_id = attrs.pop('applicant_id', user.pk)
        if applicant_id != user.pk and not user.has_perm('tickets.add_superticket'):
            raise PermissionDenied('Submitting for another user requires super-ticket permission.')
        applicant = available_users(org_id).filter(pk=applicant_id).first()
        if not applicant:
            raise serializers.ValidationError({'applicant': 'Select an active member of this organization.'})
        if applicant_id == user.pk and not available_users(org_id).filter(pk=user.pk).exists():
            raise PermissionDenied()
        workflow_id = attrs.pop('workflow_id')
        with tmp_to_root_org():
            workflow = Workflow.objects.filter(
                pk=workflow_id, org_id__in=[org_id, Organization.ROOT_ID],
                type=attrs['type'], enabled=True, active_version__published_at__isnull=False,
            ).first()
        if not workflow:
            raise serializers.ValidationError({'workflow_id': 'Select an enabled, published workflow for this organization and type.'})
        attrs.update(workflow=workflow, applicant=applicant)
        return attrs
