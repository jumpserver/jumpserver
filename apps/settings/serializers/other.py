from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class OtherSettingSerializer(serializers.Serializer):
    EMAIL_SUFFIX = serializers.CharField(
        required=False, max_length=1024, label=_("Email suffix"),
        help_text=_('This is used by default if no email is returned during SSO authentication')
    )

    OTP_ISSUER_NAME = serializers.CharField(
        required=False, max_length=16, label=_('OTP issuer name'),
    )
    OTP_VALID_WINDOW = serializers.IntegerField(
        min_value=1, max_value=10,
        label=_("OTP valid window")
    )

    WINDOWS_SSH_DEFAULT_SHELL = serializers.ChoiceField(
        choices=[
            ('cmd', _("CMD")),
            ('powershell', _("PowerShell"))
        ],
        label=_('Shell (Windows)'),
        help_text=_('The shell type used when Windows assets perform ansible tasks')
    )

    PERM_SINGLE_ASSET_TO_UNGROUP_NODE = serializers.BooleanField(
        required=False, label=_("Perm ungroup node"),
        help_text=_("Perm single to ungroup node")
    )

    TICKET_AUTHORIZE_DEFAULT_TIME = serializers.IntegerField(
        min_value=7, max_value=9999, required=False,
        label=_("Ticket authorize default time"), help_text=_("Unit: day")
    )

    HELP_DOCUMENT_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("Help Docs URL"),
        help_text=_('default: http://docs.jumpserver.org')
    )

    HELP_SUPPORT_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("Help Support URL"),
        help_text=_('default: http://www.jumpserver.org/support/')
    )

    # 准备废弃
    # PERIOD_TASK_ENABLED = serializers.BooleanField(
    #     required=False, label=_("Enable period task")
    # )

