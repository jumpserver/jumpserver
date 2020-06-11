
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from users.models import UserGroup
from assets.models import Asset, Domain, AdminUser, SystemUser, Label
from perms.models import AssetPermission
from common.serializers import AdaptedBulkListSerializer
from .utils import set_current_org, get_current_org
from .models import Organization
from .mixins.serializers import OrgMembershipSerializerMixin


class OrgSerializer(ModelSerializer):
    class Meta:
        model = Organization
        list_serializer_class = AdaptedBulkListSerializer
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'created_by', 'date_created', 'comment'
        ]
        fields_m2m = ['users', 'admins', 'auditors']
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created']
        extra_kwargs = {
            'admins': {'write_only': True},
            'users': {'write_only': True},
            'auditors': {'write_only': True},
        }


class OrgReadSerializer(OrgSerializer):
    pass


class OrgMembershipAdminSerializer(OrgMembershipSerializerMixin, ModelSerializer):
    class Meta:
        model = Organization.admins.through
        list_serializer_class = AdaptedBulkListSerializer
        fields = '__all__'


class OrgMembershipUserSerializer(OrgMembershipSerializerMixin, ModelSerializer):
    class Meta:
        model = Organization.users.through
        list_serializer_class = AdaptedBulkListSerializer
        fields = '__all__'


class OrgAllUserSerializer(serializers.Serializer):
    user = serializers.UUIDField(read_only=True, source='id')
    user_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'username', 'name']

    @staticmethod
    def get_user_display(obj):
        return str(obj)


class OrgRetrieveSerializer(OrgReadSerializer):
    admins = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    auditors = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    users = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta(OrgReadSerializer.Meta):
        pass
