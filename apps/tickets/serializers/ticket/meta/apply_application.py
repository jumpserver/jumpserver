from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from applications.models import Category, Application
from assets.models import SystemUser
from .mixin import BaseApproveSerializerMixin

__all__ = [
    'ApplyApplicationTypeSerializer', 'ApplySerializer', 'ApproveSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_category = serializers.ChoiceField(
        required=True, choices=Category.choices, label=_('Category')
    )
    apply_category_display = serializers.CharField(
        read_only=True, label=_('Category display')
    )
    apply_type = serializers.ChoiceField(
        required=True, choices=Category.get_all_type_choices(), label=_('Type')
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

    def validate_apply_type(self, tp):
        category = self.root.initial_data['meta'].get('apply_category')
        if not category:
            return tp
        valid_type_types = list((dict(Category.get_type_choices(category)).keys()))
        if tp in valid_type_types:
            return tp
        error = _('Type `{}`  is not a valid choice `({}){}`'.format(tp, category, valid_type_types))
        raise serializers.ValidationError(error)


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


