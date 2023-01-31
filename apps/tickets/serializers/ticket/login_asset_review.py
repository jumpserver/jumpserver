from tickets.models import ApplyLoginAssetTicket
from .ticket import TicketApplySerializer

__all__ = [
    'LoginAssetReviewSerializer'
]


class LoginAssetReviewSerializer(TicketApplySerializer):
    class Meta:
        model = ApplyLoginAssetTicket
        writeable_fields = ['apply_login_user', 'apply_login_asset', 'apply_login_account']
        fields = TicketApplySerializer.Meta.fields + writeable_fields
