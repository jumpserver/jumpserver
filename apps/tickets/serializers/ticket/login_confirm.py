from tickets.models import ApplyLoginTicket
from .ticket import TicketApplySerializer

__all__ = [
    'LoginConfirmSerializer'
]


class LoginConfirmSerializer(TicketApplySerializer):
    class Meta:
        model = ApplyLoginTicket
        fields = TicketApplySerializer.Meta.fields + [
            'apply_login_ip', 'apply_login_city', 'apply_login_datetime'
        ]
