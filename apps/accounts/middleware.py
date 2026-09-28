from accounts.credential_client.audit import CredentialFetchAudit


class ApplicationAuditMiddleware:
    """Record rejected operations after ATOMIC_REQUESTS has rolled them back."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        context = getattr(request, 'application_audit', None)
        if context is None:
            return response

        if context.fetch_identity is not None:
            CredentialFetchAudit(context).record_result(response.status_code)
        elif response.status_code >= 400:
            context.record_failure(response.status_code)
        return response
