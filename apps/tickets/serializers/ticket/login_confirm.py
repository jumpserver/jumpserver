from tickets.models import ApplyLoginTicket
from .ticket import TicketApplySerializer

__all__ = [
    'LoginConfirmSerializer'
]


class LoginConfirmSerializer(TicketApplySerializer):
    class Meta(TicketApplySerializer.Meta):
        model = ApplyLoginTicket
        writeable_fields = ['apply_login_ip', 'apply_login_city', 'apply_login_datetime']
        fields = TicketApplySerializer.Meta.fields + writeable_fields
