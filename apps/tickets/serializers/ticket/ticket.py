# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from common.utils.timezone import dt_formatter, dt_parser
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from orgs.models import Organization
from orgs.utils import tmp_to_org
from tickets.const import TicketType, TicketStatus, TicketState, TicketOrigin, TicketLevel, StepState
from tickets.models import Ticket, TicketAssignee, Workflow
from users.models import User
from tickets.plugins import get_ticket_plugin, ticket_type_choices
from tickets.workflow.const import NodeState

__all__ = [
    'TicketApplySerializer', 'TicketApproveSerializer', 'TicketSerializer',
]


class TicketFlowField(ObjectRelatedField):
    def to_representation(self, value):
        data = super().to_representation(value)
        data['name'] = str(value)
        return data


class TicketProcessMapField(serializers.JSONField):
    def to_file_representation(self, value):
        rows = []
        for step in value:
            state = step.get('state')
            date = step.get('approval_date')
            if date and state != StepState.pending:
                date = dt_formatter(dt_parser(date))
            else:
                date = None
            details = [
                (_('Approve level'), step.get('name') or dict(TicketLevel.choices).get(step.get('approval_level'), step.get('approval_level'))),
                (_('Reviewers'), ', '.join(step.get('assignees_display') or [])),
                (_('Processor'), step.get('processor_display')),
                (_('State'), {**dict(NodeState.choices), **dict(StepState.choices)}.get(state, state)),
                (_('Date'), date),
            ]
            rows.append('; '.join(f'{label}: {content or "-"}' for label, content in details))
        return '\n'.join(rows) or '-'


class TicketSnapshotField(serializers.JSONField):
    def to_file_representation(self, value):
        labels = {
            'applicant': _('Applicant'),
            'cc_users': _('CC users'),
            'apply_nodes': _('Apply nodes'),
            'apply_assets': _('Apply assets'),
            'apply_login_user': _('Login user'),
            'apply_login_asset': _('Login asset'),
            'apply_run_user': _('Run user'),
            'apply_from_session': _('Session'),
            'apply_from_cmd_filter_acl': _('Command filter acl'),
        }
        rows = []
        for name, label in labels.items():
            if name not in value:
                continue
            content = value[name]
            if isinstance(content, list):
                content = ', '.join(str(item) for item in content)
            rows.append(f'{label}: {content or "-"}')
        return '\n'.join(rows) or '-'


class TicketRequestItemsField(serializers.SerializerMethodField):
    def to_file_representation(self, value):
        rows = []
        for item in value:
            content = item['value']
            if isinstance(content, list):
                content = ', '.join(str(part) for part in content)
            if content is None or content == '':
                content = '-'
            rows.append(f"{item['label']}: {content}")
        return '\n'.join(rows) or '-'


class TicketSerializer(OrgResourceModelSerializerMixin):
    applicant = ObjectRelatedField(read_only=True, attrs=('id', 'name', 'username'))
    type = LabeledChoiceField(choices=TicketType.choices, read_only=True, label=_('Type'))
    status = LabeledChoiceField(
        choices=TicketStatus.choices, read_only=True,
        label=_('Ticket status'),
        help_text=_('Indicates whether the ticket is open or finished')
    )
    origin = LabeledChoiceField(choices=TicketOrigin.choices, read_only=True, label=_('Ticket origin'))
    state = LabeledChoiceField(
        choices=TicketState.choices, read_only=True,
        label=_('Approval result'),
        help_text=_(
            'Indicates the current approval outcome: pending, closed, '
            'approved, or rejected'
        )
    )
    process_map = TicketProcessMapField(read_only=True, default=list, label=_('Process map'))
    rel_snapshot = TicketSnapshotField(read_only=True, label=_('Relation snapshot'))
    login_asset_connections = serializers.SerializerMethodField(label=_('Connection details'))
    cc_users = ObjectRelatedField(
        many=True, read_only=True, attrs=('id', 'name', 'username'), label=_('CC users')
    )
    workflow = TicketFlowField(
        read_only=True, attrs=('id', 'name'), label=_('Ticket flow')
    )

    workflow_instance = serializers.SerializerMethodField()
    my_tasks = serializers.SerializerMethodField()
    request_items = TicketRequestItemsField(label=_('Request parameters'))
    execution_mode = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()
    source_ticket = serializers.SerializerMethodField()
    reapply_action = serializers.SerializerMethodField()

    def get_reapply_action(self, obj):
        view = self.context.get('view')
        if not view or view.action not in ('list', 'retrieve'):
            return None
        from tickets.plugins.reapply import can_reapply
        user = getattr(self.context.get('request'), 'user', None)
        return 'reapply' if can_reapply(obj, user, self.context.setdefault('reapply_memberships', {})) else None

    def get_source_ticket(self, obj):
        view = self.context.get('view')
        if view and view.action != 'retrieve':
            return None
        source = obj.meta.get('source_ticket')
        if not source:
            return None
        from tickets.models import Ticket
        from orgs.utils import tmp_to_org
        user = getattr(self.context.get('request'), 'user', None)
        can_view = False
        if user:
            with tmp_to_org(source['org_id']):
                can_view = Ticket.get_user_related_tickets(user).filter(pk=source['id']).exists()
                if not can_view and 'audits.view_ticketaudit' in user.get_all_permissions():
                    can_view = Ticket.objects.filter(pk=source['id'], org_id=source['org_id']).exists()
        return {**source, 'can_view': can_view}

    @staticmethod
    def get_request_items(obj):
        items = get_ticket_plugin(obj.type).request_items(obj)
        if obj.request_data.get('resource_description'):
            items = [item for item in items if item['name'] != 'resource_description']
            items.insert(0, {'name': 'resource_description', 'label': str(_('Purpose and resource description')),
                             'value': obj.request_data['resource_description']})
        return items

    @staticmethod
    def get_execution_mode(obj):
        return get_ticket_plugin(obj.type).get_execution_mode(obj)

    def get_result(self, obj):
        view = self.context.get('view')
        if not view or view.action != 'retrieve':
            return None
        request = self.context.get('request')
        return get_ticket_plugin(obj.type).get_result(obj, request.user if request else None)

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
            'state', 'applicant', 'status', 'origin', 'date_created',
            'date_updated', 'org_name', 'rel_snapshot', 'workflow_instance', 'my_tasks',
            'request_data', 'request_items', 'execution_mode', 'result', 'source_ticket', 'reapply_action', 'login_asset_connections'
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
        choices = dict(ticket_type_choices())
        choices.pop(TicketType.general, None)
        tp.choices = choices.items()

    @staticmethod
    def get_login_asset_connections(instance):
        if instance.type != TicketType.login_asset_confirm:
            return []
        entries = (instance.meta or {}).get('login_asset_connections')
        complete = entries is not None and all(
            all(key in entry for key in ('asset_name', 'asset_address', 'reason'))
            for entry in entries
        )
        tokens = {}
        ticket = instance
        if not complete:
            with tmp_to_org(instance.org_id):
                if entries is None:
                    from assets.models import Asset
                    asset_id = ticket.request_data.get('apply_login_asset')
                    asset = Asset.objects.filter(pk=asset_id).first() if asset_id else None
                    return [{
                        'asset': {
                            'id': str(ticket.request_data.get('apply_login_asset') or ''),
                            'name': asset.name if asset else ticket.rel_snapshot.get('apply_login_asset', ''),
                            'address': asset.address if asset else '',
                        },
                        'account': ticket.request_data.get('apply_login_account', ''), 'reason': ticket.comment or '',
                    }]
                tokens = {str(token.pk): token for token in ticket.connection_tokens.select_related('asset')}
        rows = []
        for entry in entries:
            token = tokens.get(entry.get('token_id'))
            if token and (
                    str(token.asset_id) != entry.get('asset_id')
                    or (token.acl_context or {}).get('username') != entry.get('account')
                    or str(token.user_id) != str(ticket.applicant_id)
            ):
                token = None
            if 'reason' not in entry and not token:
                # Without the exact legacy token, an empty reason would hide
                # the only surviving history in the ticket's combined comment.
                # Let clients retain their original ticket display instead.
                return []
            asset = token.asset if token else None
            reason = ((token.acl_context or {}).get('reason') or token.comment or '') if token else ''
            rows.append({
                'asset': {
                    'id': entry.get('asset_id', ''),
                    'name': entry.get('asset_name', asset.name if asset else entry.get('asset_id', '')),
                    'address': entry.get('asset_address', asset.address if asset else ''),
                },
                'account': entry.get('account', ''),
                # An old shared ticket's comment contains every connection's reason.
                # Only its exact token may provide a missing per-connection reason.
                'reason': entry.get('reason', reason),
            })
        return rows

    @classmethod
    def setup_eager_loading(cls, queryset):
        ticket_assignees = TicketAssignee.objects.select_related('assignee')
        return queryset.select_related('applicant', 'workflow', 'workflow_instance').prefetch_related(
            Prefetch(
                'ticket_steps__ticket_assignees',
                queryset=ticket_assignees,
            ),
            'cc_users', 'beneficiaries',
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
            raise serializers.ValidationError(gettext('Submitted requests are immutable. Withdraw and submit a new request.'))
        org_id = attrs['org_id']
        if org_id == Organization.ROOT_ID or not Organization.objects.filter(pk=org_id).exists():
            raise serializers.ValidationError({'org_id': gettext('Select a concrete organization.')})
        user = self.context['request'].user
        applicant_id = attrs.pop('applicant_id', user.pk)
        if applicant_id != user.pk:
            raise PermissionDenied(gettext('The applicant must be the submitting user. Select authorized users in the request parameters.'))
        applicant = available_users(org_id).filter(pk=applicant_id).first()
        if not applicant:
            raise serializers.ValidationError({'applicant': gettext('Select an active member of this organization.')})
        if applicant_id == user.pk and not available_users(org_id).filter(pk=user.pk).exists():
            raise PermissionDenied()
        workflow_id = attrs.pop('workflow_id')
        with tmp_to_root_org():
            workflow = Workflow.objects.filter(
                pk=workflow_id, org_id__in=[org_id, Organization.ROOT_ID],
                type=attrs['type'], enabled=True, active_version__published_at__isnull=False,
            ).first()
        if not workflow:
            raise serializers.ValidationError({'workflow_id': gettext('Select an enabled, published workflow for this organization and type.')})
        attrs.update(workflow=workflow, applicant=applicant)
        return attrs
