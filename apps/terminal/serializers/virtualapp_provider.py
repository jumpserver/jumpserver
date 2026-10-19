import re
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from common.const.choices import Status
from assets.models import Platform
from assets.serializers import HostSerializer
from terminal import const
from terminal.automations.deploy_app_provider import default_panda_image
from ..models import AppProvider, AppProviderDeployment

__all__ = [
    'AppProviderSerializer', 'AppProviderContainerSerializer',
    'AppProviderDeploymentSerializer',
]


class AppProviderDeployOptionsSerializer(serializers.Serializer):
    CORE_HOST = serializers.CharField(
        default=settings.SITE_URL or '', max_length=1024, label=_('Core API')
    )
    IGNORE_VERIFY_CERTS = serializers.BooleanField(
        default=True, label=_('Ignore Certificate Verification')
    )
    PANDA_IMAGE = serializers.CharField(
        default='', allow_blank=True, max_length=255, label=_('Panda image')
    )
    PANDA_RANGE_PORTS = serializers.CharField(
        default='6900-7900', max_length=64, label=_('Container port range')
    )

    def get_fields(self):
        fields = super().get_fields()
        # Form metadata only exposes concrete default values.
        fields['PANDA_IMAGE'].default = default_panda_image()
        return fields

    def validate(self, attrs):
        core_host = attrs.get('CORE_HOST')
        if core_host is not None:
            try:
                url = urlsplit(core_host)
                valid = (
                    url.scheme in ('http', 'https') and url.hostname
                    and not any((url.username, url.password, url.query, url.fragment))
                    and (url.port is None or 1 <= url.port <= 65535)
                    and not any(char.isspace() for char in core_host)
                )
            except ValueError:
                valid = False
            if not valid:
                raise serializers.ValidationError({'CORE_HOST': _('Enter a valid HTTP or HTTPS Core URL')})
            attrs['CORE_HOST'] = core_host.rstrip('/')

        image = attrs.get('PANDA_IMAGE')
        if image is not None:
            image = attrs['PANDA_IMAGE'] = image or default_panda_image()
        if image:
            component = r'[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*'
            reference = (
                rf'(?:(?:[a-z0-9][a-z0-9.-]*)(?::[0-9]{{1,5}})?/)?'
                rf'{component}(?:/{component})*'
                r'(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})?(?:@sha256:[a-f0-9]{64})?'
            )
            if not re.fullmatch(reference, image):
                raise serializers.ValidationError({'PANDA_IMAGE': _('Enter a valid Docker image reference')})

        ports = attrs.get('PANDA_RANGE_PORTS')
        if ports is not None:
            match = re.fullmatch(r'([0-9]{1,5})-([0-9]{1,5})', ports)
            start, end = map(int, match.groups()) if match else (0, 0)
            if not 1 <= start < end <= 65535 or start <= 9001 <= end:
                raise serializers.ValidationError({
                    'PANDA_RANGE_PORTS': _('Use a port range between 1 and 65535, excluding the Panda API port 9001')
                })
            attrs['PANDA_RANGE_PORTS'] = f'{start}-{end}'
        return attrs


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
        if not self.instance:
            data.setdefault('nodes_display', ['VirtualAppHosts'])
        if 'protocols' in data or not self.instance:
            ssh_protocol = next(
                (item for item in data.get('protocols', []) if item.get('name') == 'ssh'),
                {'name': 'ssh', 'port': 22},
            )
            data['protocols'] = [ssh_protocol]
        self.initial_data = data
        return super().to_internal_value(data)


class AppProviderSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, max_length=128, label=_('Name'))
    address = serializers.CharField(read_only=True, label=_('Address'))
    host = AppProviderHostSerializer(required=False, allow_null=True, label=_('Host'))
    load = LabeledChoiceField(
        read_only=True, label=_('Load status'), choices=const.ComponentLoad.choices,
    )
    deploy_options = AppProviderDeployOptionsSerializer(
        required=False, label=_('Deploy options')
    )
    deployment = serializers.SerializerMethodField(label=_('Deployment'))
    deployment_error = serializers.SerializerMethodField(label=_('Deployment error'))

    class Meta:
        model = AppProvider
        field_mini = ['id', 'name', 'address']
        read_only_fields = [
            'terminal',
            'date_created', 'date_updated',
        ]
        fields = field_mini + [
            'host',
            'deploy_options', 'deployment', 'deployment_error', 'load', 'terminal', 'comment',
        ] + read_only_fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # DRF validates a nested serializer as though it were creating a new
        # object unless its instance is bound explicitly. Provider updates
        # submit the represented host along with deploy options, so bind the
        # existing host to make UUID/name uniqueness checks update-aware.
        if isinstance(self.instance, AppProvider):
            self.fields['host'].instance = self.instance.host

    @staticmethod
    def get_deployment(instance):
        deployment = instance.latest_deployment
        if not deployment:
            return None
        data = AppProviderDeploymentSerializer(deployment).data
        return {key: data[key] for key in ('id', 'status', 'task', 'date_start', 'date_finished')}

    @staticmethod
    def get_deployment_error(instance):
        def message(detail):
            if isinstance(detail, dict):
                return '; '.join(message(value) for value in detail.values())
            if isinstance(detail, list):
                return '; '.join(message(value) for value in detail)
            return str(detail)

        try:
            instance.validate_deployment()
        except serializers.ValidationError as exc:
            return message(exc.detail)
        return ''

    def validate(self, attrs):
        attrs = super().validate(attrs)
        host = attrs.get('host')
        request = self.context.get('request')
        is_service_account = bool(
            request and getattr(request.user, 'is_service_account', False)
        )
        existing_host = self.instance.host if self.instance else None
        if existing_host and 'host' in attrs and host is None:
            raise serializers.ValidationError({'host': _('The provider host cannot be removed')})
        if host or existing_host:
            host = host or {}
            name = host.get('name', getattr(existing_host, 'name', None))
            address = host.get('address', getattr(existing_host, 'address', None))
            if not name or not address:
                raise serializers.ValidationError({
                    'host': _('Host name and address are required')
                })
            providers = AppProvider.objects.filter(name=name)
            if self.instance:
                providers = providers.exclude(pk=self.instance.pk)
            if providers.exists():
                raise serializers.ValidationError({
                    'host': {'name': _('An application provider with this name already exists')}
                })
            attrs['name'] = name
        elif not self.instance:
            if not is_service_account:
                raise serializers.ValidationError({'host': _('Application provider host is required')})
            if not attrs.get('name'):
                raise serializers.ValidationError({'name': _('This field is required.')})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        host_data = validated_data.pop('host', None)
        if host_data:
            validated_data['host'] = self.fields['host'].create(host_data)
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = AppProvider.objects.select_for_update().get(pk=instance.pk)
        if instance.deployments.filter(publication__isnull=True, status__in=('pending', 'running')).exists():
            raise serializers.ValidationError(_('Wait for the current deployment to finish before editing the provider'))
        self.fields['host'].instance = instance.host
        if 'deploy_options' in validated_data:
            validated_data['deploy_options'] = {**instance.deploy_options, **validated_data['deploy_options']}
        host_data = validated_data.pop('host', None)
        if host_data:
            if instance.host:
                host = self.fields['host'].update(instance.host, host_data)
            else:
                host = self.fields['host'].create(host_data)
            validated_data.update({
                'host': host,
                'name': host.name,
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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        publication = attrs.get('publication')
        if publication:
            raise serializers.ValidationError({'publication': _('Use the application publication API to publish images')})
        return attrs
