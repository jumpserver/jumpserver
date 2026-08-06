from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from common.serializers.fields import ObjectRelatedField
from common.const.choices import Status
from assets.models import Host
from terminal import const
from ..models import AppProvider, AppProviderDeployment

__all__ = [
    'AppProviderSerializer', 'AppProviderContainerSerializer',
    'AppProviderDeploymentSerializer',
]


class AppProviderDeployOptionsSerializer(serializers.Serializer):
    CORE_HOST = serializers.CharField(
        default=settings.SITE_URL, max_length=1024, label=_('Core API')
    )
    IGNORE_VERIFY_CERTS = serializers.BooleanField(
        default=True, label=_('Ignore Certificate Verification')
    )
    PANDA_IMAGE = serializers.CharField(
        default='jumpserver/panda:latest', max_length=255, label=_('Panda image')
    )
    PANDA_RANGE_PORTS = serializers.CharField(
        default='6900-7900', max_length=64, label=_('Container port range')
    )


class AppProviderSerializer(serializers.ModelSerializer):
    host = ObjectRelatedField(
        queryset=Host.objects.all(), required=False, allow_null=True,
        attrs=('id', 'name', 'address'), label=_('Host'),
    )
    load = LabeledChoiceField(
        read_only=True, label=_('Load status'), choices=const.ComponentLoad.choices,
    )
    deploy_options = AppProviderDeployOptionsSerializer(
        required=False, label=_('Deploy options')
    )

    class Meta:
        model = AppProvider
        field_mini = ['id', 'name', 'hostname']
        read_only_fields = [
            'terminal', 'date_created', 'date_updated',
        ]
        fields = field_mini + [
            'host', 'runtime_type', 'connection_mode', 'service_url',
            'deploy_options', 'load', 'terminal',
        ] + read_only_fields


class AppProviderContainerSerializer(serializers.Serializer):
    container_id = serializers.CharField(label=_('Container ID'))
    container_image = serializers.CharField(label=_('Container Image'))
    container_name = serializers.CharField(label=_('Container Name'))
    container_status = serializers.CharField(label=_('Container Status'))
    container_ports = serializers.ListField(child=serializers.CharField(), label=_('Container Ports'))


class AppProviderDeploymentSerializer(serializers.ModelSerializer):
    status = LabeledChoiceField(
        choices=Status.choices, read_only=True, label=_('Status')
    )

    class Meta:
        model = AppProviderDeployment
        fields = [
            'id', 'provider', 'publication', 'status', 'task', 'comment',
            'date_start', 'date_finished', 'date_created', 'date_updated',
        ]
        read_only_fields = [
            'status', 'task', 'date_start', 'date_finished',
            'date_created', 'date_updated',
        ]

    def validate_provider(self, provider):
        if not provider.host:
            raise serializers.ValidationError(_('Provider host is required before deployment'))
        if provider.runtime_type != AppProvider.RuntimeType.docker:
            raise serializers.ValidationError(_('Only Docker runtime deployment is currently supported'))
        return provider

    def validate(self, attrs):
        attrs = super().validate(attrs)
        provider = attrs.get('provider')
        publication = attrs.get('publication')
        if publication and publication.provider_id != provider.id:
            raise serializers.ValidationError(
                {'publication': _('Publication does not belong to this provider')}
            )
        return attrs
