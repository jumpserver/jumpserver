# -*- coding: utf-8 -*-
#
from django.http import Http404

from orgs.mixins.api import OrgModelViewSet
from common.permissions import IsOrgAdmin
from common.utils import is_uuid, lazyproperty
from .. import serializers
from .. import models

__all__ = ['AssetPermissionUserViewSet']


class AssetPermissionRelationMixin:
    @lazyproperty
    def current_permission(self):
        pk = self.kwargs.get('permission_pk')
        if not pk or not is_uuid(pk):
            raise Http404()
        return pk

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['permission'] = self.current_permission
        return context


class AssetPermissionUserViewSet(AssetPermissionRelationMixin, OrgModelViewSet):
    serializer_class = serializers.AssetPermissionUserSerializer
    permission_classes = (IsOrgAdmin,)
    filterset_fields = ['id', 'user_id', 'assetpermission_id']
    model = models.AssetPermission.users.through
    search_fields = filterset_fields

    def get_queryset(self):
        pk = self.current_permission
        queryset = self.model.objects.filter(
            assetpermission=pk
        )
        return queryset

    def create(self, request, *args, **kwargs):
        print(request.data)
        return super().create(request, *args, **kwargs)
