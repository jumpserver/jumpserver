from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from common.drf.fields import ObjectRelatedField, LabeledChoiceField
from common.validators import ProjectUniqueValidator
from assets.models import Platform
from assets.serializers import HostSerializer
from ..models import Applet, AppletPublication, AppletHost, AppletHostDeployment


__all__ = [
    'AppletSerializer', 'AppletPublicationSerializer',
    'AppletHostSerializer', 'AppletHostDeploymentSerializer',
    'AppletUploadSerializer',
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


class DeployOptionsSerializer(serializers.Serializer):
    LICENSE_MODE_CHOICES = (
        (4, _('Per Session')),
        (2, _('Per Device')),
    )
    SESSION_PER_USER = (
        (1, _("Disabled")),
        (0, _("Enabled")),
    )
    RDS_Licensing = serializers.BooleanField(default=False, label=_("RDS Licensing"))
    RDS_LicenseServer = serializers.CharField(default='127.0.0.1', label=_('RDS License Server'), max_length=1024)
    RDS_LicensingMode = serializers.ChoiceField(choices=LICENSE_MODE_CHOICES, default=4, label=_('RDS Licensing Mode'))
    RDS_fSingleSessionPerUser = serializers.ChoiceField(choices=SESSION_PER_USER, default=1, label=_("RDS fSingleSessionPerUser"))
    RDS_MaxDisconnectionTime = serializers.IntegerField(default=60000, label=_("RDS Max Disconnection Time"))
    RDS_RemoteAppLogoffTimeLimit = serializers.IntegerField(default=0, label=_("RDS Remote App Logoff Time Limit"))


class AppletHostSerializer(HostSerializer):
    deploy_options = DeployOptionsSerializer(required=False, label=_("Deploy options"))

    class Meta(HostSerializer.Meta):
        model = AppletHost
        fields = HostSerializer.Meta.fields + [
            'account_automation', 'status', 'date_synced', 'deploy_options'
        ]
        extra_kwargs = {
            'status': {'read_only': True},
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


class AppletHostDeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppletHostDeployment
        fields_mini = ['id', 'host', 'status']
        read_only_fields = [
            'status', 'date_created', 'date_updated',
            'date_start', 'date_finished'
        ]
        fields = fields_mini + ['comment'] + read_only_fields
