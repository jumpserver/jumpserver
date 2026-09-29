from rest_framework import serializers
from orgs.models import Organization
from orgs.utils import current_org, tmp_to_root_org
from tickets.models import Workflow


class WorkflowACLSerializerMixin(serializers.Serializer):
    workflow = serializers.UUIDField(required=False, allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['workflow'] = str(instance.workflow_id) if instance.workflow_id else None
        return data

    def validate_workflow(self, value):
        if value is None:
            return None
        types = {'loginacl': 'login_confirm', 'loginassetacl': 'login_asset_confirm',
                 'commandfilteracl': 'command_confirm'}
        ticket_type = types[self.Meta.model._meta.model_name]
        org_id = Organization.ROOT_ID if ticket_type == 'login_confirm' else str(current_org.id)
        with tmp_to_root_org():
            workflow = Workflow.objects.filter(pk=value, type=ticket_type, org_id__in=[org_id, Organization.ROOT_ID],
                                               enabled=True, active_version__published_at__isnull=False).first()
        if not workflow:
            raise serializers.ValidationError('Select an enabled workflow for this ACL type and organization.')
        return workflow
