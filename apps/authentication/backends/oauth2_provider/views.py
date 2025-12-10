from django.views.generic import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from oauth2_provider.settings import oauth2_settings
from typing import List, Dict, Any
from .utils import get_or_create_jumpserver_client_application, CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX 


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(cache_page(timeout=60 * 60 * 24, key_prefix=CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX), name='dispatch')
class OAuthAuthorizationServerView(View):
    """
    OAuth 2.0 Authorization Server Metadata Endpoint
    RFC 8414: https://datatracker.ietf.org/doc/html/rfc8414
    
    This endpoint provides machine-readable information about the
    OAuth 2.0 authorization server's configuration.
    """
    
    def get_base_url(self, request) -> str:
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        return f"{scheme}://{host}"
    
    def get_supported_scopes(self) -> List[str]:
        scopes_config = oauth2_settings.SCOPES
        if isinstance(scopes_config, dict):
            return list(scopes_config.keys())
        return []
    
    def get_metadata(self, request) -> Dict[str, Any]:
        base_url = self.get_base_url(request)
        application = get_or_create_jumpserver_client_application()
        metadata = {
            "issuer": base_url,
            "client_id": application.client_id if application else "Not found any application.",
            "authorization_endpoint": base_url + reverse('authentication:oauth2-provider:authorize'),
            "token_endpoint": base_url + reverse('authentication:oauth2-provider:token'),
            "revocation_endpoint": base_url + reverse('authentication:oauth2-provider:revoke-token'),
            
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "scopes_supported": self.get_supported_scopes(),
            
            "token_endpoint_auth_methods_supported": ["none"],
            "revocation_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
            "response_modes_supported": ["query"],
        }
        if hasattr(oauth2_settings, 'ACCESS_TOKEN_EXPIRE_SECONDS'):
            metadata["token_expires_in"] = oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
        if hasattr(oauth2_settings, 'REFRESH_TOKEN_EXPIRE_SECONDS'):
            if oauth2_settings.REFRESH_TOKEN_EXPIRE_SECONDS:
                metadata["refresh_token_expires_in"] = oauth2_settings.REFRESH_TOKEN_EXPIRE_SECONDS
        return metadata
    
    def get(self, request, *args, **kwargs):
        metadata = self.get_metadata(request)
        response = JsonResponse(metadata)
        self.add_cors_headers(response)
        return response
    
    def options(self, request, *args, **kwargs):
        response = JsonResponse({})
        self.add_cors_headers(response)
        return response
    
    @staticmethod
    def add_cors_headers(response):
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['Access-Control-Max-Age'] = '3600'