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
    'AppletHostStartupSerializer', 'AppletSetupSerializer'
]


class DeployOptionsSerializer(serializers.Serializer):
    LICENSE_MODE_CHOICES = (
        (2, _('Per Device (Device number limit)')),
        (4, _('Per User (User number limit)')),
    )

    # 单用户单会话，
    # 默认值为1，表示启用状态（组策略默认值），此时单用户只能有一个会话连接
    # 如果改为 0 ，表示禁用状态，此时可以单用户多会话连接
    SESSION_PER_USER = (
        (0, _("Disabled")),
        (1, _("Enabled")),
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
    RDS_Licensing = serializers.BooleanField(
        default=False, label=_("Existing RDS license"),
        help_text=_(
            'If not exist, the RDS will be in trial mode, and the trial period is 120 days. <a '
            'href="https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/rds-client-access'
            '-license">Detail</a>'
        )
    )
    RDS_LicenseServer = serializers.CharField(default='127.0.0.1', label=_('RDS License Server'), max_length=1024)
    RDS_LicensingMode = serializers.ChoiceField(
        choices=LICENSE_MODE_CHOICES, default=2, label=_('RDS Licensing Mode'),
    )
    RDS_fSingleSessionPerUser = serializers.ChoiceField(
        choices=SESSION_PER_USER, default=1, label=_("RDS Single Session Per User"),
        help_text=_('Tips: A RDS user can have only one session at a time. If set, when next login connected, '
                    'previous session will be disconnected.')
    )
    RDS_MaxDisconnectionTime = serializers.IntegerField(
        default=60000, label=_("RDS Max Disconnection Time (ms)"),
        help_text=_(
            'Tips: Set the maximum duration for keeping a disconnected session active on the server (log off the '
            'session after 60000 milliseconds).'
        )
    )
    RDS_RemoteAppLogoffTimeLimit = serializers.IntegerField(
        default=0, label=_("RDS Remote App Logoff Time Limit (ms)"),
        help_text=_(
            'Tips: Set the logoff time for RemoteApp sessions after closing all RemoteApp programs (0 milliseconds, '
            'log off the session immediately).'
        )
    )


class AppletHostSerializer(HostSerializer):
    deploy_options = DeployOptionsSerializer(required=False, label=_("Deploy options"))
    load = LabeledChoiceField(
        read_only=True, label=_('Load status'), choices=const.ComponentLoad.choices,
    )

    class Meta(HostSerializer.Meta):
        model = AppletHost
        fields = HostSerializer.Meta.fields + [
            'auto_create_accounts', 'accounts_create_amount',
            'load', 'date_synced', 'deploy_options', 'using_same_account',
        ]
        extra_kwargs = {
            **HostSerializer.Meta.extra_kwargs,
            'date_synced': {'read_only': True},
            'auto_create_accounts': {
                'help_text': _(
                    'These accounts are used to connect to the published application, '
                    'the account is now divided into two types, one is dedicated to each account, '
                    'each user has a private account, the other is public, '
                    'when the application does not support multiple open and the special has been used, '
                    'the public account will be used to connect'
                )
            },
            'accounts_create_amount': {'help_text': _('The number of public accounts created automatically')},
            'using_same_account': {
                'help_text': _(
                    'Connect to the host using the same account first. For security reasons, please set the '
                    'configuration item CACHE_LOGIN_PASSWORD_ENABLED=true and restart the service to enable it.'
                )
            }
        }

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
    pass


class AppletSetupSerializer(serializers.Serializer):
    hosts = serializers.ListField(child=serializers.UUIDField(label=_('Host ID')), label=_('Hosts'))
    applet_id = serializers.UUIDField(label=_('Applet ID'))
