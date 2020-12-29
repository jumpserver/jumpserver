from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from applications.models import Category, Application
from assets.models import SystemUser
from .mixin import BaseTicketMetaSerializer, BaseTicketMetaApproveSerializerMixin

__all__ = [
    'TicketMetaApplyApplicationApplySerializer', 'TicketMetaApplyApplicationApproveSerializer',
]


class TicketMetaApplyApplicationSerializer(BaseTicketMetaSerializer):
    # 申请信息
    apply_category = serializers.ChoiceField(
        choices=Category.choices, required=True, label=_('Category')
    )
    apply_type = serializers.ChoiceField(
        choices=Category.get_all_type_choices(), required=True, label=_('Type')
    )
    apply_application_group = serializers.ListField(
        child=serializers.CharField(), default=list, label=_('Application group')
    )
    apply_system_user_group = serializers.ListField(
        child=serializers.CharField(), default=list, label=_('System user group')
    )
    apply_date_start = serializers.DateTimeField(
        required=True, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired')
    )
    # 审批信息
    approve_applications = serializers.ListField(
        child=serializers.UUIDField(), required=True,
        label=_('Approve applications')
    )
    approve_system_users = serializers.ListField(
        child=serializers.UUIDField(), required=True,
        label=_('Approve system users')
    )
    approve_date_start = serializers.DateTimeField(
        required=True, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired')
    )


class TicketMetaApplyApplicationApplySerializer(TicketMetaApplyApplicationSerializer):

    class Meta:
        fields = [
            'apply_category', 'apply_type', 'apply_application_group', 'apply_system_user_group',
            'apply_date_start', 'apply_date_expired'
        ]

    def validate_apply_type(self, tp):
        category = self.root.initial_data['meta'].get('apply_category')
        if not category:
            return tp
        valid_type_types = list((dict(Category.get_type_choices(category)).keys()))
        if tp in valid_type_types:
            return tp
        error = _('Type `{}`  is not a valid choice `({}){}`'.format(tp, category, valid_type_types))
        raise serializers.ValidationError(error)


class TicketMetaApplyApplicationApproveSerializer(BaseTicketMetaApproveSerializerMixin,
                                                  TicketMetaApplyApplicationSerializer):

    class Meta:
        fields = {
            'approve_applications', 'approve_system_users', 'approve_date_start',
            'approve_date_expired'
        }

    def validate_approve_applications(self, approve_applications):
        application_type = self.root.instance.meta['apply_type']
        queries = {'type': application_type}
        applications_id = self.filter_approve_resources(
            resource_model=Application, resources_id=approve_applications, queries=queries
        )
        return applications_id

    def validate_approve_system_users(self, approve_system_users):
        application_type = self.root.instance.meta['apply_type']
        protocol = SystemUser.get_protocol_by_application_type(application_type)
        queries = {'protocol': protocol}
        system_users_id = self.filter_approve_system_users(approve_system_users, queries)
        return system_users_id
