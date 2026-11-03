from django.http import HttpResponseBadRequest
from django.utils.translation import gettext as _
from oauth2_provider.models import get_application_model
from oauth2_provider.views import AuthorizationView

from authentication.services.client_login_session import (
    client_login_policy, client_policy_transaction, is_client_application,
)


class ClientAuthorizationView(AuthorizationView):
    def dispatch(self, request, *args, **kwargs):
        with client_policy_transaction():
            # DOT uses POST client_id when the authorization form is submitted.
            data = request.POST if request.method == 'POST' else request.GET
            application = get_application_model().objects.filter(client_id=data.get('client_id', '').strip()).first()
            version = data.get('client_login_policy_version', request.GET.get('client_login_policy_version'))
            if is_client_application(application) and any(client_login_policy().values()) and version != '1':
                return HttpResponseBadRequest(_('Please upgrade the JumpServer client to use the configured login policy.'))
            return super().dispatch(request, *args, **kwargs)
