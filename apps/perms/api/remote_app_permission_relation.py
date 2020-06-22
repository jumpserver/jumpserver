# coding: utf-8
#
from perms.api.base import RelationViewSet
from rest_framework import generics
from django.db.models import F
from django.shortcuts import get_object_or_404

from common.permissions import IsOrgAdmin
from .. import models, serializers

__all__ = [
    'RemoteAppPermissionUserRelationViewSet',
    'RemoteAppPermissionRemoteAppRelationViewSet',
    'RemoteAppPermissionAllRemoteAppListApi',
    'RemoteAppPermissionAllUserListApi',
]


class RemoteAppPermissionAllUserListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.PermissionAllUserSerializer
    filter_fields = ("username", "name")
    search_fields = filter_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        perm = get_object_or_404(models.RemoteAppPermission, pk=pk)
        users = perm.all_users.only(
            *self.serializer_class.Meta.only_fields
        )
        return users


class RemoteAppPermissionUserRelationViewSet(RelationViewSet):
    serializer_class = serializers.RemoteAppPermissionUserRelationSerializer
    m2m_field = models.RemoteAppPermission.users.field
    permission_classes = (IsOrgAdmin,)
    filter_fields = [
        'id', 'user', 'remoteapppermission'
    ]
    search_fields = ('user__name', 'user__username', 'remoteapppermission__name')

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(user_display=F('user__name'))
        return queryset


class RemoteAppPermissionRemoteAppRelationViewSet(RelationViewSet):
    serializer_class = serializers.RemoteAppPermissionRemoteAppRelationSerializer
    m2m_field = models.RemoteAppPermission.remote_apps.field
    permission_classes = (IsOrgAdmin,)
    filter_fields = [
        'id', 'remoteapp', 'remoteapppermission',
    ]
    search_fields = [
        "id", "remoteapp__name", "remoteapppermission__name"
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(remoteapp_display=F('remoteapp__name'))
        return queryset


class RemoteAppPermissionAllRemoteAppListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.RemoteAppPermissionAllRemoteAppSerializer
    filter_fields = ("name",)
    search_fields = filter_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        perm = get_object_or_404(models.RemoteAppPermission, pk=pk)
        remote_apps = perm.all_remote_apps.only(
            *self.serializer_class.Meta.only_fields
        )
        return remote_apps
