from tickets.models import ApplyLoginAssetTicket
from .ticket import TicketApplySerializer

__all__ = [
    'LoginAssetConfirmSerializer'
]


class LoginAssetConfirmSerializer(TicketApplySerializer):
    class Meta:
        model = ApplyLoginAssetTicket
        writeable_fields = ['apply_login_user', 'apply_login_asset', 'apply_login_account']
        fields = TicketApplySerializer.Meta.fields + writeable_fields
