from tickets.models import ApplyLoginTicket
from .ticket import TicketApplySerializer

__all__ = [
    'LoginReviewSerializer'
]


class LoginReviewSerializer(TicketApplySerializer):
    class Meta(TicketApplySerializer.Meta):
        model = ApplyLoginTicket
        writeable_fields = ['apply_login_ip', 'apply_login_city', 'apply_login_datetime']
        fields = TicketApplySerializer.Meta.fields + writeable_fields
