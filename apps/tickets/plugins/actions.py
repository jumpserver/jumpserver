"""Trusted action handlers share DRF permissions and throttles with the host API."""


class TicketAction:
    method = 'POST'
    permission_classes = ()
    throttle_classes = ()

    def execute(self, ticket, request):
        raise NotImplementedError
