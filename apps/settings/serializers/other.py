from abc import ABCMeta

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class OtherSettingSerializer(serializers.Serializer):
    OTP_ISSUER_NAME = serializers.CharField(
        required=False, max_length=1024, label=_('OTP issuer name'),
    )
    OTP_VALID_WINDOW = serializers.IntegerField(label=_("OTP valid window"))

    PERIOD_TASK_ENABLED = serializers.BooleanField(required=False, label=_("Enable period task"))
    WINDOWS_SSH_DEFAULT_SHELL = serializers.CharField(
        required=False, max_length=1024, label=_('Ansible windows default shell')
    )

    EMAIL_SUFFIX = serializers.CharField(required=False, max_length=1024, label=_("Email suffix"))

    PERM_SINGLE_ASSET_TO_UNGROUP_NODE = serializers.BooleanField(
        required=False, label=_("Perm single to ungroup node")
    )


