from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['OtherSettingSerializer']


class OtherSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('More...')

    PERM_SINGLE_ASSET_TO_UNGROUP_NODE = serializers.BooleanField(
        required=False, label=_("Perm ungroup node"),
        help_text=_("Perm single to ungroup node")
    )

    # 准备废弃
    # PERIOD_TASK_ENABLED = serializers.BooleanField(
    #     required=False, label=_("Enable period task")
    # )
