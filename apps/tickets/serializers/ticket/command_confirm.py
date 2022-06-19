from tickets.models import ApplyCommandTicket
from .ticket import TicketApplySerializer

__all__ = [
    'ApplyCommandConfirmSerializer',
]


class ApplyCommandConfirmSerializer(TicketApplySerializer):
    class Meta:
        model = ApplyCommandTicket
        fields = TicketApplySerializer.Meta.fields + [
            'apply_run_user', 'apply_run_asset', 'apply_run_system_user',
            'apply_run_command', 'apply_from_session', 'apply_from_cmd_filter',
            'apply_from_cmd_filter_rule'
        ]
