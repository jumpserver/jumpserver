from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from .mixin import TicketMetaSerializerMixin
from applications.models import Category


class TicketMetaApplyApplicationSerializer(TicketMetaSerializerMixin, serializers.Serializer):
    # 申请信息
    apply_category = serializers.ChoiceField(
        choices=Category.choices, required=True, allow_blank=True, label=_('Category')
    )
    apply_type = serializers.ChoiceField(
        choices=Category.get_all_type_choices(), required=True, allow_blank=True,
        label=_('Category')
    )
    apply_application_group = serializers.ListField(
        child=serializers.CharField(), allow_null=True, default=list, label=_('Application group')
    )
    apply_system_user_group = serializers.ListField(
        child=serializers.CharField(), allow_null=True, default=list, label=_('System user group')
    )
    apply_date_start = serializers.DateTimeField(
        allow_null=True, required=True, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        allow_null=True, required=True, label=_('Date expired')
    )

    # 审批信息
    approve_applications = serializers.ListField(
        child=serializers.UUIDField(), required=True, allow_null=True,
        label=_('Approve applications')
    )
    approve_system_users = serializers.ListField(
        child=serializers.UUIDField(), required=True, allow_null=True,
        label=_('Approve system users')
    )
    approve_date_start = serializers.DateTimeField(
        required=True, allow_null=True, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, allow_null=True, label=_('Date expired')
    )


class TicketMetaApplyApplicationApplySerializer(TicketMetaApplyApplicationSerializer):
    need_fields_prefix = 'apply_'


class TicketMetaApplyApplicationApproveSerializer(TicketMetaApplyApplicationSerializer):
    need_fields_prefix = 'approve_'
