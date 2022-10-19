from django.utils.translation import ugettext as _
from rest_framework import serializers

from perms.models import ApplicationPermission
from perms.serializers.base import ActionsField
from orgs.utils import tmp_to_org
from applications.models import Application
from tickets.models import ApplyApplicationTicket
from .ticket import TicketApplySerializer
from .common import BaseApplyAssetApplicationSerializer

__all__ = ['ApplyApplicationSerializer', 'ApplyApplicationDisplaySerializer', 'ApproveApplicationSerializer']


class ApplyApplicationSerializer(BaseApplyAssetApplicationSerializer, TicketApplySerializer):
    apply_actions = ActionsField(required=True, allow_empty=False)
    permission_model = ApplicationPermission

    class Meta:
        model = ApplyApplicationTicket
        writeable_fields = [
            'id', 'title', 'type', 'apply_category', 'comment',
            'apply_type', 'apply_applications', 'apply_system_users',
            'apply_actions', 'apply_date_start', 'apply_date_expired', 'org_id'
        ]
        fields = TicketApplySerializer.Meta.fields + \
                 writeable_fields + ['apply_permission_name', 'apply_actions_display']
        read_only_fields = list(set(fields) - set(writeable_fields))
        ticket_extra_kwargs = TicketApplySerializer.Meta.extra_kwargs
        extra_kwargs = {
            'apply_applications': {'required': False, 'allow_empty': True},
            'apply_system_users': {'required': False, 'allow_empty': True},
        }
        extra_kwargs.update(ticket_extra_kwargs)

    def validate_apply_applications(self, applications):
        if self.is_final_approval and not applications:
            raise serializers.ValidationError(_('This field is required.'))
        tp = self.initial_data.get('apply_type')
        return self.filter_many_to_many_field(Application, applications, type=tp)


class ApproveApplicationSerializer(ApplyApplicationSerializer):
    class Meta(ApplyApplicationSerializer.Meta):
        read_only_fields = ApplyApplicationSerializer.Meta.read_only_fields + ['title', 'type']


class ApplyApplicationDisplaySerializer(ApplyApplicationSerializer):
    apply_applications = serializers.SerializerMethodField()
    apply_system_users = serializers.SerializerMethodField()

    class Meta:
        model = ApplyApplicationSerializer.Meta.model
        fields = ApplyApplicationSerializer.Meta.fields
        read_only_fields = fields

    @staticmethod
    def get_apply_applications(instance):
        with tmp_to_org(instance.org_id):
            return instance.apply_applications.values_list('id', flat=True)

    @staticmethod
    def get_apply_system_users(instance):
        with tmp_to_org(instance.org_id):
            return instance.apply_system_users.values_list('id', flat=True)
