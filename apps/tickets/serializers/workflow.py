from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from rest_framework import serializers

from orgs.models import Organization
from orgs.utils import current_org, tmp_to_root_org
from rbac.models import Role
from tickets.models import Workflow, WorkflowVersion, WorkflowInstance, WorkflowNodeInstance, ApprovalTask, WorkflowEvent
from tickets.workflow.definition import validate_definition
from tickets.workflow.errors import WorkflowConflict
from tickets.workflow.publication import publish_workflow
from tickets.workflow.preview import upcoming_nodes
from tickets.plugins import ticket_plugins


class WorkflowSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    org_name = serializers.CharField(read_only=True, label=_('Org name'), default='')
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    active_version_number = serializers.IntegerField(source='active_version.number', read_only=True, default=None)
    expected_version = serializers.IntegerField(min_value=0, required=False, write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].choices = [(p.type, p.label) for p in ticket_plugins.all(visible=True)]

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'display_name', 'type', 'type_label', 'enabled', 'comment', 'org_id', 'org_name',
                  'active_version', 'active_version_number', 'expected_version', 'legacy_flow_id', 'migration_notes',
                  'created_by', 'date_created', 'date_updated']
        read_only_fields = ['org_id', 'active_version', 'legacy_flow_id', 'migration_notes',
                            'created_by', 'date_created', 'date_updated']
        # Organization is supplied by the server, not the request body.
        validators = []

    def validate(self, attrs):
        current = self.instance.active_version.number if self.instance and self.instance.active_version_id else 0
        if 'expected_version' in attrs and attrs['expected_version'] != current:
            raise WorkflowConflict(gettext('A newer version was published. Reload before publishing.'))
        if self.instance and 'type' in attrs and attrs['type'] != self.instance.type and self.instance.versions.exists():
            raise serializers.ValidationError({'type': gettext('A published workflow cannot change ticket type.')})
        if attrs.get('enabled') and (not self.instance or not self.instance.active_version_id):
            raise serializers.ValidationError({'enabled': gettext('Publish a version before enabling the workflow.')})
        org_id = self.instance.org_id if self.instance and current_org.is_root() else current_org.id
        ticket_type = attrs.get('type', getattr(self.instance, 'type', ''))
        if ticket_type == 'login_confirm' and org_id != Organization.ROOT_ID:
            raise serializers.ValidationError({'type': gettext(
                'Login confirmation workflows can only be configured in the global organization.'
            )})
        qs = Workflow.objects.filter(org_id=org_id, name=attrs.get('name', getattr(self.instance, 'name', '')),
                                     type=ticket_type)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': gettext('A workflow with this name and type already exists.')})
        return attrs

    def create(self, validated_data):
        validated_data.pop('expected_version', None)
        return super().create({**validated_data, 'org_id': current_org.id,
                               'created_by': str(self.context['request'].user)[:128]})

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.org_id == Organization.ROOT_ID and not current_org.is_root():
            # Editing an inherited flow must never change another organization's approvals.
            with tmp_to_root_org():
                instance = Workflow.objects.select_for_update().get(pk=instance.pk)
            self.instance = instance
            self.validate(validated_data)
            validated_data.pop('expected_version', None)
            local = Workflow.objects.create(
                name=validated_data.get('name', instance.name), type=validated_data.get('type', instance.type),
                comment=instance.comment, enabled=instance.enabled,
                migration_notes=instance.migration_notes,
                created_by=str(self.context['request'].user)[:128],
            )
            if instance.active_version_id:
                publish_workflow(local, instance.active_version.as_definition(),
                                 actor=self.context['request'].user, expected_version=0)
                local.refresh_from_db()
            instance = local
        instance = Workflow.objects.select_for_update().get(pk=instance.pk)
        self.instance = instance
        self.validate(validated_data)
        validated_data.pop('expected_version', None)
        return super().update(instance, validated_data)


class WorkflowPublishSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=0, required=True)
    definition = serializers.JSONField()

    def validate_definition(self, value):
        return validate_definition(value)


class WorkflowVersionSerializer(serializers.ModelSerializer):
    definition = serializers.SerializerMethodField()
    node_names = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowVersion
        fields = ['id', 'workflow', 'number', 'published_at', 'created_by', 'definition', 'node_names']

    @staticmethod
    def get_node_names(obj):
        return {node.key: str(obj.workflow.node_display_name(node)) for node in obj.nodes.all()}

    @staticmethod
    def get_definition(obj):
        return obj.as_definition()


class ApprovalTaskSerializer(serializers.ModelSerializer):
    ticket = serializers.UUIDField(source='node_instance.instance.ticket_id', read_only=True)
    instance = serializers.UUIDField(source='node_instance.instance_id', read_only=True)
    node_name = serializers.SerializerMethodField()
    deadline = serializers.DateTimeField(source='node_instance.deadline', read_only=True)

    @staticmethod
    def get_node_name(obj):
        run = obj.node_instance
        return str(run.instance.version.workflow.node_display_name(run.node))

    class Meta:
        model = ApprovalTask
        fields = ['id', 'ticket', 'instance', 'node_instance', 'node_name', 'assignee', 'assignee_snapshot', 'state',
                  'is_added', 'predecessor', 'deadline', 'comment', 'date_created', 'date_finished']
        read_only_fields = fields


class WorkflowNodeInstanceSerializer(serializers.ModelSerializer):
    config = serializers.JSONField(source='node.config', read_only=True)
    key = serializers.CharField(source='node.key', read_only=True)
    name = serializers.SerializerMethodField()
    type = serializers.CharField(source='node.type', read_only=True)
    tasks = ApprovalTaskSerializer(many=True, read_only=True)

    @staticmethod
    def get_name(obj):
        return str(obj.instance.version.workflow.node_display_name(obj.node))

    class Meta:
        model = WorkflowNodeInstance
        fields = ['id', 'key', 'name', 'type', 'config', 'state', 'required', 'deadline', 'result', 'date_created', 'date_finished', 'tasks']
        read_only_fields = fields


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    workflow = serializers.UUIDField(source='version.workflow_id', read_only=True)
    version_number = serializers.IntegerField(source='version.number', read_only=True)

    class Meta:
        model = WorkflowInstance
        fields = ['id', 'ticket', 'org_id', 'workflow', 'version', 'version_number', 'applicant', 'state',
                  'date_started', 'date_finished']
        read_only_fields = fields


class WorkflowInstanceDetailSerializer(WorkflowInstanceSerializer):
    workflow_name = serializers.CharField(source='version.workflow.display_name', read_only=True)
    approver_role_names = serializers.SerializerMethodField()
    nodes = WorkflowNodeInstanceSerializer(source='node_instances', many=True, read_only=True)
    upcoming_nodes = serializers.SerializerMethodField()
    resource_adjustment = serializers.SerializerMethodField()

    @staticmethod
    def get_approver_role_names(instance):
        role_ids = set()
        for node in instance.version.nodes.all():
            approvers = node.config.get('approvers', {})
            if approvers.get('type') == 'role':
                role_ids.update(approvers['value'])
        return {str(role.pk): str(role.display_name) for role in Role.objects.filter(pk__in=role_ids)}

    @staticmethod
    def get_upcoming_nodes(instance):
        return upcoming_nodes(instance)

    def get_resource_adjustment(self, instance):
        from tickets.workflow.resources import adjustment_status
        request = self.context.get('request')
        return adjustment_status(instance, request.user if request else None)

    class Meta(WorkflowInstanceSerializer.Meta):
        fields = WorkflowInstanceSerializer.Meta.fields + [
            'workflow_name', 'approver_role_names', 'context', 'nodes', 'upcoming_nodes', 'resource_adjustment',
        ]
        read_only_fields = fields


class WorkflowEventSerializer(serializers.ModelSerializer):
    resources = serializers.SerializerMethodField()

    def get_resources(self, event):
        if event.type not in ('action.executed', 'action.submitted'):
            return []
        instance = self.context.get('workflow_instance') or event.instance
        plugin_type = instance.context.get('plugin', {}).get('type') or instance.ticket.type
        request = self.context.get('request')
        plugin = ticket_plugins.get(plugin_type)
        return plugin.get_result_resources(instance, event, request.user if request else None)

    class Meta:
        model = WorkflowEvent
        fields = ['id', 'instance', 'node_instance', 'task', 'type', 'actor', 'actor_snapshot', 'data', 'resources', 'date_created']
        read_only_fields = fields


class WorkflowDecisionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='', max_length=4096)


class WorkflowReassignSerializer(WorkflowDecisionSerializer):
    target = serializers.UUIDField()


class WorkflowApproveSerializer(WorkflowDecisionSerializer):
    expected_revision = serializers.IntegerField(min_value=0, required=False)


class WorkflowResourceSerializer(serializers.Serializer):
    resources = serializers.DictField()
    reason = serializers.CharField(max_length=4096)
    expected_revision = serializers.IntegerField(min_value=0)
