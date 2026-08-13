from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from common.const.choices import Status
from assets.models import Platform
from assets.serializers import HostSerializer
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


class AppProviderHostSerializer(HostSerializer):
    """Host-shaped input for an application provider.

    The platform and SSH protocol are server-controlled so every managed
    provider is deployable without trusting UI defaults.
    """

    def to_internal_value(self, data):
        data = data.copy()
        # The update form posts the represented host object, including its
        # existing UUID. This nested serializer is validated before the
        # provider update method binds `instance.host`, so AssetSerializer's
        # UUID uniqueness validator would otherwise treat it as a new asset.
        # Host identity is controlled by the provider relation below; clients
        # must not create or replace it by posting an id.
        data.pop('id', None)
        platform = Platform.objects.get(name='VirtualAppHost', internal=True)
        data['platform'] = platform.id
        data.setdefault('nodes_display', ['VirtualAppHosts'])
        ssh_protocol = next(
            (item for item in data.get('protocols', []) if item.get('name') == 'ssh'),
            {'name': 'ssh', 'port': 22},
        )
        data['protocols'] = [ssh_protocol]
        self.initial_data = data
        self._extract_accounts()
        return super().to_internal_value(data)


class AppProviderSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, max_length=128, label=_('Name'))
    hostname = serializers.CharField(required=False, max_length=128, label=_('Hostname'))
    host = AppProviderHostSerializer(required=False, allow_null=True, label=_('Host'))
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
            'runtime_type', 'connection_mode', 'service_url', 'terminal',
            'date_created', 'date_updated',
        ]
        fields = field_mini + [
            'host', 'runtime_type', 'connection_mode', 'service_url',
            'deploy_options', 'load', 'terminal', 'comment',
        ] + read_only_fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # DRF validates a nested serializer as though it were creating a new
        # object unless its instance is bound explicitly. Provider updates
        # submit the represented host along with deploy options, so bind the
        # existing host to make UUID/name uniqueness checks update-aware.
        if self.instance and not isinstance(self.instance, (list, tuple)):
            self.fields['host'].instance = self.instance.host

    def validate(self, attrs):
        attrs = super().validate(attrs)
        host = attrs.get('host')
        request = self.context.get('request')
        is_service_account = bool(
            request and getattr(request.user, 'is_service_account', False)
        )
        if host:
            providers = AppProvider.objects.filter(name=host['name'])
            if self.instance:
                providers = providers.exclude(pk=self.instance.pk)
            if providers.exists():
                raise serializers.ValidationError({
                    'host': {'name': _('An application provider with this name already exists')}
                })
            attrs['name'] = host['name']
            attrs['hostname'] = host['address']
            attrs['runtime_type'] = AppProvider.RuntimeType.docker
            attrs['connection_mode'] = AppProvider.ConnectionMode.ssh
        elif not self.instance:
            if not is_service_account:
                raise serializers.ValidationError({
                    'host': _('Application provider host is required')
                })
            if not attrs.get('name') or not attrs.get('hostname'):
                raise serializers.ValidationError({
                    'host': _('Legacy provider registration requires name and hostname')
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        host_data = validated_data.pop('host', None)
        if host_data:
            validated_data['host'] = self.fields['host'].create(host_data)
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        host_data = validated_data.pop('host', None)
        if host_data:
            if instance.host:
                host = self.fields['host'].update(instance.host, host_data)
            else:
                host = self.fields['host'].create(host_data)
            validated_data.update({
                'host': host,
                'name': host.name,
                'hostname': host.address,
                'runtime_type': AppProvider.RuntimeType.docker,
                'connection_mode': AppProvider.ConnectionMode.ssh,
            })
        return super().update(instance, validated_data)


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
