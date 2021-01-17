from django.db.models import F
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from users.models.user import User
from common.drf.serializers import AdaptedBulkListSerializer
from common.drf.serializers import BulkModelSerializer
from common.db.models import concated_display as display
from .models import Organization, OrganizationMember, ROLE


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
    users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True, required=False)
    admins = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True, required=False)
    auditors = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True, required=False)

    resource_statistics = ResourceStatisticsSerializer(source='resource_statistics_cache', read_only=True)

    class Meta:
        model = Organization
        list_serializer_class = AdaptedBulkListSerializer
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'created_by', 'date_created', 'comment', 'resource_statistics'
        ]

        fields_m2m = ['users', 'admins', 'auditors']
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created']

    def create(self, validated_data):
        members = self._pop_members(validated_data)
        instance = Organization.objects.create(**validated_data)
        OrganizationMember.objects.add_users_by_role(instance, *members)
        return instance

    def _pop_members(self, validated_data):
        return (
            validated_data.pop('users', None),
            validated_data.pop('admins', None),
            validated_data.pop('auditors', None)
        )

    def update(self, instance, validated_data):
        members = self._pop_members(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        OrganizationMember.objects.set_users_by_role(instance, *members)
        return instance


class OrgReadSerializer(OrgSerializer):
    pass


class OrgMemberSerializer(BulkModelSerializer):
    org_display = serializers.CharField(read_only=True)
    user_display = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = ('id', 'org', 'user', 'role', 'org_display', 'user_display', 'role_display')
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


class OrgMemberOldBaseSerializer(BulkModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        label=_('Organization'), queryset=Organization.objects.all(), required=True, source='org'
    )

    def to_internal_value(self, data):
        view = self.context['view']
        org_id = view.kwargs.get('org_id')
        if org_id:
            data['organization'] = org_id
        return super().to_internal_value(data)

    class Meta:
        model = OrganizationMember
        fields = ('id', 'organization', 'user', 'role')


class OrgMemberAdminSerializer(OrgMemberOldBaseSerializer):
    role = serializers.HiddenField(default=ROLE.ADMIN)


class OrgMemberUserSerializer(OrgMemberOldBaseSerializer):
    role = serializers.HiddenField(default=ROLE.USER)


class OrgRetrieveSerializer(OrgReadSerializer):
    admins = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    auditors = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    users = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta(OrgReadSerializer.Meta):
        pass
