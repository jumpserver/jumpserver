from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from applications.models import Application
from applications.const import ApplicationCategoryChoices, ApplicationTypeChoices
from assets.models import SystemUser
from orgs.utils import tmp_to_org
from tickets.models import Ticket

__all__ = [
    'ApplyApplicationSerializer', 'ApplySerializer', 'ApproveSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_category = serializers.ChoiceField(
        required=True, choices=ApplicationCategoryChoices.choices, label=_('Category'),
        allow_null=True,
    )
    apply_category_display = serializers.CharField(
        read_only=True, label=_('Category display'), allow_null=True,
    )
    apply_type = serializers.ChoiceField(
        required=True, choices=ApplicationTypeChoices.choices, label=_('Type'),
        allow_null=True
    )
    apply_type_display = serializers.CharField(
        required=False, read_only=True, label=_('Type display'),
        allow_null=True
    )
    apply_application_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('Application group'),
        default=list, allow_null=True
    )
    apply_system_user_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('System user group'),
        default=list, allow_null=True
    )
    apply_date_start = serializers.DateTimeField(
        required=True, label=_('Date start'), allow_null=True
    )
    apply_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired'), allow_null=True
    )


class ApproveSerializer(serializers.Serializer):
    # 审批信息
    approve_applications = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Approve applications'),
        allow_null=True
    )
    approve_applications_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve applications display'), allow_null=True,
        default=list
    )
    approve_system_users = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Approve system users'),
        allow_null=True
    )
    approve_system_users_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve system user display'), allow_null=True,
        default=list
    )
    approve_date_start = serializers.DateTimeField(
        required=True, label=_('Date start'), allow_null=True
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired'), allow_null=True
    )

    def validate_approve_applications(self, approve_applications):
        if not isinstance(self.root.instance, Ticket):
            return []

        with tmp_to_org(self.root.instance.org_id):
            apply_type = self.root.instance.meta.get('apply_type')
            queries = Q(type=apply_type)
            queries &= Q(id__in=approve_applications)
            applications_id = Application.objects.filter(queries).values_list('id', flat=True)
            applications_id = [str(application_id) for application_id in applications_id]
            if applications_id:
                return applications_id

        raise serializers.ValidationError(_(
            'No `Application` are found under Organization `{}`'.format(self.root.instance.org_name)
        ))

    def validate_approve_system_users(self, approve_system_users):
        if not isinstance(self.root.instance, Ticket):
            return []

        with tmp_to_org(self.root.instance.org_id):
            apply_type = self.root.instance.meta.get('apply_type')
            protocol = SystemUser.get_protocol_by_application_type(apply_type)
            queries = Q(protocol=protocol)
            queries &= Q(id__in=approve_system_users)
            system_users_id = SystemUser.objects.filter(queries).values_list('id', flat=True)
            system_users_id = [str(system_user_id) for system_user_id in system_users_id]
            if system_users_id:
                return system_users_id

        raise serializers.ValidationError(_(
            'No `SystemUser` are found under Organization `{}`'.format(self.root.instance.org_name)
        ))


class ApplyApplicationSerializer(ApplySerializer, ApproveSerializer):
    # 推荐信息
    recommend_applications = serializers.SerializerMethodField()
    recommend_system_users = serializers.SerializerMethodField()

    def get_recommend_applications(self, value):
        if not isinstance(self.root.instance, Ticket):
            return []

        apply_application_group = value.get('apply_application_group', [])
        apply_type = value.get('apply_type')
        queries = Q()
        for application in apply_application_group:
            queries |= Q(name__icontains=application)
        queries &= Q(type=apply_type)

        with tmp_to_org(self.root.instance.org_id):
            applications_id = Application.objects.filter(queries).values_list('id', flat=True)[:5]
            applications_id = [str(application_id) for application_id in applications_id]
            return applications_id

    def get_recommend_system_users(self, value):
        if not isinstance(self.root.instance, Ticket):
            return []

        apply_type = value.get('apply_type')
        apply_system_user_group = value.get('apply_system_user_group', [])
        protocol = SystemUser.get_protocol_by_application_type(apply_type)
        queries = Q()
        for system_user in apply_system_user_group:
            queries |= Q(username__icontains=system_user)
            queries |= Q(name__icontains=system_user)
        queries &= Q(protocol=protocol)

        with tmp_to_org(self.root.instance.org_id):
            system_users_id = SystemUser.objects.filter(queries).values_list('id', flat=True)[:5]
            system_users_id = [str(system_user_id) for system_user_id in system_users_id]
            return system_users_id
