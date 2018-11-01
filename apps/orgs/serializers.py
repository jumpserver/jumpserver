
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer

from common.mixins import BulkSerializerMixin

from users.models import User, UserGroup
from assets.models import Asset, Domain, AdminUser, SystemUser, Label
from perms.models import AssetPermission
from .utils import set_current_org, get_current_org
from .models import Organization


class OrgSerializer(BulkSerializerMixin, ModelSerializer):
    admins = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()
    user_groups = serializers.SerializerMethodField()
    assets = serializers.SerializerMethodField()
    domains = serializers.SerializerMethodField()
    admin_users = serializers.SerializerMethodField()
    system_users = serializers.SerializerMethodField()
    labels = serializers.SerializerMethodField()
    perms = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        list_serializer_class = BulkListSerializer
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'date_created']

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

    @staticmethod
    def get_users(obj):
        return [user.name for user in obj.users.all()]

    @staticmethod
    def get_admins(obj):
        return [admin.name for admin in obj.admins.all()]

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


class OrgUpdateUserSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all()
    )

    class Meta:
        model = Organization
        fields = ['id', 'users']


class OrgUpdateAdminSerializer(serializers.ModelSerializer):
    admins = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all()
    )

    class Meta:
        model = Organization
        fields = ['id', 'admins']
