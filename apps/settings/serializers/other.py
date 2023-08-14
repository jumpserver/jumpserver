from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class OtherSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('More...')

    PERM_SINGLE_ASSET_TO_UNGROUP_NODE = serializers.BooleanField(
        required=False, label=_("Perm ungroup node"),
        help_text=_("Perm single to ungroup node")
    )

    TICKET_AUTHORIZE_DEFAULT_TIME = serializers.IntegerField(
        min_value=1, max_value=999999, required=False,
        label=_("Ticket authorize default time")
    )
    TICKET_AUTHORIZE_DEFAULT_TIME_UNIT = serializers.ChoiceField(
        choices=[('day', _("day")), ('hour', _("hour"))],
        label=_("Ticket authorize default time unit"), required=False,
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
