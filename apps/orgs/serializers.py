
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from users.models import User, UserGroup
from assets.models import Asset, Domain, AdminUser, SystemUser, Label
from perms.models import AssetPermission
from common.serializers import AdaptedBulkListSerializer
from .utils import set_current_org, get_current_org
from .models import Organization
from .mixins import OrgMembershipSerializerMixin


class OrgSerializer(ModelSerializer):
    class Meta:
        model = Organization
        list_serializer_class = AdaptedBulkListSerializer
        fields = '__all__'
        read_only_fields = ['created_by', 'date_created']


class OrgReadSerializer(ModelSerializer):
    admins = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    users = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    user_groups = serializers.SerializerMethodField()
    assets = serializers.SerializerMethodField()
    domains = serializers.SerializerMethodField()
    admin_users = serializers.SerializerMethodField()
    system_users = serializers.SerializerMethodField()
    labels = serializers.SerializerMethodField()
    perms = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = '__all__'

    @staticmethod
    def get_data_from_model(obj, model):
        current_org = get_current_org()
        set_current_org(Organization.root())
        if model == Asset:
            data = [o.hostname for o in model.objects.filter(org_id=obj.id)]
        else:
            data = [o.name for o in model.objects.filter(org_id=obj.id)]
        set_current_org(current_org)
        return data

    def get_user_groups(self, obj):
        return self.get_data_from_model(obj, UserGroup)

    def get_assets(self, obj):
        return self.get_data_from_model(obj, Asset)

    def get_domains(self, obj):
        return self.get_data_from_model(obj, Domain)

    def get_admin_users(self, obj):
        return self.get_data_from_model(obj, AdminUser)

    def get_system_users(self, obj):
        return self.get_data_from_model(obj, SystemUser)

    def get_labels(self, obj):
        return self.get_data_from_model(obj, Label)

    def get_perms(self, obj):
        return self.get_data_from_model(obj, AssetPermission)


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
