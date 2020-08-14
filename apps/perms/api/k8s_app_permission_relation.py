# coding: utf-8
#
from rest_framework import generics
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404

from common.permissions import IsOrgAdmin
from .base import RelationViewSet
from .. import models, serializers


class K8sAppPermissionUserRelationViewSet(RelationViewSet):
    serializer_class = serializers.K8sAppPermissionUserRelationSerializer
    m2m_field = models.K8sAppPermission.users.field
    permission_classes = (IsOrgAdmin,)
    filter_fields = [
        'id', 'user', 'k8sapppermission'
    ]
    search_fields = ('user__name', 'user__username', 'k8sapppermission__name')

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(user_display=F('user__name'))
        return queryset


class K8sAppPermissionUserGroupRelationViewSet(RelationViewSet):
    serializer_class = serializers.K8sAppPermissionUserGroupRelationSerializer
    m2m_field = models.K8sAppPermission.user_groups.field
    permission_classes = (IsOrgAdmin,)
    filter_fields = [
        'id', "usergroup", "k8sapppermission"
    ]
    search_fields = ["usergroup__name", "k8sapppermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(usergroup_display=F('usergroup__name'))
        return queryset


class K8sAppPermissionAllUserListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.K8sAppPermissionAllUserSerializer
    filter_fields = ("username", "name")
    search_fields = filter_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        perm = get_object_or_404(models.K8sAppPermission, pk=pk)
        users = perm.get_all_users().only(
            *self.serializer_class.Meta.only_fields
        )
        return users


class K8sAppPermissionK8sAppRelationViewSet(RelationViewSet):
    serializer_class = serializers.K8sAppPermissionK8sAppRelationSerializer
    m2m_field = models.K8sAppPermission.k8s_apps.field
    permission_classes = (IsOrgAdmin,)
    filter_fields = [
        'id', 'k8sapp', 'k8sapppermission',
    ]
    search_fields = [
        "id", "k8sapp__name", "k8sapppermission__name"
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(k8sapp_display=F('k8sapp__name'))
        return queryset


class K8sAppPermissionAllK8sAppListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.K8sAppPermissionAllK8sAppSerializer
    filter_fields = ("name",)
    search_fields = filter_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        perm = get_object_or_404(models.K8sAppPermission, pk=pk)
        database_apps = perm.get_all_k8s_apps().only(
            *self.serializer_class.Meta.only_fields
        )
        return database_apps


class K8sAppPermissionSystemUserRelationViewSet(RelationViewSet):
    serializer_class = serializers.K8sAppPermissionSystemUserRelationSerializer
    m2m_field = models.K8sAppPermission.system_users.field
    permission_classes = (IsOrgAdmin,)
    filter_fields = [
        'id', 'systemuser', 'k8sapppermission'
    ]
    search_fields = [
        'k8sapppermission__name', 'systemuser__name', 'systemuser__username'
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            systemuser_display=Concat(
                F('systemuser__name'), Value('('), F('systemuser__username'),
                Value(')')
            )
        )
        return queryset
