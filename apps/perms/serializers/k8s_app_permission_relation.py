# coding: utf-8
#
from perms.serializers.base import PermissionAllUserSerializer
from rest_framework import serializers

from common.drf.serializers import BulkModelSerializer

from .. import models


class K8sAppPermissionUserRelationSerializer(BulkModelSerializer):
    user_display = serializers.ReadOnlyField()
    k8sapppermission_display = serializers.ReadOnlyField()

    class Meta:
        model = models.K8sAppPermission.users.through
        fields = [
            'id', 'user', 'user_display', 'k8sapppermission',
            'k8sapppermission_display'
        ]


class K8sAppPermissionUserGroupRelationSerializer(BulkModelSerializer):
    usergroup_display = serializers.ReadOnlyField()
    k8sapppermission_display = serializers.ReadOnlyField()

    class Meta:
        model = models.K8sAppPermission.user_groups.through
        fields = [
            'id', 'usergroup', 'usergroup_display', 'k8sapppermission',
            'k8sapppermission_display'
        ]


class K8sAppPermissionAllUserSerializer(PermissionAllUserSerializer):
    class Meta(PermissionAllUserSerializer.Meta):
        pass


class K8sAppPermissionK8sAppRelationSerializer(BulkModelSerializer):
    k8sapp_display = serializers.ReadOnlyField()
    k8sapppermission_display = serializers.ReadOnlyField()

    class Meta:
        model = models.K8sAppPermission.k8s_apps.through
        fields = [
            'id', "k8sapp", "k8sapp_display", 'k8sapppermission',
            'k8sapppermission_display'
        ]


class K8sAppPermissionAllK8sAppSerializer(serializers.Serializer):
    k8sapp = serializers.UUIDField(read_only=True, source='id')
    k8sapp_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'name']

    @staticmethod
    def get_k8sapp_display(obj):
        return str(obj)


class K8sAppPermissionSystemUserRelationSerializer(BulkModelSerializer):
    systemuser_display = serializers.ReadOnlyField()
    k8sapppermission_display = serializers.ReadOnlyField()

    class Meta:
        model = models.K8sAppPermission.system_users.through
        fields = [
            'id', 'systemuser', 'systemuser_display', 'k8sapppermission',
            'k8sapppermission_display'
        ]
