from threading import RLock

from django.conf import settings
from django.core.cache import cache
from oauth2_provider.models import get_application_model
from oauth2_provider.settings import OAuth2ProviderSettings, oauth2_settings

from common.utils import get_logger

logger = get_logger(__name__)

oauth2_settings_lock = RLock()
OAUTH2_TOKEN_SETTING_NAMES = ('ACCESS_TOKEN_EXPIRE_SECONDS', 'REFRESH_TOKEN_EXPIRE_SECONDS')

# Populate these lazy attributes during app startup, before settings subscriber threads start.
for _name in OAUTH2_TOKEN_SETTING_NAMES:
    getattr(oauth2_settings, _name)


class DynamicOAuth2Mixin:
    @classmethod
    def get_oauthlib_core(cls):
        with oauth2_settings_lock:
            return super().get_oauthlib_core()


def get_or_create_jumpserver_client_application():
    """Auto get or create OAuth2 JumpServer Client application."""
    Application = get_application_model()
    
    application, created = Application.objects.get_or_create(
        name=settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME,
        defaults={
            'client_type': Application.CLIENT_PUBLIC,
            'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE,
            'redirect_uris': settings.OAUTH2_PROVIDER_CLIENT_REDIRECT_URI,
            'skip_authorization': True,
        }
    )
    return application


CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX = 'oauth2_provider_metadata'


def clear_oauth2_authorization_server_view_cache():
    logger.info("Clearing OAuth2 Authorization Server Metadata view cache")
    cache_key = f'views.decorators.cache.cache_page.{CACHE_OAUTH_SERVER_VIEW_KEY_PREFIX}.GET*'
    cache.delete_pattern(cache_key)


def refresh_oauth2_provider_settings():
    from .views import AuthorizationView, TokenView

    with oauth2_settings_lock:
        token_settings = {
            name: getattr(settings, 'OAUTH2_PROVIDER_' + name)
            for name in OAUTH2_TOKEN_SETTING_NAMES
        }
        provider_settings = {**settings.OAUTH2_PROVIDER, **token_settings}
        snapshot = OAuth2ProviderSettings(provider_settings)
        cores = []
        for view in (AuthorizationView, TokenView):
            server = view.get_server_class()(view.get_validator_class()(), **snapshot.server_kwargs)
            cores.append((view, view.get_oauthlib_backend_class()(server)))

        # Publish only after all cores are ready; readers never observe a deleted cache.
        settings.OAUTH2_PROVIDER = provider_settings
        oauth2_settings.user_settings.update(token_settings)
        for name, value in token_settings.items():
            setattr(oauth2_settings, name, value)
        for view, core in cores:
            view._oauthlib_core = core
    clear_oauth2_authorization_server_view_cache()
