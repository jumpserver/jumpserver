from rest_framework import serializers

from common.drf.fields import ObjectRelatedField
from assets.models import Host
from ..models import Applet, AppletPublication, AppletHost, AppletHostDeployment


__all__ = [
    'AppletSerializer', 'AppletPublicationSerializer',
    'AppletHostSerializer', 'AppletHostDeploymentSerializer',
    'AppletUploadSerializer'
]


class AppletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applet
        fields_mini = ['id', 'name']
        read_only_fields = [
            'date_created', 'date_updated'
        ]
        fields = fields_mini + [
            'version', 'author', 'type', 'protocols', 'comment'
        ] + read_only_fields


class AppletUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class AppletPublicationSerializer(serializers.ModelSerializer):
    applet = ObjectRelatedField(queryset=Applet.objects.all())
    host = ObjectRelatedField(queryset=AppletHost.objects.all())

    class Meta:
        model = AppletPublication
        fields_mini = ['id', 'applet', 'host']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + [
            'status', 'comment',
        ] + read_only_fields


class AppletHostSerializer(serializers.ModelSerializer):
    host = ObjectRelatedField(queryset=Host.objects.all())

    class Meta:
        model = AppletHost
        fields_mini = ['id', 'host']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + [
            'comment', 'account_automation', 'date_synced', 'status',
        ] + read_only_fields


class AppletHostDeploymentSerializer(serializers.ModelSerializer):
    host = ObjectRelatedField(queryset=AppletHost.objects.all())

    class Meta:
        model = AppletHostDeployment
        fields_mini = ['id', 'host']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + [
            'status', 'comment',
        ] + read_only_fields
