from django.db import transaction
from rest_framework import serializers

from orgs.utils import current_org
from tickets.models import Workflow, WorkflowVersion, WorkflowInstance, WorkflowNodeInstance, ApprovalTask, WorkflowEvent
from tickets.workflow.definition import validate_definition
from tickets.plugins import ticket_plugins


class WorkflowSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    active_version_number = serializers.IntegerField(source='active_version.number', read_only=True, default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].choices = [(p.type, p.label) for p in ticket_plugins.all(visible=True)]

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'type', 'type_label', 'enabled', 'comment', 'org_id', 'active_version',
                  'active_version_number', 'legacy_flow_id', 'migration_notes', 'created_by', 'date_created', 'date_updated']
        read_only_fields = ['org_id', 'active_version', 'legacy_flow_id', 'migration_notes',
                            'created_by', 'date_created', 'date_updated']
        # Organization is supplied by the server, not the request body.
        validators = []

    def validate(self, attrs):
        if self.instance and 'type' in attrs and attrs['type'] != self.instance.type and self.instance.versions.exists():
            raise serializers.ValidationError({'type': 'A published workflow cannot change ticket type.'})
        if attrs.get('enabled') and (not self.instance or not self.instance.active_version_id):
            raise serializers.ValidationError({'enabled': 'Publish a version before enabling the workflow.'})
        org_id = self.instance.org_id if self.instance else current_org.id
        qs = Workflow.objects.filter(org_id=org_id, name=attrs.get('name', getattr(self.instance, 'name', '')),
                                     type=attrs.get('type', getattr(self.instance, 'type', '')))
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': 'A workflow with this name and type already exists.'})
        return attrs

    def create(self, validated_data):
        return super().create({**validated_data, 'org_id': current_org.id,
                               'created_by': str(self.context['request'].user)[:128]})

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Workflow.objects.select_for_update().get(pk=instance.pk)
        self.instance = instance
        self.validate(validated_data)
        return super().update(instance, validated_data)


class WorkflowPublishSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=0, required=True)
    definition = serializers.JSONField()

    def validate_definition(self, value):
        return validate_definition(value)


class WorkflowVersionSerializer(serializers.ModelSerializer):
    definition = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowVersion
        fields = ['id', 'workflow', 'number', 'published_at', 'created_by', 'definition']

    @staticmethod
    def get_definition(obj):
        return obj.as_definition()


class ApprovalTaskSerializer(serializers.ModelSerializer):
    ticket = serializers.UUIDField(source='node_instance.instance.ticket_id', read_only=True)
    instance = serializers.UUIDField(source='node_instance.instance_id', read_only=True)
    node_name = serializers.CharField(source='node_instance.node.name', read_only=True)
    deadline = serializers.DateTimeField(source='node_instance.deadline', read_only=True)

    class Meta:
        model = ApprovalTask
        fields = ['id', 'ticket', 'instance', 'node_instance', 'node_name', 'assignee', 'assignee_snapshot', 'state',
                  'is_added', 'predecessor', 'deadline', 'comment', 'date_created', 'date_finished']
        read_only_fields = fields


class WorkflowNodeInstanceSerializer(serializers.ModelSerializer):
    config = serializers.JSONField(source='node.config', read_only=True)
    key = serializers.CharField(source='node.key', read_only=True)
    name = serializers.CharField(source='node.name', read_only=True)
    type = serializers.CharField(source='node.type', read_only=True)
    tasks = ApprovalTaskSerializer(many=True, read_only=True)

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
    nodes = WorkflowNodeInstanceSerializer(source='node_instances', many=True, read_only=True)

    class Meta(WorkflowInstanceSerializer.Meta):
        fields = WorkflowInstanceSerializer.Meta.fields + ['context', 'nodes']
        read_only_fields = fields


class WorkflowEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowEvent
        fields = ['id', 'instance', 'node_instance', 'task', 'type', 'actor', 'actor_snapshot', 'data', 'date_created']
        read_only_fields = fields


class WorkflowDecisionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='', max_length=4096)


class WorkflowReassignSerializer(WorkflowDecisionSerializer):
    target = serializers.UUIDField()
