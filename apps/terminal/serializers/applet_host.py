from urllib.parse import urlsplit

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import Account
from assets.models import Platform
from assets.serializers import HostSerializer
from common.const.choices import Status
from common.serializers.fields import LabeledChoiceField
from common.validators import ProjectUniqueValidator
from .applet import AppletSerializer
from .. import const
from ..models import AppletHost, AppletHostDeployment
from ..utils.tinker import get_tinker_version_status, get_tinker_upgrade_message

__all__ = [
    'AppletHostSerializer', 'AppletHostDeploymentSerializer',
    'AppletHostAccountSerializer', 'AppletHostAppletReportSerializer',
    'AppletHostStartupSerializer', 'AppletSetupSerializer'
]


class DeployOptionsSerializer(serializers.Serializer):
    CORE_HOST = serializers.CharField(
        default=settings.SITE_URL, label=_('Core API'), max_length=1024,
        help_text=_(""" 
        Tips: The application release machine communicates with the Core service. 
        If the release machine and the Core service are on the same network segment, 
        it is recommended to fill in the intranet address, otherwise fill in the current site URL 
        <br> 
        eg: https://172.16.10.110 or https://dev.example.com
        """)
    )
    IGNORE_VERIFY_CERTS = serializers.BooleanField(default=True, label=_("Ignore Certificate Verification"))
    RDS_LICENSE_SERVER = serializers.CharField(
        default='', allow_blank=True, label=_('RDS License Server'), max_length=1024,
    )

    def to_internal_value(self, data):
        instance = getattr(self.parent, 'instance', None)
        if instance is not None and isinstance(data, dict):
            # Keep saved connection settings before PUT defaults are applied.
            # The declared serializer fields still filter out retired options.
            data = {**(instance.deploy_options or {}), **data}
        return super().to_internal_value(data)

    def validate(self, attrs):
        instance = getattr(self.parent, 'instance', None)
        options = {**(getattr(instance, 'deploy_options', None) or {}), **attrs}
        try:
            core = urlsplit(options.get('CORE_HOST', settings.SITE_URL))
        except ValueError:
            raise serializers.ValidationError(_('Invalid Core URL.'))
        if (core.scheme not in ('http', 'https') or not core.netloc or core.username is not None
                or core.query or core.fragment):
            raise serializers.ValidationError(_(
                'Invalid Core URL.'
            ))
        return attrs


class AppletHostSerializer(HostSerializer):
    tinker_min_version = serializers.SerializerMethodField()
    tinker_target_version = serializers.SerializerMethodField()
    tinker_version_status = serializers.SerializerMethodField()
    tinker_upgrade_message = serializers.SerializerMethodField()
    deploy_options = DeployOptionsSerializer(required=False, label=_("Deploy options"))
    load = LabeledChoiceField(
        read_only=True, label=_('Load status'), choices=const.ComponentLoad.choices,
    )

    class Meta(HostSerializer.Meta):
        model = AppletHost
        fields = HostSerializer.Meta.fields + [
            'load', 'date_synced', 'deploy_options',
            'tinker_version', 'tinker_target_version', 'tinker_version_status',
            'tinker_min_version', 'tinker_upgrade_message',
        ]
        extra_kwargs = {
            **HostSerializer.Meta.extra_kwargs,
            'date_synced': {'read_only': True},
            'tinker_version': {'read_only': True},
        }

    def get_tinker_min_version(self, obj):
        return const.TINKER_MIN_VERSION

    def get_tinker_target_version(self, obj):
        return const.TINKER_TARGET_VERSION

    def get_tinker_version_status(self, obj):
        return get_tinker_version_status(obj.tinker_version)

    def get_tinker_upgrade_message(self, obj):
        return get_tinker_upgrade_message(obj.tinker_version)

    def update(self, instance, validated_data):
        if 'deploy_options' in validated_data:
            # Retired options remain historical data, but only declared fields
            # from the request may change the stored deployment configuration.
            validated_data['deploy_options'] = {
                **(instance.deploy_options or {}), **validated_data['deploy_options'],
            }
        return super().update(instance, validated_data)

    def __init__(self, *args, data=None, **kwargs):
        if data:
            self.set_initial_data(data)
            kwargs['data'] = data
        super().__init__(*args, **kwargs)

    def set_initial_data(self, data):
        platform_id = None
        platform_data = data.get('platform')

        if isinstance(platform_data, dict):
            platform_id = platform_data.get('id')
        elif isinstance(platform_data, int):
            platform_id = platform_data

        default_platform = Platform.objects.get(name='RemoteAppHost')
        if (
                not platform_id or
                not Platform.objects.filter(
                    id=platform_id, name__startswith='RemoteAppHost'
                ).exists()
        ):
            platform_id = default_platform.id

        data.update({
            'platform': platform_id,
            'nodes_display': [
                'RemoteAppHosts'
            ]
        })

    def get_validators(self):
        validators = super().get_validators()
        # 不知道为啥没有继承过来
        uniq_validator = ProjectUniqueValidator(
            queryset=AppletHost.objects.all(),
            fields=('org_id', 'name')
        )
        validators.append(uniq_validator)
        return validators


class HostAppletSerializer(AppletSerializer):
    publication = serializers.SerializerMethodField()

    class Meta(AppletSerializer.Meta):
        fields = AppletSerializer.Meta.fields + ['publication']


class AppletHostDeploymentSerializer(serializers.ModelSerializer):
    status = LabeledChoiceField(choices=Status.choices, label=_('Status'), default=Status.pending)
    install_applets = serializers.BooleanField(default=True, label=_('Install applets'), write_only=True)

    class Meta:
        model = AppletHostDeployment
        fields_mini = ['id', 'host', 'status', 'task']
        read_only_fields = [
            'status', 'date_created', 'date_updated',
            'date_start', 'date_finished'
        ]
        write_only_fields = ['install_applets', ]
        fields = fields_mini + ['comment'] + read_only_fields + write_only_fields


class AppletHostAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'username', 'secret', 'is_active', 'date_updated']


class AppletHostAppletReportSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    version = serializers.CharField()


class AppletHostStartupSerializer(serializers.Serializer):
    version = serializers.CharField(required=False, allow_blank=True, default='', max_length=32)


class AppletSetupSerializer(serializers.Serializer):
    hosts = serializers.ListField(child=serializers.UUIDField(label=_('Host ID')), label=_('Hosts'))
    applet_id = serializers.UUIDField(label=_('Applet ID'))
