from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class OtherSettingSerializer(serializers.Serializer):
    EMAIL_SUFFIX = serializers.CharField(
        required=False, max_length=1024, label=_("Email suffix"),
        help_text=_('This is used by default if no email is returned during SSO authentication')
    )
    TICKETS_ENABLED = serializers.BooleanField(required=False, default=True, label=_("Enable tickets"))

    OTP_ISSUER_NAME = serializers.CharField(
        required=False, max_length=1024, label=_('OTP issuer name'),
    )
    OTP_VALID_WINDOW = serializers.IntegerField(label=_("OTP valid window"))

    PERIOD_TASK_ENABLED = serializers.BooleanField(required=False, label=_("Enable period task"))
    WINDOWS_SSH_DEFAULT_SHELL = serializers.ChoiceField(
        choices=[
            ('cmd', _("CMD")),
            ('powershell', _("PowerShell"))
        ],
        label=_('Shell (Windows)'),
        help_text=_('The shell type used when Windows assets perform ansible tasks')
    )

    PERM_SINGLE_ASSET_TO_UNGROUP_NODE = serializers.BooleanField(
        required=False, label=_("Perm single to ungroup node")
    )


