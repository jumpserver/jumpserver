from tickets.models import ApplyLoginAssetTicket
from .ticket import TicketApplySerializer

__all__ = [
    'LoginAssetConfirmSerializer'
]


class LoginAssetConfirmSerializer(TicketApplySerializer):
    class Meta:
        model = ApplyLoginAssetTicket
        fields = TicketApplySerializer.Meta.fields + [
            'apply_login_user', 'apply_login_asset', 'apply_login_system_user'
        ]
