from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from common.drf.fields import ObjectRelatedField, LabeledChoiceField
from assets.models import Host, Platform
from assets.serializers import HostSerializer
from orgs.utils import tmp_to_builtin_org
from ..models import Applet, AppletPublication, AppletHost, AppletHostDeployment


__all__ = [
    'AppletSerializer', 'AppletPublicationSerializer',
    'AppletHostSerializer', 'AppletHostDeploymentSerializer',
    'AppletUploadSerializer'
]


class AppletSerializer(serializers.ModelSerializer):
    icon = serializers.ReadOnlyField(label=_("Icon"))
    type = LabeledChoiceField(choices=Applet.Type.choices, label=_("Type"))

    class Meta:
        model = Applet
        fields_mini = ['id', 'name', 'display_name']
        read_only_fields = [
            'icon', 'date_created', 'date_updated'
        ]
        fields = fields_mini + [
            'version', 'author', 'type', 'protocols',
            'tags', 'comment'
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
    host = HostSerializer(allow_null=True, required=False)

    class Meta:
        model = AppletHost
        fields_mini = ['id', 'host']
        read_only_fields = ['date_synced', 'status', 'date_created', 'date_updated']
        fields = fields_mini + ['comment', 'account_automation'] + read_only_fields

    def __init__(self, *args, **kwargs):
        self.host_data = kwargs.get('data', {}).pop('host', {})
        super().__init__(*args, **kwargs)

    def _create_host(self):
        platform = Platform.objects.get(name='RemoteAppHost')
        data = {
            **self.host_data,
            'platform': platform.id,
            'nodes_display': [
                'RemoteAppHosts'
            ]
        }
        serializer = HostSerializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError:
            raise serializers.ValidationError({'host': serializer.errors})
        host = serializer.save()
        return host

    def create(self, validated_data):
        with tmp_to_builtin_org(system=1):
            host = self._create_host()
        instance = super().create({**validated_data, 'host': host})
        return instance


class AppletHostDeploymentSerializer(serializers.ModelSerializer):
    host = ObjectRelatedField(queryset=AppletHost.objects.all())

    class Meta:
        model = AppletHostDeployment
        fields_mini = ['id', 'host']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + [
            'status', 'comment',
        ] + read_only_fields
