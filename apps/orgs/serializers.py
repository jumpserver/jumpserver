from django.db.models import F
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from common.drf.serializers import BulkModelSerializer
from common.db.models import concated_display as display
from .models import Organization, OrganizationMember


class ResourceStatisticsSerializer(serializers.Serializer):
    users_amount = serializers.IntegerField(required=False)
    groups_amount = serializers.IntegerField(required=False)

    assets_amount = serializers.IntegerField(required=False)
    nodes_amount = serializers.IntegerField(required=False)
    admin_users_amount = serializers.IntegerField(required=False)
    system_users_amount = serializers.IntegerField(required=False)
    domains_amount = serializers.IntegerField(required=False)
    gateways_amount = serializers.IntegerField(required=False)

    applications_amount = serializers.IntegerField(required=False)
    asset_perms_amount = serializers.IntegerField(required=False)
    app_perms_amount = serializers.IntegerField(required=False)


class OrgSerializer(ModelSerializer):
    resource_statistics = ResourceStatisticsSerializer(source='resource_statistics_cache', read_only=True)

    class Meta:
        model = Organization
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'resource_statistics',
            'is_default', 'is_root',
            'date_created', 'created_by',
            'comment', 'created_by',
        ]

        fields_m2m = []
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created']


class OrgMemberSerializer(BulkModelSerializer):
    org_display = serializers.CharField(read_only=True)
    user_display = serializers.CharField(read_only=True)

    class Meta:
        model = OrganizationMember
        fields_mini = ['id']
        fields_small = fields_mini + []
        fields_fk = ['org', 'user', 'org_display', 'user_display',]
        fields = fields_small + fields_fk
        use_model_bulk_create = True
        model_bulk_create_kwargs = {'ignore_conflicts': True}

    def get_unique_together_validators(self):
        if self.parent:
            return []
        return super().get_unique_together_validators()

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.annotate(
            org_display=F('org__name'),
            user_display=display('user__name', 'user__username')
        ).distinct()


class CurrentOrgSerializer(ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'is_default', 'is_root', 'comment']
