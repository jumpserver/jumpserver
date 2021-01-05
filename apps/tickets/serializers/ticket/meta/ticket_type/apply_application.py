from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from applications.models import Application
from applications.const import ApplicationCategoryChoices, ApplicationTypeChoices
from assets.models import SystemUser
from .mixin import BaseApproveSerializerMixin

__all__ = [
    'ApplyApplicationTypeSerializer', 'ApplySerializer', 'ApproveSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_category = serializers.ChoiceField(
        required=True, choices=ApplicationCategoryChoices.choices, label=_('Category')
    )
    apply_category_display = serializers.CharField(
        read_only=True, label=_('Category display')
    )
    apply_type = serializers.ChoiceField(
        required=True, choices=ApplicationTypeChoices.choices, label=_('Type')
    )
    apply_type_display = serializers.CharField(
        required=False, read_only=True, label=_('Type display')
    )
    apply_application_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('Application group'),
        default=list,
    )
    apply_system_user_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('System user group'),
        default=list,
    )
    apply_date_start = serializers.DateTimeField(
        required=True, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired')
    )


class ApproveSerializer(BaseApproveSerializerMixin, serializers.Serializer):
    # 审批信息
    approve_applications = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Approve applications')
    )
    approve_applications_snapshot = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve applications display'),
        default=list
    )
    approve_system_users = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Approve system users')
    )
    approve_system_users_snapshot = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve system user display'),
        default=list
    )
    approve_date_start = serializers.DateTimeField(
        required=True, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired')
    )

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


class ApplyApplicationTypeSerializer(ApplySerializer, ApproveSerializer):
    pass


