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

__all__ = [
    'AppletHostSerializer', 'AppletHostDeploymentSerializer',
    'AppletHostAccountSerializer', 'AppletHostAppletReportSerializer',
    'AppletHostStartupSerializer', 'AppletHostDeployAppletSerializer'
]


class DeployOptionsSerializer(serializers.Serializer):
    LICENSE_MODE_CHOICES = (
        (4, _('Per Session')),
        (2, _('Per Device')),
    )
    SESSION_PER_USER = (
        (1, _("Disabled")),
        (0, _("Enabled")),
    )

    CORE_HOST = serializers.CharField(
        default=settings.SITE_URL, label=_('Core API'), max_length=1024,
        help_text=_(""" 
        Tips: The application release machine communicates with the Core service. 
        If the release machine and the Core service are on the same network segment, 
        it is recommended to fill in the intranet address, otherwise fill in the current site URL 
        <br> 
        eg: https://172.16.10.110 or https://dev.jumpserver.com 
        """) 
    )
    IGNORE_VERIFY_CERTS = serializers.BooleanField(default=True, label=_("Ignore Certificate Verification"))
    RDS_Licensing = serializers.BooleanField(default=False, label=_("Existing RDS license"))
    RDS_LicenseServer = serializers.CharField(default='127.0.0.1', label=_('RDS License Server'), max_length=1024)
    RDS_LicensingMode = serializers.ChoiceField(choices=LICENSE_MODE_CHOICES, default=2, label=_('RDS Licensing Mode'))
    RDS_fSingleSessionPerUser = serializers.ChoiceField(choices=SESSION_PER_USER, default=1,
                                                        label=_("RDS Single Session Per User"))
    RDS_MaxDisconnectionTime = serializers.IntegerField(default=60000, label=_("RDS Max Disconnection Time"))
    RDS_RemoteAppLogoffTimeLimit = serializers.IntegerField(default=0, label=_("RDS Remote App Logoff Time Limit"))


class AppletHostSerializer(HostSerializer):
    deploy_options = DeployOptionsSerializer(required=False, label=_("Deploy options"))
    load = LabeledChoiceField(
        read_only=True, label=_('Load status'), choices=const.ComponentLoad.choices,
    )

    class Meta(HostSerializer.Meta):
        model = AppletHost
        fields = HostSerializer.Meta.fields + [
            'load', 'date_synced', 'deploy_options'
        ]
        extra_kwargs = {
            **HostSerializer.Meta.extra_kwargs,
            'date_synced': {'read_only': True}
        }

    def __init__(self, *args, data=None, **kwargs):
        if data:
            self.set_initial_data(data)
            kwargs['data'] = data
        super().__init__(*args, **kwargs)

    @staticmethod
    def set_initial_data(data):
        platform = Platform.objects.get(name='RemoteAppHost')
        data.update({
            'platform': platform.id,
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

    class Meta:
        model = AppletHostDeployment
        fields_mini = ['id', 'host', 'status', 'task']
        read_only_fields = [
            'status', 'date_created', 'date_updated',
            'date_start', 'date_finished'
        ]
        fields = fields_mini + ['comment'] + read_only_fields


class AppletHostDeployAppletSerializer(AppletHostDeploymentSerializer):
    applet_id = serializers.UUIDField(write_only=True, allow_null=True, required=False)

    class Meta(AppletHostDeploymentSerializer.Meta):
        fields = AppletHostDeploymentSerializer.Meta.fields + ['applet_id']


class AppletHostAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'username', 'secret', 'is_active', 'date_updated']


class AppletHostAppletReportSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    version = serializers.CharField()


class AppletHostStartupSerializer(serializers.Serializer):
    pass
