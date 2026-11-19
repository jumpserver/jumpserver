from rest_framework import serializers

from authentication.const import ConfirmType
from authentication.permissions import UserConfirmation
from tickets.plugins.actions import TicketAction
from tickets.plugins.resources import RequestSerializer


class RevealParameters(RequestSerializer):
    account_id = serializers.UUIDField()


class ViewSecret(TicketAction):
    permission_classes = (UserConfirmation.require(ConfirmType.MFA),)

    def execute(self, ticket, request):
        from accounts.ticket_secret import reveal_ticket_secret
        serializer = RevealParameters(data=request.data)
        serializer.is_valid(raise_exception=True)
        return reveal_ticket_secret(request, serializer.validated_data['account_id'], ticket.pk)
