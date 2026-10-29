"""OAuth policy for explicitly registered, public Agent clients."""
from urllib.parse import urlsplit

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.http import OAuth2ResponseRedirect
from oauth2_provider.models import get_application_model, get_refresh_token_model
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauth2_provider.views import AuthorizationView
from oauthlib.oauth2 import InvalidScopeError, InvalidRequestError, InvalidGrantError
from oauthlib.oauth2.rfc6749.errors import CustomOAuth2Error
from rest_framework.exceptions import PermissionDenied, ValidationError

from terminal.agent_service import available_agent_organizations, check_agent_organization
from terminal.models import AgentApplication, AgentOAuthBinding
from .agent_forms import AgentAllowForm
from .views import OAuthAuthorizationServerView

SCOPE = 'agent:access'


class AgentOAuth2Validator(OAuth2Validator):
    @staticmethod
    def registration(client):
        if client is None:
            return None
        return AgentApplication.objects.filter(application=client).first()

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        registration = self.registration(client)
        if registration:
            if not registration.is_active or set(scopes) != {SCOPE}:
                return False
        elif SCOPE in scopes:
            return False
        return super().validate_scopes(client_id, scopes, client, request, *args, **kwargs)

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        if self.registration(request.client):
            return [SCOPE]
        return super().get_default_scopes(client_id, request, *args, **kwargs)

    def save_authorization_code(self, client_id, code, request, *args, **kwargs):
        registration = self.registration(request.client)
        if registration:
            if not registration.is_active or set(request.scopes) != {SCOPE}:
                raise InvalidScopeError(request=request)
            if request.code_challenge_method != 'S256' or not request.code_challenge:
                raise InvalidRequestError(description='Agent clients require S256 PKCE', request=request)
            resources = request.resource if isinstance(request.resource, list) else [request.resource]
            if resources != [registration.resource]:
                raise CustomOAuth2Error(error='invalid_target', request=request)
            request.resource = resources
            org_id = getattr(request, 'agent_organization_id', None)
            if not org_id:
                organizations = list(available_agent_organizations(request.user)[:2])
                if len(organizations) == 1:
                    org_id = organizations[0].pk
            try:
                org_id = check_agent_organization(request.user, org_id)
            except (PermissionDenied, ValidationError):
                raise InvalidRequestError(description='Select an available organization', request=request)
            with transaction.atomic():
                # Use the same lock order as cleanup of never-authorized DCR clients.
                Application = get_application_model()
                try:
                    Application.objects.select_for_update().get(pk=request.client.pk)
                    registration = AgentApplication.objects.select_for_update().get(pk=registration.pk)
                except (Application.DoesNotExist, AgentApplication.DoesNotExist):
                    raise InvalidRequestError(description='Agent client is no longer available', request=request)
                if not registration.is_active:
                    raise InvalidRequestError(description='Agent client is disabled', request=request)
                grant = self._create_authorization_code(request, code)
                AgentOAuthBinding.objects.create(
                    user=request.user, application=request.client, org_id=org_id, grant=grant,
                )
                if registration.date_authorized is None:
                    registration.date_authorized = timezone.now()
                    registration.save(update_fields=['date_authorized'])
            return
        return super().save_authorization_code(client_id, code, request, *args, **kwargs)

    def organization_binding(self, request):
        bindings = AgentOAuthBinding.objects.filter(user=request.user, application=request.client)
        if request.grant_type == 'authorization_code':
            return bindings.filter(grant__code=request.code).first()
        refresh = getattr(request, 'refresh_token_instance', None)
        if refresh and refresh.token_family:
            return bindings.filter(refresh_family=refresh.token_family).first()
        return None

    def valid_organization_binding(self, request):
        registration = self.registration(request.client)
        if not registration:
            return True
        if not registration.is_active or not request.user or not request.user.is_valid:
            return False
        binding = self.organization_binding(request)
        if not binding:
            return False
        try:
            check_agent_organization(request.user, binding.org_id)
        except (PermissionDenied, ValidationError):
            return False
        return True

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        return (super().validate_code(client_id, code, client, request, *args, **kwargs)
                and self.valid_organization_binding(request))

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        return (super().validate_refresh_token(refresh_token, client, request, *args, **kwargs)
                and self.valid_organization_binding(request))

    def _save_bearer_token(self, token, request, *args, **kwargs):
        # The provider wraps this hook in the same transaction as token rotation.
        if not self.valid_organization_binding(request):
            raise InvalidGrantError(request=request)
        binding = self.organization_binding(request) if self.registration(request.client) else None
        result = super()._save_bearer_token(token, request, *args, **kwargs)
        if binding:
            access = self._load_access_token(token['access_token'])
            refresh = get_refresh_token_model().objects.filter(access_token=access).first()
            # Keep each access token bound even if its refresh row is deleted;
            # keep the family independently when old access tokens are cleaned.
            subjects = [{'access_token': access}]
            if refresh:
                subjects.append({'refresh_family': refresh.token_family})
            for subject in subjects:
                saved, _ = AgentOAuthBinding.objects.get_or_create(
                    **subject, defaults={
                        'user': request.user, 'application': request.client, 'org_id': binding.org_id,
                    },
                )
                if (saved.org_id != binding.org_id or saved.user_id != request.user.pk
                        or saved.application_id != request.client.pk):
                    raise InvalidGrantError(request=request)
        return result

    def _check_and_set_request_resource(self, request):
        super()._check_and_set_request_resource(request)
        registration = self.registration(request.client)
        if registration and (not registration.is_active or request.resource != [registration.resource]):
            raise CustomOAuth2Error(error='invalid_target', request=request)

    def validate_bearer_token(self, token, scopes, request):
        # Agent tokens are resource capabilities, never general Core API logins.
        # The dedicated, component-authenticated introspection endpoint validates
        # them directly and emits a narrower node-bound execution capability.
        access_token = self._load_access_token(token) if token else None
        if access_token and SCOPE in access_token.scope.split():
            return False
        return super().validate_bearer_token(token, scopes, request)


class AgentAwareAuthorizationView(AuthorizationView):
    def agent_registration(self):
        data = self.request.POST if self.request.method == 'POST' else self.request.GET
        return AgentApplication.objects.filter(application__client_id=data.get('client_id')).first()

    def get_form_class(self):
        return AgentAllowForm if self.agent_registration() else super().get_form_class()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.agent_registration():
            kwargs['user'] = self.request.user
        return kwargs

    def get_template_names(self):
        if self.agent_registration():
            return ['authentication/agent_authorize.html']
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = self.agent_registration()
        if registration:
            context['application'] = registration.application
        return context

    def form_valid(self, form):
        if isinstance(form, AgentAllowForm):
            organization = form.cleaned_data.get('organization')
            self.agent_organization_id = str(organization.pk) if organization else None
        return super().form_valid(form)

    def create_authorization_response(self, request, scopes, credentials, allow):
        if self.agent_registration():
            credentials['agent_organization_id'] = getattr(self, 'agent_organization_id', None)
        return super().create_authorization_response(request, scopes, credentials, allow)

    def get(self, request, *args, **kwargs):
        if AgentApplication.objects.filter(application__client_id=request.GET.get('client_id')).exists():
            request.GET = request.GET.copy()
            request.GET['approval_prompt'] = 'force'
        return super().get(request, *args, **kwargs)

    def redirect(self, redirect_to, application):
        if application and AgentApplication.objects.filter(application=application, is_active=True).exists():
            data = self.request.POST if self.request.method == 'POST' else self.request.GET
            callback = data.get('redirect_uri') or self.oauth2_data.get('redirect_uri', '')
            source, target = urlsplit(callback), urlsplit(redirect_to)
            if (source.scheme == 'http' and source.hostname in ('127.0.0.1', '::1')
                    and application.redirect_uri_allowed(callback)
                    and source._replace(query='') == target._replace(query='')):
                # OAuth appends code/state or error parameters to the already
                # validated callback. Permit only this Agent's loopback response.
                return OAuth2ResponseRedirect(redirect_to, allowed_schemes=['http'])
        return super().redirect(redirect_to, application)


class AgentAuthorizationServerView(OAuthAuthorizationServerView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        # DCR can be enabled/disabled independently; do not inherit the built-in
        # client's cached metadata or retain stale registration discovery.
        response = View.dispatch(self, request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response

    def get_metadata(self, request):
        base = self.get_base_url(request)
        from django.urls import reverse
        metadata = {
            'issuer': base,
            'authorization_endpoint': base + reverse('authentication:oauth2-provider:authorize'),
            'token_endpoint': base + reverse('authentication:oauth2-provider:token'),
            'revocation_endpoint': base + reverse('authentication:oauth2-provider:revoke-token'),
            'response_types_supported': ['code'],
            'grant_types_supported': ['authorization_code', 'refresh_token'],
            'scopes_supported': [SCOPE],
            'token_endpoint_auth_methods_supported': ['none'],
            'revocation_endpoint_auth_methods_supported': ['none'],
            'code_challenge_methods_supported': ['S256'],
        }
        from .agent_registration import configured_resource
        if configured_resource():
            metadata['registration_endpoint'] = base + reverse('authentication:oauth2-provider:agent-register')
        return metadata
