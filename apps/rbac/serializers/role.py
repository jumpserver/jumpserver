
from rest_framework import serializers
from rbac.models import Role, RoleNamespaceBinding
from rbac.serializers import PermissionSerializer


__all__ = ['RoleSerializer', 'RoleNamespaceBindingSerializer', 'RoleOrgBindingSerializer']


class RoleSerializer(serializers.ModelSerializer):
    permissions_info = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            'id', 'name', 'type', 'permissions', 'permissions_info', 'is_build_in',
            'created_by', 'updated_by', 'date_created', 'date_updated'
        )
        read_only_fields = ('id', 'created_by', 'updated_by')
        extra_kwargs = {'permissions': {'allow_empty': True}}

    @staticmethod
    def get_permissions_info(obj):
        permissions = obj.permissions.all()
        serializer = PermissionSerializer(permissions, many=True)
        return serializer.data


class RoleNamespaceBindingSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    role_info = serializers.SerializerMethodField()
    namespace_info = serializers.SerializerMethodField()

    class Meta:
        model = RoleNamespaceBinding
        fields = (
            'id', 'user', 'user_info', 'role', 'role_info',
            'namespace', 'namespace_info', 'created_by',
            'updated_by', 'date_created', 'date_updated'
        )
        read_only_fields = ('id', 'created_by', 'updated_by')

    @staticmethod
    def get_user_info(obj):
        user = obj.user
        return {'id': user.id, 'name': user.name, 'username': user.username}

    @staticmethod
    def get_role_info(obj):
        role = obj.role
        return {'id': role.id, 'name': role.name, 'type': role.type}

    @staticmethod
    def get_namespace_info(obj):
        namespace = obj.namespace
        return {'id': namespace.id, 'name': namespace.name, 'comment': namespace.comment}


class RoleOrgBindingSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    role_info = serializers.SerializerMethodField()
    org_info = serializers.SerializerMethodField()

    class Meta:
        model = RoleNamespaceBinding
        fields = (
            'id', 'user', 'user_info', 'role', 'role_info',
            'orgs', 'org_info', 'created_by', 'updated_by',
            'date_created', 'date_updated'
        )
        read_only_fields = ('id', 'created_by', 'updated_by')

    @staticmethod
    def get_user_info(obj):
        user = obj.user
        return {'id': user.id, 'name': user.name, 'username': user.username}

    @staticmethod
    def get_role_info(obj):
        role = obj.role
        return {'id': role.id, 'name': role.name, 'type': role.type}

    @staticmethod
    def get_org_info(obj):
        org = obj.org
        return {'id': org.id, 'name': org.name}
