
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


class ComponentsStateSerializer(serializers.Serializer):
    # system
    system_cpu_load_1 = serializers.FloatField(
        required=False, label=_("System cpu load (1 minutes)")
    )
    system_memory_used_percent = serializers.FloatField(
        required=False, label=_('System memory used percent')
    )
    system_disk_used_percent = serializers.FloatField(
        required=False, label=_('System disk used percent')
    )
    # sessions
    session_active_count = serializers.IntegerField(
        required=False, label=_("Session active count")
    )

    def save(self, **kwargs):
        request = self.context['request']
        terminal = request.user.terminal
        terminal.state = self.validated_data
