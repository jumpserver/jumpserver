from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = [
    'ApplySerializer', 'CommandConfirmSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_run_user = serializers.CharField(required=True, label=_('Run user'))
    apply_run_asset = serializers.CharField(required=True, label=_('Run asset'))
    apply_run_system_user = serializers.CharField(
        required=True, max_length=64, label=_('Run system user')
    )
    apply_run_command = serializers.CharField(required=True, label=_('Run command'))
    apply_from_session_id = serializers.UUIDField(required=False, label=_('From session'))
    apply_from_cmd_filter_rule_id = serializers.UUIDField(
        required=False, label=_('From cmd filter rule')
    )
    apply_from_cmd_filter_id = serializers.UUIDField(required=False, label=_('From cmd filter'))


class CommandConfirmSerializer(ApplySerializer):
    pass
