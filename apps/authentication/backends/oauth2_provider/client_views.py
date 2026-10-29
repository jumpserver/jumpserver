import json

from django.db import transaction
from django.http import HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from oauth2_provider.models import get_application_model
from oauth2_provider.views import AuthorizationView, RevokeTokenView, TokenView

from authentication.services.client_login_session import (
    client_login_session_data, client_policy_enabled, client_policy_lock,
    expired_session_from_receipt, is_client_application,
)


@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ClientAuthorizationView(AuthorizationView):
    def _unsupported_client_response(self, request):
        if not client_policy_enabled():
            return None
        # DOT reads the authorization form's client_id on POST, which need not
        # match the query string. Apply the capability check to that same client.
        data = request.POST if request.method == 'POST' else request.GET
        client_id = data.get('client_id', '')
        if request.method == 'POST':
            client_id = client_id.strip()  # Match DOT AllowForm's CharField normalization.
        application = get_application_model().objects.filter(client_id=client_id).first()
        version = data.get('client_login_policy_version', request.GET.get('client_login_policy_version'))
        if is_client_application(application) and version != '1':
            return HttpResponseBadRequest(_('Please upgrade the JumpServer client to use the configured login policy.'))
        return None

    def get(self, request, *args, **kwargs):
        with client_policy_lock(), transaction.atomic():
            response = self._unsupported_client_response(request)
            if response is not None:
                return response
            return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        with client_policy_lock(), transaction.atomic():
            response = self._unsupported_client_response(request)
            if response is not None:
                return response
            return super().post(request, *args, **kwargs)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ClientTokenView(TokenView):
    def post(self, request, *args, **kwargs):
        with client_policy_lock(), transaction.atomic():
            response = super().post(request, *args, **kwargs)
            if response.status_code == 400 and request.POST.get('grant_type') == 'refresh_token':
                data = json.loads(response.content)
                if data.get('error') == 'invalid_grant' and not data.get('client_login_reason'):
                    session = expired_session_from_receipt(
                        request.POST.get('client_login_session_receipt'), request.POST.get('refresh_token'),
                        'refresh_token', client_id=request.POST.get('client_id', ''),
                    )
                    if session and session.client_login_reason:
                        data['client_login_reason'] = session.client_login_reason
                        data['client_login_session'] = client_login_session_data(session)
                        response.content = json.dumps(data)
            return response


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ClientRevokeTokenView(RevokeTokenView):
    def post(self, request, *args, **kwargs):
        with client_policy_lock(), transaction.atomic():
            return super().post(request, *args, **kwargs)
