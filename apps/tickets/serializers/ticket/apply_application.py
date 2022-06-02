from perms.models import ApplicationPermission
from orgs.utils import tmp_to_org
from applications.models import Application
from tickets.models import ApplyApplicationTicket
from .ticket import TicketApplySerializer
from .common import BaseApplyAssetApplicationSerializer

__all__ = ['ApplyApplicationSerializer', 'ApplyApplicationDisplaySerializer']


class ApplyApplicationSerializer(BaseApplyAssetApplicationSerializer, TicketApplySerializer):
    permission_model = ApplicationPermission

    class Meta:
        model = ApplyApplicationTicket
        writeable_fields = [
            'id', 'title', 'type', 'apply_category',
            'apply_type', 'apply_applications', 'apply_system_users',
            'apply_date_start', 'apply_date_expired', 'org_id'
        ]
        fields = TicketApplySerializer.Meta.fields + writeable_fields + ['apply_permission_name']
        read_only_fields = list(set(fields) - set(writeable_fields))
        ticket_extra_kwargs = TicketApplySerializer.Meta.extra_kwargs
        extra_kwargs = {}
        extra_kwargs.update(ticket_extra_kwargs)

    def validate_apply_applications(self, apply_applications):
        type = self.initial_data.get('apply_type')
        org_id = self.initial_data.get('org_id')
        with tmp_to_org(org_id):
            applications = Application.objects.filter(
                id__in=apply_applications, type=type
            ).values_list('id', flat=True)
        return list(applications)


class ApplyApplicationDisplaySerializer(ApplyApplicationSerializer):
    class Meta:
        model = ApplyApplicationSerializer.Meta.model
        fields = ApplyApplicationSerializer.Meta.fields
        read_only_fields = fields
