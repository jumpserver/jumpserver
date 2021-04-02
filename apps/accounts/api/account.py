from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import SafeRolePermission
from .. import serializers
from ..models import Account
from ..utils import get_user_binding_safes


__all__ = ['AccountViewSet']


class SafeViewSetMixin(object):
    model = None

    def get_queryset(self):
        queryset = super().get_queryset()
        safes = get_user_binding_safes(self.request.user)
        allowed_safes = [safe for safe in safes if self.check_safe_permissions(safe)]
        queryset = queryset.filter(safe__in=allowed_safes)
        return queryset

    def perform_create(self, serializer):
        objs = self.get_to_create_objects_by_serializer(serializer)
        self.check_objects_permissions(objs)
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        objs = self.get_to_update_objects_by_serializer(serializer)
        self.check_objects_permissions(objs)
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        self.check_object_permissions(self.request, instance)
        return super().perform_destroy(instance)

    def check_safe_permissions(self, safe):
        for permission in self.get_permissions():
            if not hasattr(permission, 'has_safe_permission'):
                continue
            if not permission.has_safe_permission(self.request, self, safe):
                return False
        return True

    def check_objects_permissions(self, objs):
        for obj in objs:
            self.check_object_permissions(self.request, obj)

    def get_to_create_objects_by_serializer(self, serializer):
        validated_data = serializer.validated_data
        if not isinstance(validated_data, list):
            validated_data = [validated_data]
        objs = [self.model(**data) for data in validated_data]
        return objs

    def get_to_update_objects_by_serializer(self, serializer):
        if isinstance(serializer.instance, self.model):
            objs = [serializer.instance]
        else:
            # bulk
            id_attr = getattr(serializer.child.Meta, 'update_lookup_field', 'id')
            objs_ids = [i.pop(id_attr) for i in serializer.validated_data]
            objs = serializer.instance.filter(**{'{}__in'.format(id_attr): objs_ids})
        return objs


class AccountViewSet(SafeViewSetMixin, OrgBulkModelViewSet):
    permission_classes = (SafeRolePermission, )
    serializer_class = serializers.AccountSerializer
    model = Account
    filterset_fields = {
        'id': ['exact', 'in'],
        'name': ['exact'],
        'username': ['exact'],
        'type': ['exact', 'in'],
        'type__name': ['exact', 'in'],
        'address': ['exact'],
        'is_privileged': ['exact'],
        'safe': ['exact', 'in'],
        'safe__name': ['exact']
    }
    search_fields = (
        'id', 'name', 'username', 'type', 'type__name', 'address', 'is_privileged', 'safe',
        'safe__name'
    )
