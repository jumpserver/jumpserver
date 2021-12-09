from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from perms.models import ApplicationPermission
from applications.const import AppCategory, AppType
from orgs.utils import tmp_to_org
from tickets.models import Ticket
from applications.models import Application
from .common import DefaultPermissionName

__all__ = [
    'ApplySerializer',
]


class ApplySerializer(serializers.Serializer):
    apply_permission_name = serializers.CharField(
        max_length=128, default=DefaultPermissionName(), label=_('Apply name')
    )
    # 申请信息
    apply_category = serializers.ChoiceField(
        required=True, choices=AppCategory.choices, label=_('Category'),
        allow_null=True,
    )
    apply_category_display = serializers.CharField(
        read_only=True, label=_('Category display'), allow_null=True,
    )
    apply_type = serializers.ChoiceField(
        required=True, choices=AppType.choices, label=_('Type'),
        allow_null=True
    )
    apply_type_display = serializers.CharField(
        required=False, read_only=True, label=_('Type display'),
        allow_null=True
    )
    apply_applications = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Apply applications'),
        allow_null=True
    )
    apply_applications_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Apply applications display'), allow_null=True,
        default=list
    )
    apply_system_users = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Apply system users'),
        allow_null=True
    )
    apply_system_users_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Apply system user display'), allow_null=True,
        default=list
    )
    apply_date_start = serializers.DateTimeField(
        required=True, label=_('Date start'), allow_null=True
    )
    apply_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired'), allow_null=True
    )

    def validate_approve_permission_name(self, permission_name):
        if not isinstance(self.root.instance, Ticket):
            return permission_name

        with tmp_to_org(self.root.instance.org_id):
            already_exists = ApplicationPermission.objects.filter(name=permission_name).exists()
            if not already_exists:
                return permission_name

        raise serializers.ValidationError(_(
            'Permission named `{}` already exists'.format(permission_name)
        ))

    def validate_apply_applications(self, apply_applications):
        type = self.root.initial_data['meta'].get('apply_type')
        org_id = self.root.initial_data.get('org_id')
        with tmp_to_org(org_id):
            applications = Application.objects.filter(
                id__in=apply_applications, type=type
            ).values_list('id', flat=True)
        return list(applications)

    def validate(self, attrs):
        apply_date_start = attrs['apply_date_start'].strftime('%Y-%m-%d %H:%M:%S')
        apply_date_expired = attrs['apply_date_expired'].strftime('%Y-%m-%d %H:%M:%S')

        if apply_date_expired <= apply_date_start:
            error = _('The expiration date should be greater than the start date')
            raise serializers.ValidationError({'apply_date_expired': error})

        attrs['apply_date_start'] = apply_date_start
        attrs['apply_date_expired'] = apply_date_expired
        return attrs
