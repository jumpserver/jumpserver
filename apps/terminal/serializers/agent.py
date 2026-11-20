from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from terminal.const import AgentActionKind, AgentActionStatus, AgentSessionStatus


class AgentAuditSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True, allow_null=True, label=_('User ID'))
    user_display = serializers.CharField(read_only=True, label=_('User'))
    org_id = serializers.UUIDField(read_only=True)
    client_id = serializers.CharField(read_only=True, label=_('Client ID'))
    asset_id = serializers.CharField(read_only=True, allow_null=True, label=_('Asset ID'))
    account = serializers.CharField(read_only=True, allow_null=True, label=_('Account'))
    protocol = serializers.CharField(max_length=16, read_only=True, label=_('Protocol'))
    date_created = serializers.DateTimeField(read_only=True, label=_('Date created'))


class AgentSessionAuditSerializer(AgentAuditSerializer):
    status = serializers.ChoiceField(
        choices=AgentSessionStatus.choices, read_only=True, label=_('Status')
    )
    terminal_session_id = serializers.UUIDField(
        read_only=True, allow_null=True, label=_('Session ID')
    )
    date_expires = serializers.DateTimeField(read_only=True, label=_('Date expired'))


class AgentActionAuditSerializer(AgentAuditSerializer):
    kind = serializers.ChoiceField(
        choices=AgentActionKind.choices, read_only=True, label=_('Operation')
    )
    status = serializers.ChoiceField(
        choices=AgentActionStatus.choices, read_only=True, label=_('Status')
    )
    session_id = serializers.UUIDField(read_only=True, label=_('Session ID'))
    date_started = serializers.DateTimeField(read_only=True, allow_null=True, label=_('Date start'))
    date_finished = serializers.DateTimeField(read_only=True, allow_null=True, label=_('Date end'))
