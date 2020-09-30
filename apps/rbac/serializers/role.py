
from rest_framework import serializers
from rbac.models import Role, RoleBinding
from rbac.serializers import PermissionSerializer


__all__ = ['RoleSerializer', 'RoleBindingSerializer']


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


class RoleBindingSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    role_info = serializers.SerializerMethodField()
    namespace_info = serializers.SerializerMethodField()
    org_info = serializers.SerializerMethodField()

    class Meta:
        model = RoleBinding
        fields = (
            'id', 'user', 'user_info', 'role', 'role_info', 'namespaces', 'namespace_info', 'orgs',
            'org_info', 'date_expired', 'created_by', 'updated_by', 'date_created', 'date_updated'
        )
        read_only_fields = ('id', 'created_by', 'updated_by')
        extra_kwargs = {'orgs': {'allow_empty': True},
                        'namespaces': {'allow_empty': True},
                        }

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
        namespaces = obj.namespaces.all()
        return [{'id': n.id, 'name': n.name, 'comment': n.comment} for n in namespaces]

    @staticmethod
    def get_org_info(obj):
        orgs = obj.orgs.all()
        return [{'id': o.id, 'name': o.name} for o in orgs]
